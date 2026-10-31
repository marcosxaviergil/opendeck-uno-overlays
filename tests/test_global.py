"""Global automations: they run whatever profile, device or key is visible (items 1 and 12 of 2.0.0).

OpenDeck sends willAppear only for keys of the selected profile of a connected device and
willDisappear when the profile changes (events/frontend/profiles.rs). Every scenario here runs the
automation with the related key never shown, or after its willDisappear, and with keys of two
devices ("devA", "devB").
"""

import asyncio
from copy import deepcopy

from support import (
    TOKEN,
    Case,
    FakeObs,
    Server,
    appear,
    disappear,
    errors,
    last_image,
    press,
    serving,
    settings_changed,
    state,
)
from uno.automations import app_id

APP = app_id("TESTTOKEN")
REGISTRY = {"controlApps": {APP: {"token": "TESTTOKEN", "name": "Desk"}}}


def trigger(event, function, overlay="OV1", **extra):
    return {"id": f"t-{event}-{function}", "on": True, "event": event, "function": function, "app": APP,
            "overlay": overlay, "delay": 0, **extra}  # fmt: skip


class GlobalTriggers(Case):
    async def test_obs_trigger_runs_with_no_key_visible_and_logs_each_step(self):
        server, obs = Server(show=True), FakeObs()
        async with serving(server):
            r = self.runtime(server)
            store = deepcopy(REGISTRY)
            store["triggers"] = [
                trigger("obsIn", "show", scene="Cam", delay=200),
                trigger("obsOut", "hide", scene="Cam"),
                trigger("obsStreamStart", "show", overlay="OV2"),
                {**trigger("obsIn", "show", overlay="OV2", scene="Cam"), "id": "off", "on": False},
            ]
            with self.assertLogs("uno", "INFO") as logs:
                await self.start_obs(obs, store)
                await obs.switch("Cam")
                await self.settle(0.8)
                self.check(
                    "scene goes to program: the global trigger shows OV1 after its delay, no key needed",
                    state(server, "OV1") == "In" and not r.settings,
                    str(self.backend.calls()),
                )
                self.check("a trigger switched off does nothing", state(server, "OV2") == "Out1")
                await obs.switch("Main")
                await self.settle(0.5)
                self.check("scene leaves program: hidden", state(server, "OV1") == "Out1")
                await obs.stream(True)
                await self.settle(0.5)
                self.check("streaming starts: OV2 shown", state(server, "OV2") == "In")
            text = "\n".join(logs.output)
            self.check("the OBS event is logged", "OBS event CurrentProgramSceneChanged" in text, text)
            self.check("each trigger decision is logged", "fired" in text and "ignored" in text, text)
            self.check("the UNO result is logged", "ShowOverlay OV1 → OK" in text, text)
            self.check("no token in the log", "TESTTOKEN" not in text)
            await r.close()

    async def test_key_triggers_move_to_the_global_list_once(self):
        server, obs = Server(show=True), FakeObs()
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            store = {}
            await self.start_obs(obs, store)
            old = {
                **TOKEN,
                "overlayId": "OV1",
                "obsScene": "Cam",
                "obsInFunction": "show",
                "obsInDelay": "0",
                "obsOutFunction": "hide",
                "unoOutFunction": "show",
                "unoOutTarget": "OV2",
                "obsOnlyScenes": "Cam",
                "autoClose": "5",
            }
            await r.handle(appear("K1", "toggle", old, device="devB"))
            await r.handle(appear("K2", "toggle", old, device="devA"))
            await self.settle()
            triggers = r.global_settings.get("triggers") or []
            self.check(
                "three triggers copied once, with the key's control app and overlay",
                sorted((t["event"], t["overlay"]) for t in triggers)
                == [("obsIn", "OV1"), ("obsOut", "OV1"), ("unoOut", "OV2")]
                and all(t["app"] == APP for t in triggers),
                str(triggers),
            )
            stripped = [e["payload"] for e in sent if e.get("event") == "setSettings" and e["context"] == "K1"]
            self.check(
                "old fields removed from the key; its own protection and Auto Close stay",
                stripped
                and "obsInFunction" not in stripped[-1]
                and "obsScene" not in stripped[-1]
                and stripped[-1].get("obsOnlyScenes") == "Cam"
                and stripped[-1].get("autoClose") == "5",
                str(stripped),
            )
            self.check("the control app is registered for global use", r.global_settings["controlApps"][APP]["token"])
            for ctx, device in (("K1", "devB"), ("K2", "devA")):
                await r.handle(disappear(ctx, "toggle", old, device=device))
            await obs.switch("Cam")
            await self.settle(0.5)
            self.check("after the profile changed, the migrated trigger still runs", state(server, "OV1") == "In")
            await r.close()


class GlobalChainsAndGroups(Case):
    async def test_chain_when_an_overlay_goes_out_with_no_key(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            store = {
                **deepcopy(REGISTRY),
                "triggers": [trigger("unoOut", "show", overlay="OV2", sourceApp=APP, sourceOverlay="OV1")],
            }
            await self.set_global(store)
            await self.settle(0.5)
            api = self.backend.api("TESTTOKEN")
            await api.call("ShowOverlay", id="OV1")
            await self.settle(0.3)
            await api.call("HideOverlay", id="OV1")
            await self.settle(0.5)
            self.check(
                "vMix OnOverlayOut from the global list: OV1 goes out, OV2 shows",
                state(server, "OV2") == "In",
                str(self.backend.calls()),
            )
            await r.close()

    async def test_global_group_hides_a_member_whose_key_is_not_visible(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            await self.set_global({**deepcopy(REGISTRY)})
            k1 = {**TOKEN, "overlayId": "OV1", "group": "LT", "groupDelay": "0"}
            await r.handle(appear("K1", "toggle", k1, device="devA"))
            await self.settle(0.3)
            await r.handle(press("K1", "toggle", k1, device="devA"))
            await self.settle()
            await r.handle(disappear("K1", "toggle", k1, device="devA"))
            k2 = {**TOKEN, "overlayId": "OV2", "group": "LT"}
            await r.handle(appear("K2", "toggle", k2, device="devB"))
            await self.settle(0.3)
            group = r.global_settings.get("groups", {}).get("LT", {})
            self.check(
                "the group lives in the global settings with both overlays",
                {m["overlay"] for m in group.get("members", [])} == {"OV1", "OV2"},
                str(group),
            )
            await r.handle(press("K2", "toggle", k2, device="devB"))
            await self.settle()
            self.check(
                "showing OV2 (devB) hides OV1, whose key (devA) is no longer visible",
                state(server, "OV1") == "Out1" and state(server, "OV2") == "In",
                str(self.backend.calls()),
            )
            await r.close()


class SurvivesProfileSwitch(Case):
    async def test_auto_close_still_hides_after_the_key_disappears(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            key = {**TOKEN, "overlayId": "OV1", "autoClose": "1"}
            await r.handle(appear("K1", "toggle", key))
            await self.settle(0.3)
            await r.handle(press("K1", "toggle", key))
            await self.settle(0.3)
            await r.handle(disappear("K1", "toggle", key))  # the user switched profile
            await asyncio.sleep(1.2)
            await self.settle()
            self.check("Auto Close hid the overlay", state(server, "OV1") == "Out1", str(self.backend.calls()))
            await r.close()

    async def test_a_press_already_made_runs_after_the_key_disappears(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            self.backend.latency = 0.4
            key = {**TOKEN, "overlayId": "OV1", "fieldId": "Score", "operation": "increment", "step": "2"}
            await r.handle(appear("N1", "numericfields", key))
            await r.handle(press("T1", "toggle", {**TOKEN, "overlayId": "OV1"}))  # keeps the queue busy
            await r.handle(press("N1", "numericfields", key))
            await r.handle(disappear("N1", "numericfields", key))
            await self.settle(1.5)
            self.check("the queued press was not lost", server.payload()["Score"] == 3, str(server.payload()))
            await r.handle(appear("N1", "numericfields", key))
            await r.handle(press("T1", "toggle", {**TOKEN, "overlayId": "OV1"}))
            await r.handle(press("N1", "numericfields", key))
            await r.handle(settings_changed("N1", "numericfields", {**key, "step": "5"}))
            await self.settle(1.5)
            self.check(
                "a real change of the key's settings still drops its queued press",
                server.payload()["Score"] == 3,
                str(server.payload()),
            )
            await r.close()


class GlobalRegistry(Case):
    async def test_a_forgotten_app_stays_forgotten_while_its_watch_still_connects(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            gate, connect = asyncio.Event(), r.store

            async def slow_store(token):  # the realtime copy of a global trigger connects slowly
                await gate.wait()
                return await connect(token)

            r.store = slow_store
            chain = trigger("unoOut", "show", overlay="OV2", sourceApp=APP, sourceOverlay="OV1")
            await self.set_global({**deepcopy(REGISTRY), "triggers": [chain]})
            await r.save_settings({"apps": []})  # the settings page forgets the app meanwhile
            gate.set()
            await self.idle()
            self.check("the app is not registered again by that watch", not r.apps(), str(r.apps()))
            await r.close()

    async def test_status_panic_and_restore_reach_apps_of_keys_not_visible(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            await r.handle(appear("K1", "toggle", {**TOKEN, "overlayId": "OV1"}))
            await self.settle()
            saved = deepcopy(r.global_settings)
            self.check("a key's working token enters the registry", APP in saved.get("controlApps", {}), str(saved))
            await r.close()
            # A new plugin run on another profile: no key with this token has appeared.
            r = self.runtime(server)
            await self.set_global(saved)
            await self.show("OV1", "OV2")
            status = r.status()
            self.check("Status lists the registered app", any(APP in item["name"] for item in status["items"]))
            await r.handle(press("PANIC", "panic", {}))
            await self.settle()
            self.check(
                "Panic without token hides every registered app",
                state(server, "OV1") == "Out1" and state(server, "OV2") == "Out1",
            )
            await r.handle(press("REST", "restore", {}))
            await self.settle()
            self.check("Restore brings them back", state(server, "OV1") == "In" and state(server, "OV2") == "In")
            await r.close()

    async def test_cycle_resets_a_clock_whose_key_is_not_visible(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            clock = {**TOKEN, "fieldComposite": "OV1::Time", "mode": "countdown", "duration": "00:10"}
            await r.handle(appear("CL", "clock", clock, device="devA"))
            await self.settle(0.3)
            await r.handle(disappear("CL", "clock", clock, device="devA"))
            cycle = {**TOKEN, "fieldComposite": "OV1::Period", "values": "1\n2", "resetClock": "OV1::Time"}
            mark = len(sent)
            await r.handle(press("CY", "cycle", cycle, device="devB"))
            await self.settle()
            self.check("no 'No Clock key shows this field'", not errors(sent[mark:]), str(errors(sent[mark:])))
            self.check("the clock was stopped and reset in its field", server.payload()["Time"] == "0:10")
            await r.close()

    async def test_shift_on_one_device_drives_a_knob_on_another(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            knob = {**TOKEN, "fieldComposite": "OV1::Score", "shiftFieldComposite": "OV1::Fouls", "channel": "2"}
            await r.handle(appear("D2", "dialvalue", knob, "Encoder", device="devB"))
            await r.handle(appear("V2", "visor", {"channel": "2"}, device="devA"))
            await r.handle(appear("SH", "shift", {}, device="devA"))
            await self.settle(0.3)
            await r.handle(press("SH", "shift", {}, "keyDown", device="devA"))
            for event in ("dialDown", "dialUp"):
                await r.handle(press("D2", "dialvalue", knob, event, device="devB"))
            await r.handle(press("D2", "dialvalue", knob, "dialRotate", device="devB", ticks=3))
            await self.settle(0.3)
            self.check("the Visor on devA shows the knob of devB", "→ 3" in last_image(sent, "V2"))
            await r.close()
