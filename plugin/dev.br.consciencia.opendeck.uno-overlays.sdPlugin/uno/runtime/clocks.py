"""Clock keys: run a Clock (uno.clock) per text field and write its text each second."""

import asyncio
import logging

from uno.api import UnoError
from uno.clock import Clock
from uno.datastore import component
from uno.i18n import tr
from uno.images import icon_image
from uno.values import composite, parse_hms

log = logging.getLogger(__name__)

__all__ = ["ClockMixin"]


class ClockMixin:
    def _init_clocks(self):
        self.clocks, self.clock_task = {}, None  # (token, overlay, field) -> Clock

    def clock_press(self, ctx, s):
        self.clock_op(ctx, s, s.get("operation") or "pause", s.get("value"))

    def clock_op(self, ctx, s, operation, value=None):
        clock = self.clocks.setdefault(self.clock_key(s), Clock(s))
        clock.cfg, clock.owner = dict(s), ctx
        clock.apply(operation, value, asyncio.get_running_loop().time())
        self.start_clocks()
        self.spawn(self.repaint())

    def clock_settings(self, ctx, s):
        """A settings change reaches a stopped clock; time of day starts by itself (stagetimer)."""
        key = self.clock_key(s, False)
        if key is None:
            return
        clock = self.clocks.get(key)
        if clock and not clock.running:
            clock.duration, clock.cfg, clock.dirty = parse_hms(s.get("duration")), dict(s), True
        if s.get("mode") == "timeofday" and clock is None:
            self.clock_op(ctx, s, "start")
        elif clock:
            self.start_clocks()

    def clock_key(self, s, required=True):
        overlay_id, field_id = composite(s.get("fieldComposite"))
        token = str(s.get("token") or "").strip()
        if not (token and overlay_id and field_id):
            if required:
                raise UnoError(tr("Select the text field that shows the clock."))
            return None
        return token, overlay_id, field_id

    def clock_config(self, token, field):
        """Settings of the clock shown in a field: the live clock, else a Clock key for it."""
        live = [c.cfg for key, c in self.clocks.items() if key[0] == token and f"{key[1]}::{key[2]}" == field]
        keys = [
            s
            for ctx, s in self.settings.items()
            if self.actions.get(ctx, "").endswith(".clock")
            and str(s.get("token") or "").strip() == token
            and s.get("fieldComposite") == field
        ]
        saved = self.remembered("clockConfigs", token, field)  # a Clock key seen before, maybe not visible now
        found = live + keys + ([saved] if saved else [])
        if not found:
            raise UnoError(tr("No Clock key shows this field."))
        return found[0]

    def clock_image(self, s):
        clock = self.clocks.get(self.clock_key(s, required=False))
        if clock is None:
            return icon_image("clock")
        now = asyncio.get_running_loop().time()
        return icon_image("clock", clock.color(now), None, [""] if clock.hidden(now) else [clock.text(now)])

    def start_clocks(self):
        if self.clock_task is None or self.clock_task.done():
            self.clock_task = self.spawn(self.clock_tick())

    async def clock_tick(self):
        while True:
            now = asyncio.get_running_loop().time()
            active = False
            for key, clock in list(self.clocks.items()):
                store = self.stores.get(clock.cfg.get("token"))
                ready = store is not None and store.ready.is_set()
                if clock.cfg.get("pauseOffAir") and ready:
                    clock.follow_air(store.on_air(key[1]), now)
                if clock.complete(now):  # vMix OnCountdownCompleted
                    self.fire(clock.owner, {**clock.cfg, "overlayId": key[1]}, "countdown")
                if not clock.active(now):
                    continue
                active = True
                text = "" if clock.hidden(now) and clock.cfg.get("flashField") else clock.text(now)
                if ready and not clock.busy:
                    clock.dirty = False
                    if text != clock.written:
                        self.spawn(self.write_clock(key, clock, store, text))
            await self.repaint(
                [ctx for ctx, action in list(self.actions.items()) if action.endswith((".clock", ".visor"))]
            )
            if not active:
                return
            await asyncio.sleep(0.25)

    async def write_clock(self, key, clock, store, text):
        # ponytail: clock text goes straight to the datastore (its own rate limiter), outside the key
        # queue, so a long queued job cannot freeze the clock. Same path the official client writes.
        clock.busy = True
        try:
            await store.write({f"{store.node(key[1])[0]}.payload.{component(key[2])}": text})
            clock.written = text
        except UnoError as exc:
            log.warning("UNO clock: %s", exc)
        finally:
            clock.busy = False
