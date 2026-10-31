"""Key images: Material Symbols glyph, tally (red on air), Auto Close badge and the Visor."""

import asyncio
import logging
import math
import time

from uno.api import UnoError
from uno.i18n import tr
from uno.images import RED, WHITE, caption, icon_image, step_image
from uno.runtime.dials import DIALS
from uno.runtime.safety import STATUS_COLORS
from uno.values import composite, integer

__all__ = ["TALLY", "KeyImageMixin"]

log = logging.getLogger(__name__)

TALLY = ("toggle", "numericfields", "nextslot", "prevslot")  # keys bound to one overlay
MINUS = "\u2212"  # the minus sign the inspector shows in "Decrement (−)"


class KeyImageMixin:
    def _init_keys(self):
        self.images, self.tally_checked = {}, set()

    async def repaint(self, ctxs=None):
        for ctx in list(self.actions if ctxs is None else ctxs):
            image = self.paint(ctx) if ctx in self.actions else None
            if image is not None and self.images.get(ctx) != image:
                self.images[ctx] = image
                await self.message("setImage", ctx, {"image": image})

    def paint(self, ctx):
        action = self.actions.get(ctx, "").rsplit(".", 1)[-1]
        if self.controllers.get(ctx) == "Encoder" or action in ("display", "knob") + DIALS:
            return None  # Display draws numbers; the Sound 01 knobs have no screen
        s = self.settings.get(ctx, {})
        if ctx in self.armed and int(time.monotonic() * 2) % 2:  # armed: blinks until the second press
            return icon_image(action, WHITE if self.live(ctx, action, s) else RED)
        if action == "status":
            report = self.status()
            color, background = STATUS_COLORS[report["category"]]
            return icon_image("status", color, None, [str(report["calls"])], background)
        if action == "visor":
            return self.visor(s)
        if action == "clock":
            return self.clock_image(s)
        now = asyncio.get_running_loop().time()
        badge = next((max(1, math.ceil(e[2] - now)) for e in self.timers.values() if e[0] == ctx), None)
        color = RED if self.live(ctx, action, s) else WHITE
        if action == "numericfields":  # empty Fixed step: the global multiplier is what one press adds
            sign = MINUS if s.get("operation") == "decrement" else "+"
            return step_image(f"{sign}{abs(integer(s.get('step'))) or self.multiplier}", color, badge)
        return icon_image(action, color, badge)

    def live(self, ctx, action, s):
        store = self.stores.get(s.get("token"))
        ready = store is not None and store.ready.is_set()
        if action in TALLY:
            return ready and bool(s.get("overlayId")) and store.on_air(s["overlayId"])
        if action == "timer":
            overlay_id, field_id = composite(s.get("fieldComposite"))
            try:
                return ready and bool((store.content(overlay_id).get(field_id) or {}).get("isRunning"))
            except (UnoError, AttributeError):
                return False
        if action == "obsscene":
            return bool(self.obs and self.obs.connected and s.get("sceneName") and self.obs.scene == s["sceneName"])
        if action == "macro":
            return ctx in self.macros
        if action == "lock":
            return str(s.get("token") or "").strip() in self.locked
        if action == "reset":
            return ctx in self.holds
        if action == "lockdesk":
            return self.desk_locked
        if action == "datasource":
            return s.get("operation") == "autonext" and bool(self.source_state(str(s.get("source") or ""))["auto"])
        if action == "goal":
            return ((self.global_settings.get("goals") or {}).get(str(s.get("goal") or "")) or {}).get(
                "state"
            ) == "active"
        if action == "shift":
            return bool(self.shifts)
        if action == "reveal":
            return ready and self.revealed(store, s)
        return False

    def visor(self, s):
        dial = self.dial_for(s.get("channel"))
        if dial is None:
            return icon_image("visor")
        action, d, ds = self.actions[dial].rsplit(".", 1)[-1], self.dials.get(dial, {}), self.dial_settings(dial)
        if action == "clock":
            return self.clock_image(ds)
        if action == "datasource":
            return self.source_image(dial, ds)
        store = self.stores.get(ds.get("token"))
        if store is None or not store.ready.is_set():
            return icon_image(action, WHITE, None, ["…"])
        try:
            if action == "slotwheel":
                items = [i for i in store.slots(ds.get("overlayId")).get("data") or [] if isinstance(i, dict)]
                if not items:
                    return icon_image(action, WHITE, None, [tr("No slots")])
                current = store.slots(ds.get("overlayId")).get("currentSlotId")
                if ds.get("carousel"):  # carousel: the slot on air, not a chosen one
                    slot = next((i for i in items if i.get("id") == current), items[0])
                else:
                    slot = items[self.cued(dial, ds, items) % len(items)]
                on_air = slot.get("id") == current and store.on_air(ds.get("overlayId"))
                return icon_image(action, RED if on_air else WHITE, None, caption(slot.get("name") or tr("Slot")))
            overlay_id, field_id = composite(d["field"] if d.get("editing") else ds.get("fieldComposite"))
            value = d["pending"] if d.get("editing") else store.content(overlay_id).get(field_id, "")
            return icon_image(action, WHITE, None, [("→ " if d.get("editing") else "") + str(value)])
        except UnoError:
            return icon_image(action, WHITE, None, ["—"])

    def dial_for(self, channel):
        def knob(ctx, kind):
            return kind in DIALS or (kind in ("clock", "datasource") and self.controllers.get(ctx) == "Encoder")

        return next(
            (
                ctx
                for ctx, action in self.actions.items()
                if channel
                and knob(ctx, action.rsplit(".", 1)[-1])
                and self.settings.get(ctx, {}).get("channel") == channel
            ),
            None,
        )

    def check_tally(self, token, overlay_id, api_visible):
        # Tally reads compositionStates; log once if it disagrees with GetOverlays.
        store = self.stores.get(token)
        if store is None or not store.ready.is_set() or (token, overlay_id) in self.tally_checked:
            return
        self.tally_checked.add((token, overlay_id))
        if store.on_air(overlay_id) != api_visible:
            log.warning(
                "Tally check: UNO API visible=%s but datastore state says %s for one overlay.",
                api_visible,
                store.on_air(overlay_id),
            )
