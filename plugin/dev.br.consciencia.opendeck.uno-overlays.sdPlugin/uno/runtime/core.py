"""OpenAction transport and routing: the Runtime receives every OpenDeck event and dispatches it.

Each feature lives in its own mixin module (one reason to change per file); all of them share
this object's state, created by their _init_* methods. Action events run once on Down; Up
never invokes UNO. Every UNO operation goes through the global queue (uno.runtime.queue).
"""

import asyncio
import logging
from copy import deepcopy

from uno import PLUGIN_ID
from uno.api import UnoAPI, UnoError
from uno.backup import LIVE as GOAL_STATE  # start, end and reached: set by the plugin only
from uno.datastore import Datastore
from uno.i18n import resolve, set_language, tr
from uno.runtime.automation import AUTOMATION, AutomationMixin
from uno.runtime.clocks import ClockMixin
from uno.runtime.content import ContentMixin
from uno.runtime.datasources import DataSourceMixin
from uno.runtime.derived import DerivedMixin
from uno.runtime.dials import DIALS, DialMixin
from uno.runtime.keys import KeyImageMixin
from uno.runtime.numeric import NumericMixin
from uno.runtime.overlays import OverlayMixin
from uno.runtime.queue import QueueMixin
from uno.runtime.reveal import RevealMixin
from uno.runtime.rpc import RpcMixin
from uno.runtime.safety import Counted, SafetyMixin
from uno.runtime.scoreboard import ScoreboardMixin
from uno.runtime.settingspage import OBS_KEYS, PAGE_KEYS, SettingsPageMixin
from uno.runtime.showcontrol import ShowControlMixin
from uno.runtime.triggers import TriggerMixin
from uno.values import composite, integer

log = logging.getLogger(__name__)

__all__ = ["Runtime"]

# Written by the plugin only (settings page, keys it adopts, counters): an inspector's older copy never replaces them.
OWNED = ("scenes", "apiCalls", *OBS_KEYS, *PAGE_KEYS, "clockConfigs", "revealConfigs")
KNOB_KEYS = ("overlayId", "slotNumber", "serverSlotId", "autoClose", "delay", "fieldComposite", "tokens")


class Runtime(
    QueueMixin,
    AutomationMixin,
    ContentMixin,
    RpcMixin,
    OverlayMixin,
    NumericMixin,
    DialMixin,
    KeyImageMixin,
    TriggerMixin,
    ScoreboardMixin,
    ClockMixin,
    DataSourceMixin,
    DerivedMixin,
    SafetyMixin,
    ShowControlMixin,
    SettingsPageMixin,
    RevealMixin,
):
    def __init__(self, send, plugin_uuid, api_factory=UnoAPI, store_factory=Datastore, info=None):
        self.send, self.plugin_uuid = send, plugin_uuid
        application = info.get("application") if isinstance(info, dict) else None  # OpenDeck registration info
        self.info_language = str(application.get("language") or "") if isinstance(application, dict) else ""
        self.api_factory, self.store_factory = api_factory, store_factory
        self.settings, self.actions, self.controllers = {}, {}, {}  # per OpenDeck context
        self.open_inspectors, self.tasks = set(), set()
        self.global_settings, self.loaded, self.multiplier = {}, False, 1
        self._init_queue()
        self._init_automation()
        self._init_content()
        self._init_overlays()
        self._init_dials()
        self._init_keys()
        self._init_triggers()
        self._init_scoreboard()
        self._init_clocks()
        self._init_datasources()
        self._init_derived()
        self._init_safety()
        self._init_showcontrol()
        self._init_settings_page()
        self._init_reveal()
        self.refresh_language()

    # ── OpenDeck events ───────────────────────────────────────────────────

    async def handle(self, msg):
        if not isinstance(msg, dict):
            return
        event, ctx, p = msg.get("event"), msg.get("context"), msg.get("payload") or {}
        if event == "didReceiveGlobalSettings":
            await self.receive_global(p.get("settings") or {})
            return
        if event == "showSettingsInterface":  # the gear in Plugins (manifest HasSettingsInterface)
            await self.show_settings()
            return
        action = msg.get("action") or self.actions.get(ctx, "")
        if not isinstance(ctx, str) or not action.startswith(PLUGIN_ID + "."):
            return
        if event == "propertyInspectorDidAppear":
            self.open_inspectors.add(ctx)
        elif event == "propertyInspectorDidDisappear":
            self.open_inspectors.discard(ctx)
            self.flush_edits(owner=ctx)  # a closed inspector never leaves an edit waiting
        elif event == "willDisappear":
            self.forget(ctx)
        elif event in ("willAppear", "didReceiveSettings"):
            await self.appear(ctx, action, event, p)
        elif event == "sendToPlugin":
            self.open_inspectors.add(ctx)  # requests come from an open inspector
            if p.get("type") == "uno.edit":
                self.queue_edit(ctx, action, p)
            elif p.get("type") == "uno.flush":  # another field got the focus: send what was typed
                self.flush_edits(owner=ctx)
            else:
                self.spawn(self.rpc(ctx, action, p))
        else:
            await self.on_input(ctx, action, event, p)

    async def receive_global(self, settings):
        goals = self.global_settings.get("goals") or {}
        # The first read is the stored copy; after it, the plugin's own keys win over an inspector's copy.
        owned = {key: self.global_settings[key] for key in OWNED if key in self.global_settings and self.loaded}
        self.global_settings, self.loaded = {**deepcopy(settings), **owned}, True
        for name, goal in (self.global_settings.get("goals") or {}).items():
            if isinstance(goal, dict) and name in goals:  # start, end and reached are set by the plugin only
                goal.update({key: goals[name][key] for key in GOAL_STATE if key in goals[name]})
        self.multiplier = max(1, min(50, integer(self.global_settings.get("multiplier"), 1)))
        self.refresh_language()
        await self.configure_obs()
        self.watch_lock()
        self.watch_global()
        await self.repaint()

    def refresh_language(self):
        """Settings page choice, else OpenDeck's language (read again each time: OpenDeck does not say when
        it changes), else the registration info. True when it changed."""
        before = getattr(self, "language", None)
        self.language = set_language(resolve(self.global_settings.get("language"), self.info_language))
        if before not in (None, self.language):
            self.images.clear()  # captions are drawn in the new language
            return True
        return False

    async def appear(self, ctx, action, event, p):
        new = deepcopy(p.get("settings") or {})
        previous = self.known.get(ctx)
        # Only a real change of the key's settings cancels its Auto Close and queued presses; a key that
        # comes back after a profile switch (willDisappear, then willAppear) keeps them.
        changed = new != previous
        if changed:
            self.cancel_context(ctx)
            self.dials.pop(ctx, None)
            new = await self.adopt_key(ctx, action, new, previous)
        self.settings[ctx], self.known[ctx], self.actions[ctx] = new, new, action
        self.controllers[ctx] = p.get("controller") or self.controllers.get(ctx, "Keypad")
        if action.endswith(".display") and (changed or event == "willAppear"):
            self.spawn(self.display(ctx, new)).uno_context = ctx
        if action.endswith(".clock"):
            self.clock_settings(ctx, new)
        if new.get("token"):
            self.spawn(self.watch(new["token"])).uno_context = ctx
        if action.endswith(".status"):
            self.watch_status()
        self.watch_lock()
        await self.repaint()

    def forget(self, ctx):
        """willDisappear: a profile switch, a device that left or a deleted key (OpenDeck does not say
        which). What the key started keeps running: Auto Close, queued presses, trigger delays."""
        self.flush_edits(owner=ctx)
        for per_context in (self.settings, self.actions, self.images, self.controllers, self.dials):
            per_context.pop(ctx, None)
        self.open_inspectors.discard(ctx)
        self.shifts.discard(ctx)

    async def on_input(self, ctx, action, event, p):
        """Keys and knobs: the desk lock first, then held keys, knobs with their own gestures, presses."""
        kind = action.rsplit(".", 1)[-1]
        if await self.locked_out(ctx, kind, event):
            return
        settings = deepcopy(p.get("settings", self.settings.get(ctx, {})))
        if kind in ("shift", "reset") and event in ("keyDown", "keyUp"):
            await self.hold_key(ctx, kind, event, settings)
            return
        if kind in ("clock", "datasource") and event in ("dialDown", "dialRotate"):
            self.settings[ctx] = settings
            await self.knob_function(ctx, kind, event, integer(p.get("ticks")), settings)
            return
        if kind in DIALS and event in ("dialDown", "dialUp", "dialRotate"):
            self.settings[ctx] = settings
            self.spawn(self.guard(ctx, self.dial(ctx, kind, event, integer(p.get("ticks"))))).uno_context = ctx
            return
        if event not in ("keyDown", "dialDown", "dialRotate"):
            return
        self.settings[ctx], self.actions[ctx] = settings, action
        if event == "keyDown" and not self.confirmed(ctx, kind, settings):
            return
        if settings.get("token"):
            self.flush_edits(self.api(settings["token"]).token)  # typing still waiting goes first
        ticks = integer(p.get("ticks"))
        if event == "dialRotate" and not ticks:
            return
        gesture, steps = ("press", 1) if event != "dialRotate" else ("cw" if ticks > 0 else "ccw", abs(ticks))
        if kind == "multiplier":  # local and immediate, so the next key event sees it
            value = (
                integer(settings.get("multiplier"), 1)
                if gesture == "press"
                else self.multiplier + (steps if gesture == "cw" else -steps)
            )
            self.multiplier = max(1, min(50, value))
            self.global_settings["multiplier"] = self.multiplier
            await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
            await self.repaint()  # Numeric Fields keys without a fixed step show the multiplier
            return
        if kind == "display":
            return  # read-only; updates arrive through the datastore
        try:
            self.dispatch(ctx, kind, settings, gesture, steps)
        except Exception as exc:  # noqa: BLE001 - boundary: shown on the key as a safe message
            await self.report(ctx, exc)

    async def hold_key(self, ctx, kind, event, settings):
        if kind == "shift":  # momentary: knobs use their Shift target while any Shift key is held
            (self.shifts.add if event == "keyDown" else self.shifts.discard)(ctx)
            await self.repaint()
            return
        if event == "keyDown":  # Reset: hold two seconds; releasing earlier does nothing
            self.holds[ctx] = asyncio.get_running_loop().call_later(
                2,
                lambda: (
                    self.holds.pop(ctx, None),
                    self.submit(lambda job: self.run_reset(ctx, settings), owners={ctx}),
                ),
            )
        elif self.holds.get(ctx):
            self.holds.pop(ctx).cancel()
        await self.repaint([ctx])

    async def knob_function(self, ctx, kind, event, ticks, settings):
        """Clock knob: turn = AdjustCountdown by the knob step, press = the function. Data Source knob:
        turn = choose a row (Visor), press = select it."""
        try:
            if kind == "clock" and event == "dialRotate":
                self.clock_op(ctx, settings, "adjust", ticks * (integer(settings.get("knobStep"), 10) or 10))
            elif kind == "clock":
                self.clock_press(ctx, settings)
            elif event == "dialRotate":
                self.cue_row(ctx, settings, ticks)
            else:
                self.take_row(ctx, settings)
        except Exception as exc:  # noqa: BLE001 - boundary: shown on the key as a safe message
            await self.report(ctx, exc)

    # ── key actions ───────────────────────────────────────────────────────

    def dispatch(self, ctx, kind, settings, gesture, steps):
        local = {
            "visor": self.press_visor,
            "clock": self.clock_press,
            "status": lambda ctx, s: self.spawn(self.guard(ctx, self.run_test())),
            "lock": self.toggle_lock,
            "macro": lambda ctx, s: self.spawn(self.guard(ctx, self.run_macro(ctx, s))),
        }
        queued = {
            "panic": self.run_panic,
            "restore": self.run_restore,
            "snapshot": self.run_snapshot,
            "undo": self.run_undo,
            "cycle": self.run_cycle,
            "swap": self.run_swap,
            "datasource": self.run_source,
            "template": self.run_template,
            "obsscene": self.run_obs_scene,
            "obsrefresh": self.run_obs_refresh,
            "reveal": self.run_reveal,
        }
        sign = -1 if gesture == "ccw" else 1
        if kind in local:
            local[kind](ctx, settings)
        elif kind == "vote":  # a press adds one vote; a knob adds or removes one per tick
            self.vote(ctx, settings, steps * sign)
        elif kind == "goal" and (settings.get("operation") or "add") == "add":
            self.goal_add(ctx, settings, steps * sign)
        elif kind == "goal":
            self.submit(lambda job: self.run_goal(ctx, settings, settings.get("operation")), owners={ctx})
        elif kind in queued:
            if kind == "panic":
                self.panic()  # abort now, then Hide All in the queue
            self.submit(lambda job: queued[kind](ctx, settings), owners={ctx})
        else:
            if kind == "knob":
                kind, settings, gesture = self.knob_gesture(settings, gesture)
                if kind is None:
                    return
            self.overlay_action(ctx, kind, settings, gesture, steps)

    def overlay_action(self, ctx, kind, settings, gesture, steps):
        if kind in ("showall", "hideall"):  # one job per control app, in order; one failure does not stop the rest
            for token in self.tokens_of(settings):  # the error names the app that failed (id, never the token)
                run = lambda job, token=token: self.each_app([token], lambda api: self.all_overlays(api, kind))  # noqa: E731
                self.submit(run, owners={ctx}, token=self.api(token).token)
            return
        api = self.api(settings.get("token"))
        self.flush_edits(api.token)
        overlay_id = settings.get("overlayId", "")
        if kind == "toggle":
            self.submit(lambda job: self.toggle(ctx, api, settings), owners={ctx}, token=api.token, overlay=overlay_id)
        elif kind == "numericfields":
            op = (
                settings.get("operation", "increment")
                if gesture == "press"
                else ("increment" if gesture == "cw" else "decrement")
            )
            size = abs(integer(settings.get("step"))) or self.multiplier  # optional fixed step (+2, +3…)
            self.queue_numeric(ctx, api, settings, steps * size * (-1 if op == "decrement" else 1))
        elif kind in ("nextslot", "prevslot"):
            self.submit(
                lambda job: self.step_slot(ctx, api, settings, kind), owners={ctx}, token=api.token, overlay=overlay_id
            )
        elif kind == "timer":
            overlay_id, _ = composite(settings.get("fieldComposite"))
            self.submit(lambda job: self.run_timer(api, settings), owners={ctx}, token=api.token, overlay=overlay_id)

    @staticmethod
    def tokens_of(settings):
        """API Token plus the "More control apps" list of Show All / Hide All, each once, in order."""
        tokens = [settings.get("token"), *(settings.get("tokens") or [])]
        unique = list(dict.fromkeys(str(t).strip() for t in tokens if isinstance(t, str) and t.strip()))
        if not unique:
            raise UnoError(tr("Enter the control API token, not the output URL."))
        return unique

    @staticmethod
    def knob_gesture(settings, gesture):
        """Knob Control: each gesture has its own action; the chosen operation beats the turn direction."""
        chosen = settings.get(gesture + "Action", "none")
        if chosen == "none":
            return None, settings, gesture
        mapped = {
            "token": settings.get("token"),
            **{key: settings.get(gesture + key[0].upper() + key[1:]) for key in KNOB_KEYS},
        }
        if chosen in ("increment", "decrement"):
            mapped["overlayId"], mapped["fieldId"] = composite(mapped.get("fieldComposite"))
            mapped["operation"] = chosen
            return "numericfields", mapped, "press"
        return {"showAll": "showall", "hideAll": "hideall"}.get(chosen, chosen), mapped, gesture

    def press_visor(self, ctx, settings):
        dial = self.dial_for(settings.get("channel"))
        if dial is None:
            raise UnoError(tr("No knob uses this channel."))
        kind = self.actions[dial].rsplit(".", 1)[-1]
        if kind == "clock":
            self.clock_press(dial, self.settings[dial])
        elif kind == "datasource":
            self.take_row(dial, self.settings[dial])
        else:
            self.spawn(self.guard(ctx, self.dial(dial, kind, "click", 0)))

    def toggle_lock(self, ctx, settings):
        token = self.api(settings.get("token")).token
        (self.locked.discard if token in self.locked else self.locked.add)(token)
        self.spawn(self.repaint())

    # ── shared services ───────────────────────────────────────────────────

    def api(self, token):
        """UNO App API client for a token; every request is counted and logged (uno.runtime.safety)."""
        return Counted(self.api_factory(token), self)

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def message(self, event, ctx, payload=None):
        msg = {"event": event, "context": ctx}
        if payload is not None:
            msg["payload"] = payload
        await self.send(msg)

    async def to_inspector(self, ctx, payload, action=None):
        """sendToPropertyInspector: OpenDeck routes it to the inspector by action and context."""
        action = self.actions.get(ctx, "") if action is None else action
        await self.send({"event": "sendToPropertyInspector", "action": action, "context": ctx, "payload": payload})

    async def report(self, ctx, error):
        """Alert on the key, one log line and the inspector's status; unexpected errors stay generic."""
        text = (
            str(error)
            if isinstance(error, UnoError)
            else tr("Unexpected error. Reopen the inspector or restart the plugin.")
        )
        if ctx == AUTOMATION:  # not an OpenDeck context: the log is where an automation reports
            log.warning("UNO automation: %s", text)
            return
        log.warning("UNO: %s", text if isinstance(error, UnoError) else f"{text} ({type(error).__name__})")
        self.note(f"{self.actions.get(ctx, '').rsplit('.', 1)[-1] or 'key'}: {text}")
        await self.message("showAlert", ctx)
        if ctx in self.open_inspectors:
            await self.to_inspector(ctx, {"type": "error", "error": text})

    async def guard(self, ctx, coro):
        try:
            await coro
        except Exception as exc:  # noqa: BLE001 - boundary: shown on the key as a safe message
            await self.report(ctx, exc)

    async def close(self):
        waiting = [timer for timer in (self.save_timer, self.calls_timer) if timer]
        for timer in waiting:
            timer.cancel()
        if waiting:  # global settings changed since the last save (API count, registry, adopted keys)
            try:
                await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
            except Exception:  # noqa: BLE001 - best effort: OpenDeck may already have closed the socket
                log.info("UNO: the global settings were not saved on exit.")
        for handle in [
            *self.triggers,
            *(entry[1] for entry in self.timers.values()),
            *(batch["timer"] for batch in self.edits.values()),
            *(job.numeric["timer"] for job in self.accumulators.values() if job.numeric.get("timer")),
        ]:
            handle.cancel()
        self.page.close()
        if self.obs:
            await self.obs.close()
        if self.worker:
            self.worker.cancel()
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*([self.worker] if self.worker else []), *list(self.tasks), return_exceptions=True)
        for queue in self.queues:
            for job in queue:
                if job.future is not None and not job.future.done():
                    job.future.cancel()
        await asyncio.gather(*(store.close() for store in self.stores.values()))
        self.timers.clear()
