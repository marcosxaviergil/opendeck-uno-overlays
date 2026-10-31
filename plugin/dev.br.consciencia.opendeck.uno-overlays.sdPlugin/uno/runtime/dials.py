"""Knobs of the Vision Sound 01: Action Wheel (slots) and uno v2 edit mode (values), with Shift."""

import asyncio
import logging

from uno.api import UnoError
from uno.i18n import tr
from uno.values import composite, increment

__all__ = ["CAROUSEL_GAP", "DIALS", "DialMixin"]

log = logging.getLogger(__name__)

DIALS = ("slotwheel", "dialvalue")
# Carousel: at least this many seconds between two slot takes of a turning knob. Ticks that arrive
# meanwhile join the waiting take, so a fast turn costs one App API call (UNO answered HTTP 429 to bursts).
CAROUSEL_GAP = 0.3


class DialMixin:
    def _init_dials(self):
        self.dials, self.shifts = {}, set()

    async def dial(self, ctx, action, event, ticks):
        s, d = self.dial_settings(ctx), self.dials.setdefault(ctx, {})
        api = self.api(s.get("token"))
        store = self.stores.get(api.token)
        if store is None or not store.ready.is_set():
            store = await self.store(api.token)  # ready stores keep rotation order: no await
        if event == "dialDown":
            d["held"] = False
            if action == "dialvalue":
                # uno Stream Deck plugin v2: press and hold two seconds cancels.
                d["hold"] = asyncio.get_running_loop().call_later(2, self.cancel_edit, ctx)
            return
        if event == "dialUp":
            if d.get("hold"):
                d["hold"].cancel()
            if d.pop("held", False):
                return
            event = "click"
        if action == "slotwheel":
            overlay_id = s.get("overlayId")
            items = [i for i in store.slots(overlay_id).get("data") or [] if isinstance(i, dict)]
            if not items:
                raise UnoError(tr("This overlay has no server slots."))
            if s.get("carousel"):
                self.carousel(ctx, api, s, event, ticks)
            elif event == "dialRotate":
                d["cued"][overlay_id] = (self.cued(ctx, s, items) + ticks) % len(items)  # the wheel wraps around
            else:
                slot = items[self.cued(ctx, s, items) % len(items)]
                self.flush_edits(api.token)
                self.submit(
                    lambda job: self.toggle(ctx, api, {**s, "serverSlotId": slot["id"], "slotNumber": 0}),
                    owners={ctx},
                    token=api.token,
                    overlay=overlay_id,
                )
        else:
            overlay_id, field_id = composite(d["field"] if d.get("editing") else s.get("fieldComposite"))
            if not overlay_id or not field_id:
                raise UnoError(tr("Select a numeric field."))
            if event == "dialRotate":
                if d.get("editing"):
                    d["pending"] = increment(d["pending"], ticks * self.multiplier)
            elif not d.get("editing"):
                d.update(
                    editing=True, field=s.get("fieldComposite"), pending=store.content(overlay_id).get(field_id, 0)
                )
            else:
                value, d["editing"] = d["pending"], False
                self.check_lock(api.token)
                self.flush_edits(api.token)
                self.remember(api.token, store, {overlay_id: [field_id]})
                self.submit(
                    lambda job: self.write_content(api, store, overlay_id, {field_id: value}),
                    owners={ctx},
                    token=api.token,
                    overlay=overlay_id,
                )
        await self.repaint()

    def carousel(self, ctx, api, s, event, ticks):
        """Optional Slot Wheel mode: each turn takes the next or previous slot on air; press shows or hides."""
        overlay_id, d = s.get("overlayId"), self.dials.setdefault(ctx, {})
        if event != "dialRotate":
            self.flush_edits(api.token)
            plain = {**s, "serverSlotId": "", "slotNumber": 0, "slotsEnabled": False}
            self.submit(lambda job: self.toggle(ctx, api, plain), owners={ctx}, token=api.token, overlay=overlay_id)
            return
        d["spin"] = d.get("spin", 0) + ticks
        if d.get("spin_wait"):
            return  # a take is already waiting: this turn joins it
        loop = asyncio.get_running_loop()

        def due():
            self.triggers.discard(d["spin_wait"])
            self.submit(lambda job: self.carousel_take(ctx, api, s), owners={ctx}, token=api.token, overlay=overlay_id)

        d["spin_wait"] = loop.call_later(max(0, d.get("spin_at", 0) + CAROUSEL_GAP - loop.time()), due)
        self.triggers.add(d["spin_wait"])  # Panic cancels it

    async def carousel_take(self, ctx, api, s):
        d = self.dials.setdefault(ctx, {})
        ticks, d["spin"], d["spin_wait"] = d.get("spin", 0), 0, None
        d["spin_at"] = asyncio.get_running_loop().time()
        store, overlay_id = await self.store(api.token), s.get("overlayId")
        slots = store.slots(overlay_id)
        items = [i for i in slots.get("data") or [] if isinstance(i, dict)]
        if not ticks or not items:
            return
        self.check_edits(api.token)
        now = next((i for i, item in enumerate(items) if item.get("id") == slots.get("currentSlotId")), 0)
        target = (now + ticks) % len(items)  # wraps around, like the wheel
        await api.call("TakeOverlaySlotNumber", id=overlay_id, value=target + 1)
        log.info("Slot Wheel carousel: %d tick(s), slot %d of %d taken.", ticks, target + 1, len(items))

    def dial_settings(self, ctx):
        """While a Shift key is held, a knob uses its optional Shift overlay or field."""
        s = self.settings.get(ctx, {})
        if self.shifts and s.get("shiftOverlayId"):
            return {**s, "overlayId": s["shiftOverlayId"]}
        if self.shifts and s.get("shiftFieldComposite"):
            return {**s, "fieldComposite": s["shiftFieldComposite"]}
        return s

    def cued(self, ctx, s, items):
        cued = self.dials.setdefault(ctx, {}).setdefault("cued", {})  # per overlay: Shift may switch it
        if s.get("overlayId") not in cued:
            store = self.stores.get(s.get("token"))
            current = store.slots(s.get("overlayId")).get("currentSlotId") if store else None
            cued[s.get("overlayId")] = next((i for i, item in enumerate(items) if item.get("id") == current), 0)
        return cued[s.get("overlayId")]

    def cancel_edit(self, ctx):
        d = self.dials.get(ctx, {})
        d.update(held=True, editing=False, pending=None)
        self.spawn(self.repaint())
