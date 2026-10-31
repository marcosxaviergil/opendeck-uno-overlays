"""UNO content: the realtime datastore copy per token, reads, writes and inspector edits."""

import asyncio
import logging
from copy import deepcopy

from uno.api import UnoError
from uno.datastore import component
from uno.i18n import tr
from uno.images import number_image
from uno.values import composite, integer, merge

__all__ = ["EDIT_WINDOW", "LIVE_EDIT_DELAY", "ContentMixin"]

EDIT_WINDOW = 0.4  # seconds: off-air typing is sent at most this often (counted from the first change)
LIVE_EDIT_DELAY = 1000  # ms without changes before an on-air edit is sent; settings page, 0 to 10 000

log = logging.getLogger(__name__)


class ContentMixin:
    def _init_content(self):
        self.stores, self.edits, self.edit_errors, self.failed_patches = {}, {}, {}, {}

    async def store(self, token):
        if token not in self.stores:
            self.stores[token] = self.store_factory(token, self.store_changed)
        return await self.stores[token].ensure()

    async def watch(self, token, register=True):
        """Realtime copy of a control app. A key's token that connects joins the registry (Status, Panic,
        triggers); a watch started from the registry does not, so an app forgotten meanwhile stays forgotten."""
        try:
            await self.store(token)  # starts the realtime copy that drives tally
            if register:
                self.register(token)
        except UnoError as exc:
            log.warning("UNO: %s", exc)
        await self.repaint()

    async def store_changed(self, store):
        if store.ready.is_set():
            self.derive(store)
        for ctx, settings in list(self.settings.items()):
            if settings.get("token") != store.token:
                continue
            if self.actions.get(ctx, "").endswith(".display"):
                overlay_id, field_id = composite(settings.get("fieldComposite"))
                if overlay_id and field_id:
                    try:
                        content = store.content(overlay_id) if store.ready.is_set() else {field_id: "—"}
                        await self.display_content(ctx, content, field_id)
                    except UnoError:
                        await self.display_content(ctx, {field_id: "—"}, field_id)
            # OpenDeck keeps messages for closed inspectors in memory and replays
            # them on open (events/mod.rs); notify only inspectors that are open.
            if ctx in self.open_inspectors:
                await self.to_inspector(ctx, {"type": "uno.changed"})
        if store.ready.is_set():
            self.uno_changed(store)  # global OnOverlayIn / OnOverlayOut triggers
            self.slots_changed(store)  # Reveal Answer goes back to hidden on a new slot
        await self.repaint()

    async def display(self, ctx, settings):
        try:
            overlay_id, field_id = composite(settings.get("fieldComposite"))
            if not settings.get("token") or not overlay_id or not field_id:
                await self.message("setImage", ctx, {"image": ""})
                return
            store = await self.store(settings["token"])
            content = store.content(overlay_id)
            if self.settings.get(ctx) == settings:
                await self.display_content(ctx, content, field_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: shown to the user as a safe message
            await self.report(ctx, exc)

    async def display_content(self, ctx, content, field_id):
        image = number_image(content.get(field_id, ""))
        if self.images.get(ctx) != image:
            self.images[ctx] = image
            await self.message("setImage", ctx, {"image": image})

    async def overlay(self, api, overlay_id):
        if not overlay_id:
            raise UnoError(tr("Select an overlay."))
        overlays = await api.call("GetOverlays")
        for overlay in overlays or []:
            if str(overlay.get("id")) == str(overlay_id):
                return overlay
        raise UnoError(tr("The configured overlay was not found. Reload the overlay list."))

    async def write_content(self, api, store, overlay_id, patch, number=0, slot_id=""):
        if not patch:
            return
        selected = store.slot(overlay_id, number, slot_id)
        await store.save_slot(overlay_id, patch, number, slot_id)
        # Editing an inactive server slot must not put it on air.
        current = store.slots(overlay_id).get("currentSlotId")
        if (number or slot_id) and selected and selected[1]["id"] != current:
            return
        remote = store.content(overlay_id)
        changes = {key: merge(remote.get(key), value) for key, value in patch.items()}
        mark = store.events
        # Status 200 from the documented UNO API confirms the live content.
        await api.call("SetOverlayContent", id=overlay_id, content=changes)
        await store.sync_content(overlay_id, changes, mark)
        await self.store_changed(store)

    def queue_edit(self, ctx, action, payload):
        """Inspector typing. Off air (or an inactive server slot) it goes at most every 0.4 s; on air it
        waits until nothing changed for the live edit delay, so the audience never sees half a word."""
        key = (
            payload.get("token"),
            payload.get("id"),
            str(payload.get("slotId") or ""),
            integer(payload.get("slotNumber")),
        )
        if not isinstance(payload.get("patch"), dict) or not isinstance(payload.get("requestId"), str):
            return
        wait = self.live_wait(ctx, key)
        batch = self.edits.get(key)
        if batch is None:
            batch = {"patch": deepcopy(self.failed_patches.get(key, {})), "requests": [], "timer": None}
            self.edits[key] = batch
        if batch["timer"] is None or wait:  # on air every change restarts the wait; off air the window is fixed
            if batch["timer"]:
                batch["timer"].cancel()
            batch["timer"] = asyncio.get_running_loop().call_later(wait or EDIT_WINDOW, self.submit_edit, key)
        batch["patch"].update(deepcopy(payload["patch"]))
        batch["requests"].append((ctx, action, payload["requestId"]))
        if wait:
            self.spawn(self.to_inspector(ctx, {"type": "uno.waiting", "requestId": payload["requestId"]}, action))

    def live_wait(self, ctx, key):
        """Seconds to wait after the last change of an on-air edit; 0 when off air or for an inactive slot."""
        token, overlay_id, slot_id, number = key
        store = self.stores.get(token)
        if store is None or not store.ready.is_set():
            return 0
        try:
            current = store.slots(overlay_id).get("currentSlotId")
            selected = store.slot(overlay_id, number, slot_id) if number or slot_id else None
            if (selected and selected[1]["id"] != current) or not store.on_air(overlay_id):
                return 0
        except UnoError:
            return 0
        own = str(self.settings.get(ctx, {}).get("liveEditDelay") or "").strip()  # optional per key
        value = own if own else self.global_settings.get("liveEditDelay")
        return max(0, min(10000, integer(value, LIVE_EDIT_DELAY))) / 1000

    def submit_edit(self, key):
        batch = self.edits.pop(key, None)
        if batch is None:
            return
        batch["timer"].cancel()
        self.submit(lambda job: self.run_edit(key, batch), token=key[0], overlay=key[1])

    def flush_edits(self, token=None, owner=None):
        """Edits still waiting go into the queue now: before a key's action (its token), when an inspector
        closes or another field gets the focus (owner), and on Panic (all). Nothing typed is lost."""
        for key, batch in list(self.edits.items()):
            if (token is None or key[0] == token) and (owner is None or any(r[0] == owner for r in batch["requests"])):
                self.submit_edit(key)

    def check_edits(self, token):
        for key, error in self.edit_errors.items():
            if key[0] == token:
                raise UnoError(error)

    async def run_edit(self, key, batch):
        token, overlay_id, slot_id, number = key
        try:
            api = self.api(token)
            store = await self.store(token)
            await self.write_content(api, store, overlay_id, batch["patch"], number, slot_id)
            data, error = {"saved": True}, None
            self.edit_errors.pop(key, None)
            self.failed_patches.pop(key, None)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: shown to the user as a safe message
            data = None
            error = str(exc) if isinstance(exc, UnoError) else tr("Unable to save UNO content. Reload to verify.")
            log.warning("UNO save failed: %s", error if isinstance(exc, UnoError) else type(exc).__name__)
            self.edit_errors[key] = error
            self.failed_patches[key] = deepcopy(batch["patch"])
        for owner, action_id, request_id in batch["requests"]:
            await self.to_inspector(
                owner, {"type": "uno.result", "requestId": request_id, "data": data, "error": error}, action_id
            )

    async def change_slot(self, payload):
        token, overlay_id = payload.get("token"), payload.get("id")
        self.check_edits(token)
        store = await self.store(token)
        slots = store.slots(overlay_id)
        items = slots["data"]
        slot_id, operation = payload.get("slotId"), payload.get("operation")
        existing = next((item for item in items if isinstance(item, dict) and item.get("id") == slot_id), None)
        if operation == "add" and not existing and isinstance(payload.get("content"), dict):
            component(slot_id)
            items.append({"id": slot_id, "name": str(payload.get("name") or "New Slot"), "payload": payload["content"]})
            slots["active"] = True
        elif operation == "rename" and existing:
            existing["name"] = str(payload.get("name") or "Slot")
        elif operation == "remove" and existing:
            slots["data"] = [item for item in items if item is not existing]
            if slots.get("currentSlotId") == slot_id:
                slots["currentSlotId"] = ""
        else:
            raise UnoError(tr("The slot changed or the operation is invalid. Reload the slots."))
        await store.write({"storage.Slots." + component(overlay_id): slots})
        return store.slots(overlay_id)
