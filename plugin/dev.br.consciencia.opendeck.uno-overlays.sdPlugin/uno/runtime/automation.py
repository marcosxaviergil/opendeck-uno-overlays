"""Global automations: control app registry, triggers, exclusive groups and remembered key settings.

Everything here works with no key visible (uno.automations explains why it is global). Each automatic
path writes to the log, at INFO and without tokens or field content: the event received, the
decision for each trigger (fired or ignored, and why) and the UNO result.
"""

import asyncio
import logging
from copy import deepcopy

from uno.api import UnoError, token_value
from uno.automations import (
    OBS_EVENTS,
    UNO_EVENTS,
    app_id,
    clean_group,
    clean_trigger,
    group_delay,
    key_triggers,
    merge_triggers,
    strip_legacy,
)
from uno.i18n import tr

__all__ = ["AUTOMATION", "AutomationMixin"]

log = logging.getLogger(__name__)

AUTOMATION = "automation"  # owner of queued automation jobs: not an OpenDeck context
SAVE_AFTER = 0.5  # seconds: many keys appearing at start become one setGlobalSettings
MAX_APP_NAME = 60
LABELS = {
    "obsIn": "scene goes to program",
    "obsOut": "scene leaves program",
    "obsStreamStart": "streaming starts",
    "obsStreamStop": "streaming stops",
    "obsRecordStart": "recording starts",
    "obsRecordStop": "recording stops",
    "unoIn": "overlay goes on air",
    "unoOut": "overlay goes off air",
}


class AutomationMixin:
    def _init_automation(self):
        self.save_timer, self.known = None, {}  # known: last settings of every context seen this run
        self.app_name_lookups = set()

    # ── registry of control apps ──────────────────────────────────────────

    def apps(self):
        """Registered control apps: id → token (Status, Panic, Restore, triggers, groups)."""
        apps = self.global_settings.get("controlApps")
        return {
            app: str(entry.get("token") or "")
            for app, entry in (apps if isinstance(apps, dict) else {}).items()
            if isinstance(entry, dict) and entry.get("token")
        }

    def token_of(self, app):
        return self.apps().get(app, "")

    def register(self, token):
        """Remember a control app whose token worked (its datastore connected), for keys not visible."""
        try:
            token = token_value(token)
        except UnoError:
            return
        apps, app = self.global_settings.setdefault("controlApps", {}), app_id(token)
        if apps.get(app, {}).get("token") != token:
            apps[app] = {"token": token, "name": (apps.get(app) or {}).get("name", "")}
            log.info("Control app %s registered for global use.", app)
            self.persist()
        if not str((apps.get(app) or {}).get("name") or "").strip() and app not in self.app_name_lookups:
            self.app_name_lookups.add(app)
            task = self.spawn(self.refresh_app_name(token))
            task.add_done_callback(lambda _task, app=app: self.app_name_lookups.discard(app))

    async def refresh_app_name(self, token):
        """Fill an unnamed registered control app from its official UNO metadata without replacing a manual name."""
        try:
            token = token_value(token)
        except UnoError:
            return ""
        app = app_id(token)
        entry = (self.global_settings.get("controlApps") or {}).get(app)
        if not isinstance(entry, dict) or entry.get("token") != token:
            return ""
        current = str(entry.get("name") or "").strip()
        if current:
            return current
        try:
            metadata = await self.api(token).metadata()
        except UnoError as exc:
            log.info("Control app %s metadata name unavailable: %s", app, exc)
            return ""
        name = str((metadata or {}).get("name") or "").strip()[:MAX_APP_NAME]
        entry = (self.global_settings.get("controlApps") or {}).get(app)
        if name and isinstance(entry, dict) and entry.get("token") == token and not str(entry.get("name") or "").strip():
            entry["name"] = name
            log.info("Control app %s name loaded from UNO metadata.", app)
            self.persist()
            return name
        return str((entry or {}).get("name") or "").strip() if isinstance(entry, dict) else ""

    async def refresh_app_names(self):
        """Load official names only for registered control apps that still have no saved name."""
        apps = self.global_settings.get("controlApps") or {}
        await asyncio.gather(
            *(
                self.refresh_app_name(str(entry.get("token") or ""))
                for entry in list(apps.values())
                if isinstance(entry, dict) and entry.get("token") and not str(entry.get("name") or "").strip()
            )
        )

    def persist(self):
        """Save the global settings soon; changes made meanwhile go in the same message."""
        if self.save_timer is None:
            self.save_timer = asyncio.get_running_loop().call_later(SAVE_AFTER, self.save_now)

    def save_now(self):
        self.save_timer = None
        self.spawn(self.message("setGlobalSettings", self.plugin_uuid, self.global_settings))

    def watch_global(self):
        """Realtime copies for the apps that global triggers and groups watch (tally, OnOverlayIn/Out)."""
        wanted = {t["sourceApp"] for t in self.trigger_list() if t["event"] in UNO_EVENTS}
        for group in (self.global_settings.get("groups") or {}).values():
            wanted |= {member["app"] for member in clean_group(group)["members"]}
        for app in wanted:
            token = self.token_of(app)
            if token and token not in self.stores:
                self.spawn(self.watch(token, register=False))

    # ── triggers ──────────────────────────────────────────────────────────

    def trigger_list(self):
        return [t for t in (clean_trigger(raw) for raw in self.global_settings.get("triggers") or []) if t]

    async def obs_event(self, kind, before):
        """obs-websocket event: every global trigger is evaluated, whatever key is visible."""
        obs = self.obs
        log.info(
            "OBS event %s: program scene %r (before %r), streaming %s, recording %s.",
            kind,
            obs.scene,
            before,
            obs.streaming,
            obs.recording,
        )
        if kind in ("CurrentProgramSceneChanged", "StreamStateChanged", "RecordStateChanged"):
            happened = {
                "CurrentProgramSceneChanged": {"obsIn": obs.scene, "obsOut": before},
                "StreamStateChanged": {"obsStreamStart" if obs.streaming else "obsStreamStop": True},
                "RecordStateChanged": {"obsRecordStart" if obs.recording else "obsRecordStop": True},
            }[kind]
            for number, t in enumerate(self.trigger_list(), 1):
                if t["event"] not in OBS_EVENTS:
                    continue
                reason = self.obs_mismatch(t, happened)
                self.decide(number, t, reason)
        await self.repaint()

    @staticmethod
    def obs_mismatch(t, happened):
        if t["event"] not in happened:
            return "other event"
        if t["event"] in ("obsIn", "obsOut") and happened[t["event"]] != t["scene"]:
            return f"scene is not {t['scene']!r}"
        return ""

    def uno_changed(self, store):
        """vMix OnOverlayIn/Out from the global list: fire on a change, not on the first reading."""
        app = app_id(store.token)
        sources = {
            t["sourceOverlay"] for t in self.trigger_list() if t["event"] in UNO_EVENTS and t["sourceApp"] == app
        }
        for overlay in sorted(sources):
            try:
                now = store.on_air(overlay)
            except UnoError:
                continue
            before, self.air[(store.token, overlay)] = self.air.get((store.token, overlay)), now
            if before is None or before == now:
                continue
            event = "unoIn" if now else "unoOut"
            log.info("UNO event: overlay %s of app %s went %s.", overlay, app, "on air" if now else "off air")
            for number, t in enumerate(self.trigger_list(), 1):
                if t["event"] in UNO_EVENTS and t["sourceApp"] == app and t["sourceOverlay"] == overlay:
                    self.decide(number, t, "" if t["event"] == event else "other event")

    def decide(self, number, t, reason):
        where = f"#{number} ({LABELS[t['event']]}{' ' + repr(t['scene']) if t['scene'] else ''})"
        if not reason and not t["on"]:
            reason = "switched off"
        if not reason and not self.token_of(t["app"]):
            reason = f"control app {t['app']} is not registered (Plugins → UNO Overlays → Settings)"
        if not reason and not t["overlay"]:
            reason = "no overlay chosen"
        if reason:
            log.info("Trigger %s ignored: %s.", where, reason)
            return
        log.info(
            "Trigger %s fired: %s overlay %s of app %s in %d ms.",
            where,
            t["function"],
            t["overlay"],
            t["app"],
            t["delay"],
        )
        self.note(
            tr("Trigger {number}: {function} {overlay}", number=number, function=t["function"], overlay=t["overlay"])
        )
        self.run_later(
            self.api(self.token_of(t["app"])),
            t["function"],
            t["overlay"],
            t["delay"],
            f"Trigger {where}",
            t["slotNumber"],
            t["serverSlotId"],
            t["autoClose"],
        )

    def run_later(self, api, function, target, delay_ms, label, slot_number=0, slot_id="", auto_close=0):
        """Show or hide `target` after `delay_ms` (vMix: Delay up to 30 000 ms). Panic cancels the wait.

        No key owns it: a failure goes to the log and the Status log, never to a key's alert."""

        async def run(job):
            self.cancel_hide(api.token, target)
            command = "ShowOverlay" if function == "show" else "HideOverlay"
            try:
                if function == "show":
                    if slot_number or slot_id:
                        store = await self.store(api.token)
                        index, _ = store.slot(target, slot_number, slot_id)
                        await api.call("TakeOverlaySlotNumber", id=target, value=index + 1)
                    await self.show(api, target)
                    self.schedule_hide(AUTOMATION, api, target, auto_close)
                else:
                    await api.call("HideOverlay", id=target)
            except Exception as exc:  # noqa: BLE001 - boundary: an automation has no key to show the error
                text = str(exc) if isinstance(exc, UnoError) else type(exc).__name__
                log.warning("%s: %s %s → %s", label, command, target, text)
                self.note(f"{label}: {text}")
                return
            log.info("%s: %s %s → OK.", label, command, target)

        def due():
            self.triggers.discard(handle)
            self.submit(run, owners={AUTOMATION}, token=api.token, overlay=target)  # Panic drops it like a key's job

        handle = asyncio.get_running_loop().call_later(max(0, min(30000, delay_ms)) / 1000, due)
        self.triggers.add(handle)

    # ── exclusive groups ──────────────────────────────────────────────────

    def group_of(self, token, overlay_id):
        """(name, delay, other members as (token, overlay)) of the global group holding this overlay."""
        app = app_id(token)
        for name, raw in sorted((self.global_settings.get("groups") or {}).items()):
            group = clean_group(raw)
            if {"app": app, "overlay": overlay_id} in group["members"]:
                others = [
                    (self.token_of(m["app"]), m["overlay"])
                    for m in group["members"]
                    if (m["app"], m["overlay"]) != (app, overlay_id) and self.token_of(m["app"])
                ]
                return name, group["delay"], others
        return None, 0.0, []

    def join_group(self, token, overlay_id, name, delay=None):
        """An overlay is in one group at most (a Singular logic layer); empty name leaves its group."""
        groups, app, changed = self.global_settings.setdefault("groups", {}), app_id(token), False
        for other in list(groups):
            group = clean_group(groups[other])
            member = {"app": app, "overlay": overlay_id}
            if other != name and member in group["members"]:
                group["members"].remove(member)
                groups[other], changed = group, True
        if name:
            group = clean_group(groups.get(name)) if name in groups else clean_group({"delay": delay})
            if {"app": app, "overlay": overlay_id} not in group["members"]:
                group["members"].append({"app": app, "overlay": overlay_id})
                groups[name], changed = group, True
                log.info("Overlay %s of app %s joined the exclusive group %r.", overlay_id, app, name)
        if changed:
            self.persist()

    # ── keys: migration and remembered settings ───────────────────────────

    async def adopt_key(self, ctx, action, settings, previous):
        """Settings a key carries that belong to the plugin: move them to the global settings.

        Returns the key settings to keep. Old trigger fields and the group time go to the global
        lists (without duplicates) and are removed from the key with setSettings, so there is one source.
        """
        kind, token = action.rsplit(".", 1)[-1], str(settings.get("token") or "").strip()
        try:
            app = app_id(token_value(token))
        except UnoError:
            return settings
        if kind == "toggle" and settings.get("overlayId"):
            new = key_triggers(settings, app)
            if new:
                merged, added = merge_triggers(self.global_settings.get("triggers"), new)
                if added:
                    self.global_settings["triggers"] = merged
                    self.register(token)
                    log.info("Moved %d trigger(s) of an Overlay key to the global list.", added)
                    self.persist()
            name = str(settings.get("group") or "").strip()
            was = str((previous or {}).get("group") or "").strip()
            moved = (previous or {}).get("overlayId") not in (None, settings["overlayId"])
            if was and moved:  # the key now shows another overlay: the old one leaves the group
                self.join_group(token, previous["overlayId"], "")
            if name or was:
                delay = group_delay(settings.get("groupDelay")) if "groupDelay" in settings else None
                self.join_group(token, settings["overlayId"], name, delay)
        if kind == "clock" and settings.get("fieldComposite"):
            self.remember_config("clockConfigs", app, settings)
        if kind == "reveal" and settings.get("fieldComposite"):
            self.remember_config("revealConfigs", app, settings)
        kept = strip_legacy(settings)
        if kept != settings:
            self.settings[ctx] = self.known[ctx] = kept  # the echo of setSettings is then no change
            await self.message("setSettings", ctx, kept)
            log.info("Removed the fields that moved to the global settings from one %s key.", kind)
        return kept

    def remember_config(self, kind, app, settings):
        """Settings of a Clock or Reveal key, by field: used when no such key is visible."""
        configs = self.global_settings.setdefault(kind, {})
        config = {key: deepcopy(value) for key, value in settings.items() if key != "token"}
        key = f"{app}::{settings['fieldComposite']}"
        if configs.get(key) != {**config, "app": app}:
            configs[key] = {**config, "app": app}
            self.persist()

    def remembered(self, kind, token, field):
        config = (self.global_settings.get(kind) or {}).get(f"{app_id(token)}::{field}")
        return {**config, "token": token} if isinstance(config, dict) else None