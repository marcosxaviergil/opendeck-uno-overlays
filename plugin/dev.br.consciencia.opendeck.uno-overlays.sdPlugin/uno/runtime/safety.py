"""Safety and diagnostics: Lock Desk, confirm with a second press, Status key, API count and log."""

import asyncio
import time
from collections import deque

from uno.api import UnoError
from uno.automations import app_id
from uno.i18n import tr
from uno.runtime.queue import READ
from uno.values import integer, number

__all__ = ["FREE_CAP", "INPUT", "NO_CONFIRM", "STATUS_COLORS", "Counted", "SafetyMixin"]

INPUT = ("keyDown", "keyUp", "dialDown", "dialUp", "dialRotate")
NO_CONFIRM = ("shift", "reset", "lockdesk")
FREE_CAP = 10000  # uno Stream Deck plugin v2 article: "free users who have a 10,000-call daily cap"
# Companion "Connection: Check Status" default colors (foreground, background); None = disabled.
STATUS_COLORS = {
    "good": ("#FFFFFF", "#00C800"),
    "warning": ("#000000", "#FFFF00"),
    "error": ("#FFFFFF", "#C80000"),
    None: ("#999999", "#404040"),
}


class SafetyMixin:
    def _init_safety(self):
        self.desk_locked, self.unlock_hold, self.lock_task, self.last_input = False, None, None, time.monotonic()
        self.armed, self.arm_task, self.status_task = {}, None, None
        self.log, self.api_state, self.calls_timer = deque(maxlen=200), {}, None

    async def locked_out(self, ctx, kind, event):
        """True when the event is used up here: the Lock Desk key itself, or any control while locked."""
        if event not in INPUT:
            return False
        self.last_input = time.monotonic()
        if kind == "lockdesk":
            await self.lock_key(event)
            return True
        if self.desk_locked and event in ("keyDown", "dialDown", "dialRotate"):
            await self.message("showAlert", ctx)  # Companion lockout: controls are ignored until unlocked
        return self.desk_locked

    def confirmed(self, ctx, kind, settings):
        """Optional per key: the first press arms it (it blinks); a second press within the time runs it."""
        wait = float(number(settings.get("confirmSeconds")))
        if wait <= 0 or kind in NO_CONFIRM:
            return True
        now = time.monotonic()
        if self.armed.pop(ctx, 0) >= now:
            return True
        self.armed[ctx] = now + wait
        if self.arm_task is None or self.arm_task.done():
            self.arm_task = self.spawn(self.arm_tick())
        return False

    async def lock_key(self, event):
        """Tap locks every key and knob of the plugin; while locked, hold this key 2 s to unlock."""
        if event == "keyDown" and not self.desk_locked:
            self.lock_desk(True)
        elif event == "keyDown":
            self.unlock_hold = asyncio.get_running_loop().call_later(2, self.lock_desk, False)
        elif event == "keyUp" and self.unlock_hold:
            self.unlock_hold.cancel()
            self.unlock_hold = None
        await self.repaint()

    def lock_desk(self, locked):
        self.desk_locked, self.unlock_hold = locked, None
        if locked:  # held Shift/Reset and armed keys do not survive a lock
            self.shifts.clear()
            for handle in self.holds.values():
                handle.cancel()
            self.holds.clear()
            self.armed.clear()
        self.note(tr("Desk locked.") if locked else tr("Desk unlocked."))
        self.spawn(self.repaint())

    def watch_lock(self):
        if number(self.global_settings.get("lockAfter")) > 0 and (self.lock_task is None or self.lock_task.done()):
            self.lock_task = self.spawn(self.lock_watch())

    async def lock_watch(self):
        # Companion "Pin Timeout": seconds of inactivity before the desk locks (0 = off). Only with
        # a Lock Desk key on a device, so there is always a way to unlock.
        while (after := float(number(self.global_settings.get("lockAfter")))) > 0:
            if (
                not self.desk_locked
                and time.monotonic() - self.last_input >= after
                and any(action.endswith(".lockdesk") for action in self.actions.values())
            ):
                self.lock_desk(True)
            await asyncio.sleep(1)

    async def arm_tick(self):
        shown = set()
        while True:
            now = time.monotonic()
            for ctx in [ctx for ctx, until in self.armed.items() if until <= now]:
                del self.armed[ctx]  # no second press in time: disarm
            await self.repaint(shown | set(self.armed))
            if not self.armed:
                return
            shown = set(self.armed)
            await asyncio.sleep(0.25)

    def status(self):
        """Companion "Connection: Check Status" with All: any error, else any warning, else OK."""
        calls = self.global_settings.get("apiCalls") or {}
        counts = calls.get("counts", {}) if calls.get("date") == time.strftime("%Y-%m-%d") else {}
        cap = integer(self.global_settings.get("apiCap"), FREE_CAP)
        items = []
        for token in self.tokens_in_use():
            store, app, error = self.stores.get(token), app_id(token), self.api_state.get(token)
            realtime = None if store is None else tr("connected") if store.ready.is_set() else store.error
            count = counts.get(app, 0)
            # Companion: connecting / disconnected / failure are errors; near the daily cap is our warning.
            level = (
                "error"
                if error or (store is not None and not store.ready.is_set())
                else "warning"
                if cap and count >= cap * 0.9
                else "good"
                if store is not None or error == ""
                else None
            )
            api = error or (tr("OK") if error == "" else tr("no request yet"))
            items.append(
                {
                    "name": self.app_name(app),
                    "level": level,
                    "calls": count,
                    "detail": tr(
                        "realtime: {realtime} · API: {api} · {count} calls today",
                        realtime=realtime or tr("not started"),
                        api=api,
                        count=count,
                    ),
                }
            )
        if self.global_settings.get("obsEnabled"):
            connected = bool(self.obs and self.obs.connected)
            items.append(
                {
                    "name": "OBS",
                    "level": "good" if connected else "error",
                    "detail": tr("connected") if connected else tr("not connected (Plugins → UNO Overlays → Settings)"),
                }
            )
        levels = {item["level"] for item in items}
        category = next((level for level in ("error", "warning", "good") if level in levels), None)
        return {"category": category, "items": items, "calls": sum(counts.values()), "cap": cap}

    def app_name(self, app):
        """The saved control app name, with its anonymous id only as a fallback (never the token)."""
        name = str(((self.global_settings.get("controlApps") or {}).get(app) or {}).get("name") or "").strip()
        return name or tr("UNO app {app}", app=app)

    def watch_status(self):
        if self.status_task is None or self.status_task.done():
            self.status_task = self.spawn(self.status_tick())

    async def status_tick(self):
        while any(action.endswith(".status") for action in self.actions.values()):
            await self.repaint([ctx for ctx, action in list(self.actions.items()) if action.endswith(".status")])
            await asyncio.sleep(1)

    def tokens_in_use(self):
        """Registered control apps (also of keys not visible now), visible keys, open stores, definitions."""
        tokens = {str(s.get("token") or "").strip() for s in self.settings.values()} | set(self.stores)
        tokens |= set(self.apps().values())
        for kind in ("dataSources", "polls", "goals"):
            tokens |= {
                str(d.get("token") or "").strip()
                for d in (self.global_settings.get(kind) or {}).values()
                if isinstance(d, dict)
            }
        return sorted(token for token in tokens if token)

    async def run_test(self):
        """Connection test: one GetOverlays per control app, its realtime copy and OBS GetVersion."""
        results = []
        for token in self.tokens_in_use():
            app, started = app_id(token), time.monotonic()
            try:
                api = self.api(token)
                overlays = await self.run_job(
                    lambda job, api=api: api.call("GetOverlays"), token=token, priority=READ, barrier=False
                )
                elapsed = int((time.monotonic() - started) * 1000)
                text = tr("API OK ({count} overlays, {ms} ms)", count=len(overlays or []), ms=elapsed)
            except UnoError as exc:
                text = f"API: {exc}"
            try:
                await self.store(token)
                text += " · " + tr("realtime connected")
            except UnoError as exc:
                text += " · " + tr("realtime: {error}", error=exc)
            results.append(f"{self.app_name(app)}: {text}")
        if self.global_settings.get("obsEnabled"):
            try:
                version = await self.obs.request("GetVersion") if self.obs else {}
                results.append(f"OBS {version.get('obsVersion')} · obs-websocket {version.get('obsWebSocketVersion')}")
            except UnoError as exc:
                results.append(f"OBS: {exc}")
        for line in results or [tr("Nothing to test: no API token or OBS connection is configured.")]:
            self.note(tr("Test: {line}", line=line))
        await self.repaint()
        return results

    def called(self, token, command, overlay_id, started, error=None):
        """Every App API request counts toward today (local day: UNO does not say when its day resets)."""
        today, app = time.strftime("%Y-%m-%d"), app_id(token)
        calls = self.global_settings.get("apiCalls") or {}
        if calls.get("date") != today:
            calls = {"date": today, "counts": {}}
        calls["counts"][app] = calls["counts"].get(app, 0) + 1
        self.global_settings["apiCalls"] = calls
        self.api_state[token] = str(error or "")
        where = f" {overlay_id}" if overlay_id else ""
        elapsed = int((time.monotonic() - started) * 1000)
        self.note(f"{self.app_name(app)}: {command}{where} → {error or tr('OK')} ({elapsed} ms)")
        if self.calls_timer is None:  # saved in the global settings at most every 10 s
            self.calls_timer = asyncio.get_running_loop().call_later(10, self.save_calls)

    def save_calls(self):
        self.calls_timer = None
        self.spawn(self.message("setGlobalSettings", self.plugin_uuid, self.global_settings))

    def note(self, text):
        self.log.append(f"{time.strftime('%H:%M:%S')}  {text}")


class Counted:
    """App API client that reports each request (count per day, last result, log)."""

    def __init__(self, api, runtime):
        self.api, self.runtime, self.token = api, runtime, api.token

    async def metadata(self):
        method = getattr(self.api, "metadata", None)
        return await method() if method else {}

    async def call(self, command, **values):
        started = time.monotonic()
        try:
            result = await self.api.call(command, **values)
        except UnoError as exc:
            self.runtime.called(self.token, command, values.get("id"), started, exc)
            raise
        self.runtime.called(self.token, command, values.get("id"), started)
        return result