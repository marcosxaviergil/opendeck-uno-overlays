"""Overlays on and off air: toggle, exclusive groups, slots, Auto Close (with badge) and timers."""

import asyncio
import logging
import time

from uno.api import UnoError
from uno.datastore import component
from uno.i18n import tr
from uno.values import composite, integer, seconds, visible

__all__ = ["OverlayMixin", "timecontrol"]

log = logging.getLogger(__name__)


class OverlayMixin:
    def _init_overlays(self):
        self.timers, self.ticker = {}, None  # (token, overlay) -> [owner, handle, deadline]

    async def toggle(self, ctx, api, settings):
        # A failed save blocks Take, so an old slot is never put on air silently.
        self.check_edits(api.token)
        overlay_id = settings.get("overlayId", "")
        overlay = await self.overlay(api, overlay_id)
        is_visible = visible(overlay)
        self.check_tally(api.token, overlay_id, is_visible)
        slot = max(0, integer(settings.get("slotNumber")))
        slot_id = settings.get("serverSlotId") or ""
        pending = self.timers.get((api.token, overlay_id))

        if pending and is_visible:
            if settings.get("pressAgain") == "add":
                left = pending[2] - asyncio.get_running_loop().time()
                self.schedule_hide(
                    ctx,
                    api,
                    overlay_id,
                    max(0, left) + seconds(settings.get("autoClose")),
                )
            else:
                self.cancel_hide(api.token, overlay_id)
                await api.call("HideOverlay", id=overlay_id)
            return

        showing = settings.get("slotsEnabled") or slot or slot_id or not is_visible
        self.cancel_hide(api.token, overlay_id)
        allowed = [name.strip() for name in str(settings.get("obsOnlyScenes") or "").split(",") if name.strip()]
        if showing and allowed and not (self.obs and self.obs.connected and self.obs.scene in allowed):
            scene = self.obs.scene if self.obs and self.obs.connected else tr("unknown (OBS not connected)")
            raise UnoError(
                tr(
                    "Blocked: OBS program scene is {scene}; this overlay may show only in {scenes}.",
                    scene=scene,
                    scenes=", ".join(allowed),
                )
            )
        if settings.get("slotsEnabled") or slot or slot_id:
            if slot or slot_id:
                store = await self.store(api.token)
                index, _ = store.slot(overlay_id, slot, slot_id)
                await api.call("TakeOverlaySlotNumber", id=overlay_id, value=index + 1)
            await self.show(api, overlay_id)
        elif is_visible:
            await api.call("HideOverlay", id=overlay_id)
            return
        else:
            await self.show(api, overlay_id)
        self.schedule_hide(ctx, api, overlay_id, seconds(settings.get("autoClose")))

    async def show(self, api, overlay_id):
        """ShowOverlay. In an exclusive group, like a Singular logic layer, the others go out:
        custom time > 0 delays the new In, < 0 delays the old Out (computeLogicLayerCompositionStates).
        Groups are global (uno.automations): members whose keys are not visible go out too."""
        group, delay, members = self.group_of(api.token, overlay_id)
        others = []
        for token, other in members:
            store = self.stores.get(token)
            if store is not None and store.ready.is_set() and store.on_air(other):
                others.append((self.api(token) if token != api.token else api, other))
        if group:
            log.info("Exclusive group %r: %d other overlay(s) on air go out.", group, len(others))

        async def out(job=None):
            for other_api, other in others:
                self.cancel_hide(other_api.token, other)
                await other_api.call("HideOverlay", id=other)

        if delay < 0:
            await api.call("ShowOverlay", id=overlay_id)
            if others:
                handle = asyncio.get_running_loop().call_later(
                    -delay, lambda: (self.triggers.discard(handle), self.submit(out, token=api.token))
                )
                self.triggers.add(handle)
            return
        await out()
        if others and delay:
            await asyncio.sleep(delay)  # ponytail: holds the queue for the logic-layer time (max 30 s)
        await api.call("ShowOverlay", id=overlay_id)

    async def all_overlays(self, api, action):
        self.cancel_hide(api.token)
        await api.call("ShowAllOverlays" if action == "showall" else "HideAllOverlays")

    async def step_slot(self, ctx, api, settings, action):
        self.check_edits(api.token)
        overlay_id = settings.get("overlayId", "")
        if not overlay_id:
            raise UnoError(tr("Select an overlay."))
        self.cancel_hide(api.token, overlay_id)
        await api.call("TakeOverlayNextSlot" if action == "nextslot" else "TakeOverlayPreviousSlot", id=overlay_id)
        await self.show(api, overlay_id)
        self.schedule_hide(ctx, api, overlay_id, seconds(settings.get("autoClose")))

    def schedule_hide(self, ctx, api, overlay_id, delay):
        self.cancel_hide(api.token, overlay_id)
        if not delay:
            return
        key = (api.token, overlay_id)
        entry = [ctx, None, asyncio.get_running_loop().time() + delay]  # owner, handle, deadline

        async def hide(job):
            if self.timers.get(key) is not entry:
                return  # replaced or cancelled while waiting in the queue
            del self.timers[key]
            await api.call("HideOverlay", id=overlay_id)

        def fire():
            if self.timers.get(key) is entry:
                self.submit(hide, owners={ctx}, token=api.token, overlay=overlay_id)

        entry[1] = asyncio.get_running_loop().call_later(delay, fire)
        self.timers[key] = entry
        if self.ticker is None or self.ticker.done():
            self.ticker = self.spawn(self.tick())

    def cancel_hide(self, token, overlay_id=None):
        for key, entry in list(self.timers.items()):
            if key[0] == token and (overlay_id is None or key[1] == overlay_id):
                entry[1].cancel()
                self.timers.pop(key, None)

    async def tick(self):
        # Auto Close badges count down once per second; the last pass clears them.
        owners = set()
        while True:
            current = {entry[0] for entry in self.timers.values()}
            await self.repaint(owners | current)
            if not current:
                return
            owners = current
            await asyncio.sleep(0.2)

    async def run_timer(self, api, settings):
        overlay_id, field_id = composite(settings.get("fieldComposite"))
        if not overlay_id or not field_id:
            raise UnoError(tr("Select a timer field."))
        store = await self.store(api.token)
        current = store.content(overlay_id).get(field_id)
        current = current if isinstance(current, dict) else {}
        operation = settings.get("operation") or "toggle"
        if operation == "toggle":
            operation = "pause" if current.get("isRunning") else "play"
        value = timecontrol(current, operation, int(time.time() * 1000))
        if value is not None:
            await store.write({f"{store.node(overlay_id)[0]}.payload.{component(field_id)}": value})
        await self.repaint()


def timecontrol(current, command, now):
    """processPayloadCommand() for timecontrol fields in the official singular-datastore client."""
    value = current.get("value") or 0
    if command == "play":
        return None if current.get("isRunning") else {"UTC": now, "isRunning": True, "value": value}
    if command == "pause":
        if not current.get("isRunning"):
            return None
        return {"UTC": now, "isRunning": False, "value": value + now - (current.get("UTC") or now)}
    if command == "reset":
        return {"UTC": now, "isRunning": False, "value": 0}
    if command == "start":
        return {"UTC": now, "isRunning": True, "value": 0}
    raise UnoError(tr("Unsupported timer operation."))