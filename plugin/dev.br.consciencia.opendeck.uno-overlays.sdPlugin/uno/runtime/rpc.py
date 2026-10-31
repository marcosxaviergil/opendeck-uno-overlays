"""Requests from the property inspector (sendToPlugin): reads, slots, previews, status and backup.

Every request is answered with {"type": "uno.result", "requestId", "data" | "error"}. Errors
shown to the inspector are the plugin's own messages; anything unexpected stays generic.
"""

import asyncio
import logging

from uno.api import UnoError
from uno.backup import export, restore
from uno.i18n import tr
from uno.runtime.queue import READ
from uno.sources import table

log = logging.getLogger(__name__)

__all__ = ["RpcMixin"]


class RpcMixin:
    async def rpc(self, ctx, action, payload):
        handler = {
            "uno.read": self.rpc_read,
            "uno.slot": self.rpc_slot,
            "obs.list": self.page_obs,  # the same lists as the settings page
            "source.preview": self.rpc_preview,
            "status.get": self.rpc_status,
            "status.test": lambda payload: self.run_test(),
            "backup.export": self.rpc_export,
            "backup.import": self.rpc_import,
            "log.clear": self.rpc_clear_log,
            "scene.delete": self.rpc_delete_scene,
            "i18n.get": self.rpc_language,
        }.get(payload.get("type"))
        if handler is None or not isinstance(payload.get("requestId"), str):
            return
        result = {"type": "uno.result", "requestId": payload["requestId"]}
        try:
            result["data"] = await handler(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: answered to the inspector as a safe message
            result["error"] = str(exc) if isinstance(exc, UnoError) else tr("Unable to read UNO data.")
            log.warning(
                "UNO inspector request failed: %s", result["error"] if isinstance(exc, UnoError) else type(exc).__name__
            )
        await self.to_inspector(ctx, result, action)

    async def rpc_read(self, payload):
        command, overlay_id = payload.get("command"), payload.get("id")
        if command in ("GetOverlayContent", "GetSlots"):
            store = await self.store(payload.get("token"))  # local copy, no site request
            return store.content(overlay_id) if command == "GetOverlayContent" else store.slots(overlay_id)
        if command not in ("GetOverlays", "GetOverlayModel"):
            raise UnoError(tr("This inspector request is not supported."))
        api = self.api(payload.get("token"))
        values = {} if command == "GetOverlays" else {"id": overlay_id or ""}
        if values and not values["id"]:
            raise UnoError(tr("Select an overlay."))
        return await self.run_job(
            lambda job: api.call(command, **values), token=api.token, priority=READ, barrier=False
        )

    async def rpc_slot(self, payload):
        self.flush_edits(payload.get("token"))
        return await self.run_job(
            lambda job: self.change_slot(payload), token=payload.get("token"), overlay=payload.get("id")
        )

    async def rpc_preview(self, payload):
        """Columns, row count and the first rows of a data source, read by the plugin."""
        names, rows = table(payload.get("definition") or {})
        return {"columns": names, "count": len(rows), "rows": rows[:5]}

    async def rpc_status(self, payload):
        return {**self.status(), "log": list(self.log)[::-1], "locked": self.desk_locked}

    async def rpc_export(self, payload):
        path, count = export(self.global_settings, payload.get("path"), bool(payload.get("secrets")))
        self.note(tr("Backup exported: {count} items.", count=count))
        return {"path": path, "count": count}

    async def rpc_import(self, payload):
        self.global_settings, count = restore(self.global_settings, payload.get("path"), payload.get("token") or "")
        await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
        await self.configure_obs()
        self.note(tr("Backup imported: {count} items.", count=count))
        return {"count": count}

    async def rpc_clear_log(self, payload):
        """LGPD Art. 16: personal data are eliminated after their processing ends; the log also ends with the plugin."""
        self.log.clear()
        return {}

    async def rpc_language(self, payload):
        """The language the inspector draws in. OpenDeck does not tell plugins when its language changes
        (events/frontend/settings.rs only saves it), so each inspector that opens reads it again."""
        if self.refresh_language():
            await self.repaint()
        return {"language": self.language}

    async def rpc_delete_scene(self, payload):
        """LGPD Art. 18: a stored scene holds overlay content (names); the controller can delete it on request."""
        name = str(payload.get("name") or "")
        if (self.global_settings.get("scenes") or {}).pop(name, None) is None:
            raise UnoError(tr("Scene {name} is not stored.", name=repr(name)))
        await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
        self.note(tr("Scene deleted."))
        return {}
