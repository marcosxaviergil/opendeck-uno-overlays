"""Plugin settings (OpenDeck: Plugins → UNO Overlays → Settings): what every key shares.

OBS connection, language, live edit delay, the registry of control apps, global triggers and exclusive
groups. Tokens and the OBS password go in only: the page receives control app ids (a hash prefix) and
names, never a token, and only "a password is saved".
"""

import asyncio
import logging
import pathlib

from uno.api import UnoError, token_value
from uno.automations import app_id, clean_group, clean_trigger
from uno.i18n import LANGUAGES, opendeck_language, tr
from uno.localpage import LocalPage
from uno.obs import check_address
from uno.runtime.content import LIVE_EDIT_DELAY
from uno.runtime.queue import READ
from uno.values import integer

__all__ = ["OBS_KEYS", "PAGE_KEYS", "SettingsPageMixin"]

log = logging.getLogger(__name__)

PAGE = pathlib.Path(__file__).resolve().parents[2] / "pi"
OBS_KEYS = ("obsEnabled", "obsHost", "obsPort", "obsPassword")  # written only here and by a backup import
PAGE_KEYS = ("language", "liveEditDelay", "controlApps", "triggers", "groups")
MAX_TRIGGERS, MAX_GROUPS, MAX_NAME = 200, 50, 60


class SettingsPageMixin:
    def _init_settings_page(self):
        self.page = LocalPage(
            PAGE,
            {
                ("GET", "/api/settings"): self.settings_state,
                ("POST", "/api/settings"): self.save_settings,
                ("POST", "/api/overlays"): self.page_overlays,
                ("POST", "/api/slots"): self.page_slots,
                ("POST", "/api/obs"): self.page_obs,
            },
        )

    async def show_settings(self):
        opened = await asyncio.to_thread(self.page.open, asyncio.get_running_loop())
        self.note(
            tr("Settings page opened in the browser.") if opened else tr("No web browser found to open the settings.")
        )

    async def settings_state(self):
        await self.refresh_app_names()
        g, connected = self.global_settings, bool(self.obs and self.obs.connected)
        if self.refresh_language():  # OpenDeck's language may have changed since the last look
            await self.repaint()
        status = "off" if not g.get("obsEnabled") else "connected" if connected else "not connected"
        obs = {
            "enabled": bool(g.get("obsEnabled")),
            "host": g.get("obsHost") or "127.0.0.1",
            "port": integer(g.get("obsPort"), 4455),
            "hasPassword": bool(g.get("obsPassword")),  # the password itself never leaves the plugin
        }
        apps = g.get("controlApps") or {}
        return {
            "obs": obs,
            "status": status,
            "language": {"choice": g.get("language") or "", "current": self.language, "opendeck": opendeck_language()},
            "liveEditDelay": max(0, min(10000, integer(g.get("liveEditDelay"), LIVE_EDIT_DELAY))),
            "apps": [{"id": app, "name": str((entry or {}).get("name") or "")} for app, entry in sorted(apps.items())],
            "triggers": self.trigger_list(),
            "groups": {name: clean_group(group) for name, group in sorted((g.get("groups") or {}).items())},
        }

    async def save_settings(self, data):
        """Each section present in `data` is replaced; the others stay as they are."""
        changes, notes = {}, []
        if data.get("addToken"):  # first: a token UNO refuses stops here, before anything changes
            await self.add_app(str(data["addToken"]), str(data.get("addName") or ""))
            notes.append("Control app added.")
        if isinstance(data.get("obs"), dict):
            changes.update(self.obs_changes(data["obs"]))
            notes.append("OBS settings saved.")
        if "language" in data:
            choice = data["language"] if data["language"] in LANGUAGES else ""
            changes["language"] = choice
            notes.append("Language saved.")
        if "liveEditDelay" in data:
            changes["liveEditDelay"] = max(0, min(10000, integer(data["liveEditDelay"], LIVE_EDIT_DELAY)))
            notes.append("Live edit delay saved.")
        if isinstance(data.get("triggers"), list):
            changes["triggers"] = [t for t in map(clean_trigger, data["triggers"][:MAX_TRIGGERS]) if t]
            notes.append("Triggers saved.")
        if isinstance(data.get("groups"), dict):
            changes["groups"] = {
                str(name).strip()[:MAX_NAME]: clean_group(group)
                for name, group in list(data["groups"].items())[:MAX_GROUPS]
                if str(name).strip()
            }
            notes.append("Groups saved.")
        if isinstance(data.get("apps"), list):
            changes["controlApps"] = self.apps_changes(data["apps"])
            notes.append("Control apps saved.")
        self.global_settings.update(changes)
        await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
        await self.configure_obs()
        if self.refresh_language() or "liveEditDelay" in changes:
            await self.repaint()
        self.watch_global()
        for text in notes:
            self.note(tr(text))
            log.info("Settings page: %s", text)
        return await self.settings_state()

    def obs_changes(self, obs):
        host, port = str(obs.get("host") or "").strip() or "127.0.0.1", integer(obs.get("port"))
        password = obs.get("password") if isinstance(obs.get("password"), str) else ""
        check_address(host, port)
        if len(password) > 256:
            raise UnoError(tr("The OBS password is too long."))
        # JSON true only: the text "false" would count as on.
        changes = {"obsEnabled": obs.get("enabled") is True, "obsHost": host, "obsPort": str(port)}
        if obs.get("clearPassword") is True:
            changes["obsPassword"] = ""
        elif password:  # empty keeps the saved password, which the page never receives
            changes["obsPassword"] = password
        return changes

    def apps_changes(self, apps):
        """Rename or forget registered control apps; an app left out of the list is forgotten."""
        current = self.global_settings.get("controlApps") or {}
        names = {str(a.get("id")): str(a.get("name") or "").strip()[:MAX_NAME] for a in apps if isinstance(a, dict)}
        return {app: {**entry, "name": names[app]} for app, entry in current.items() if app in names}

    async def add_app(self, token, name):
        """A control app typed on the page: one GetOverlays proves the token before it is kept."""
        token = token_value(token)
        api = self.api(token)
        await self.run_job(lambda job: api.call("GetOverlays"), token=token, priority=READ, barrier=False)
        manual_name = name.strip()[:MAX_NAME]
        remote_name = ""
        if not manual_name:
            try:
                metadata = await api.metadata()
                remote_name = str((metadata or {}).get("name") or "").strip()[:MAX_NAME]
            except UnoError:
                pass
        self.register(token)
        entry = self.global_settings["controlApps"][app_id(token)]
        entry["name"] = manual_name or remote_name or entry.get("name", "")

    async def page_overlays(self, data):
        """Overlays of a registered control app, for the trigger and group lists (names and ids only)."""
        token = self.token_of(str(data.get("app") or ""))
        if not token:
            raise UnoError(tr("This control app is not registered. Add its token above."))
        api = self.api(token)
        overlays = await self.run_job(lambda job: api.call("GetOverlays"), token=token, priority=READ, barrier=False)
        return [{"id": str(o.get("id")), "name": str(o.get("name") or o.get("id"))} for o in overlays or []]

    async def page_slots(self, data):
        """Server slots of one overlay, for global trigger targets (names and stable ids only)."""
        token = self.token_of(str(data.get("app") or ""))
        overlay_id = str(data.get("overlay") or "")
        if not token:
            raise UnoError(tr("This control app is not registered. Add its token above."))
        if not overlay_id:
            return []
        store = await self.store(token)
        return [
            {"id": str(slot.get("id") or ""), "name": str(slot.get("name") or "")}
            for slot in store.slots(overlay_id).get("data") or []
            if isinstance(slot, dict)
        ]

    async def page_obs(self, data):
        return await self.run_job(lambda job: self.obs_lists(), priority=READ)
