"""Show control: exclusive groups, chaining, macros, Panic/Restore, scenes, Shift, off-air edits (loopback)."""

import asyncio
import time

from support import PREFIX, TOKEN, Case, Server, appear, last_image, press, serving, state


class ShowControl(Case):
    async def test_exclusive_group(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            k1 = {**TOKEN, "overlayId": "OV1", "group": "LT"}
            k2 = {**TOKEN, "overlayId": "OV2", "group": "LT"}
            await r.handle(appear("K1", "toggle", k1))
            await r.handle(appear("K2", "toggle", k2))
            await self.settle()
            await r.handle(press("K1", "toggle", k1))
            await self.settle()
            self.backend.log.clear()
            await r.handle(press("K2", "toggle", k2))
            await self.settle()
            self.check(
                "showing OV2 hides OV1 first (Singular logic layers)",
                self.backend.calls()[-2:] == [("HideOverlay", "OV1"), ("ShowOverlay", "OV2")]
                and state(server, "OV1") == "Out1"
                and state(server, "OV2") == "In",
                str(self.backend.calls()),
            )
            groups = r.global_settings["groups"]  # the group time is global (settings page)
            await self.set_global(r.global_settings, groups={"LT": {**groups["LT"], "delay": -1}})
            self.backend.log.clear()
            await r.handle(press("K1", "toggle", k1))
            await asyncio.sleep(0.5)
            early = self.backend.calls()
            await asyncio.sleep(1.0)
            await self.settle()
            self.check(
                "group time < 0: the new one goes in, the old one goes out 1 s later",
                ("ShowOverlay", "OV1") in early
                and ("HideOverlay", "OV2") not in early
                and self.backend.calls()[-1] == ("HideOverlay", "OV2"),
                f"{early} {self.backend.calls()}",
            )
            await r.close()

    async def test_chain_when_an_overlay_goes_out(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            chain = {
                **TOKEN,
                "overlayId": "OV1",
                "autoClose": "1",
                "unoOutFunction": "show",
                "unoOutTarget": "OV2",
                "unoOutDelay": "200",
            }
            await r.handle(appear("K1", "toggle", chain))
            await self.settle()
            self.backend.log.clear()
            await r.handle(press("K1", "toggle", chain))
            await asyncio.sleep(2.0)
            await self.settle()
            self.check(
                "vMix OnOverlayOut: OV1 auto-closes, then OV2 shows",
                self.backend.calls() == [("ShowOverlay", "OV1"), ("HideOverlay", "OV1"), ("ShowOverlay", "OV2")],
                str(self.backend.calls()),
            )
            await r.close()

    async def test_macro_runs_steps_in_order(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            macro = {
                **TOKEN,
                "steps": [
                    {"type": "show", "overlayId": "OV1"},
                    {"type": "wait", "ms": "600"},
                    {"type": "setfield", "fieldComposite": "OV1::Score", "value": "7"},
                    {"type": "hide", "overlayId": "OV1"},
                ],
            }
            await r.handle(appear("M1", "macro", macro))
            await self.settle(0.3)
            self.backend.log.clear()
            t0 = time.monotonic()
            await r.handle(press("M1", "macro", macro))
            await asyncio.sleep(0.3)
            running_red = 'fill="#FF0000"' in last_image(sent, "M1")
            await asyncio.sleep(0.8)
            await self.settle()
            times = {c[0]: c[3] - t0 for c in self.backend.log}
            self.check(
                "steps in order, Wait delays the rest, value typed as a number",
                self.backend.names() == ["ShowOverlay", "SetOverlayContent", "HideOverlay"]
                and server.payload()["Score"] == 7
                and times.get("HideOverlay", 0) >= 0.6,
                str(self.backend.log),
            )
            self.check(
                "key red while running, white after", running_red and 'fill="#FFFFFF" d=' in last_image(sent, "M1")
            )
            await r.close()

    async def test_macro_runs_every_step_type(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await r.handle(press("S1", "snapshot", {**TOKEN, "name": "Vazia", "operation": "store"}))
            await self.settle()
            steps = [
                {"type": "showall"},
                {"type": "hideall"},
                {"type": "takeslot", "overlayId": "OV1", "slot": "2"},
                {"type": "nextslot", "overlayId": "OV1"},
                {"type": "prevslot", "overlayId": "OV1"},
                {"type": "toggle", "overlayId": "OV2"},
                {"type": "snapshot", "name": "Vazia"},
                {"type": "timer", "fieldComposite": "OV1::Clock", "operation": "play"},
            ]
            macro = {**TOKEN, "steps": steps}
            self.backend.log.clear()
            mark = len(sent)
            await r.handle(press("M3", "macro", macro))
            await self.settle(1.0)
            names = self.backend.names()
            self.check("no step failed", not [e for e in sent[mark:] if e.get("event") == "showAlert"])
            self.check(
                "each step called UNO in order",
                names[:8]
                == [
                    "ShowAllOverlays",
                    "HideAllOverlays",
                    "TakeOverlaySlotNumber",
                    "ShowOverlay",
                    "TakeOverlayNextSlot",
                    "ShowOverlay",
                    "TakeOverlayPreviousSlot",
                    "ShowOverlay",
                ]
                and ("ShowOverlay", "OV2") in self.backend.calls(),
                str(names),
            )
            self.check("timer step started the clock", server.payload()["Clock"]["isRunning"] is True)
            self.check("scene step recalled the stored scene (all off air)", state(server, "OV2") == "Out1")
            await r.close()

    async def test_panic_and_restore(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            slow = {
                **TOKEN,
                "steps": [
                    {"type": "show", "overlayId": "OV1"},
                    {"type": "wait", "ms": "5000"},
                    {"type": "show", "overlayId": "OV2"},
                ],
            }
            timed = {**TOKEN, "overlayId": "OV2", "autoClose": "30"}
            await r.handle(appear("M2", "macro", slow))
            await r.handle(appear("K3", "toggle", timed))
            await r.handle(press("M2", "macro", slow))
            await asyncio.sleep(0.4)
            await r.handle(press("K3", "toggle", timed))
            await asyncio.sleep(0.4)
            self.backend.log.clear()
            await r.handle(appear("PANIC", "panic", TOKEN))
            await r.handle(press("PANIC", "panic", TOKEN))
            await asyncio.sleep(0.6)
            self.check(
                "Panic: macro aborted, Auto Close cleared, everything hidden",
                not r.macros
                and not r.timers
                and "HideAllOverlays" in self.backend.names()
                and state(server, "OV1") == "Out1"
                and state(server, "OV2") == "Out1",
                str(self.backend.log),
            )
            await asyncio.sleep(5)
            self.check(
                "the aborted macro never reaches its last step", ("ShowOverlay", "OV2") not in self.backend.calls()
            )
            await r.handle(press("REST", "restore", TOKEN))
            await self.settle()
            self.check(
                "Restore shows what Panic took off air",
                state(server, "OV1") == "In" and state(server, "OV2") == "In",
            )
            await r.close()

    async def test_scene_store_and_recall(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await self.show("OV1", "OV2")
            await r.handle(press("S1", "snapshot", {**TOKEN, "name": "Abertura", "operation": "store"}))
            await self.settle()
            self.check(
                "Store: saved in the global settings",
                "Abertura" in r.global_settings.get("scenes", {})
                and any(e.get("event") == "setGlobalSettings" and "scenes" in e.get("payload", {}) for e in sent),
            )
            api = self.backend.api("TESTTOKEN")
            await api.call("HideOverlay", id="OV1")
            await api.call("SetOverlayContent", id="OV2", content={"Name": "Changed"})
            await api.call("HideOverlay", id="OV2")
            await self.settle()
            recall = {**TOKEN, "name": "Abertura", "operation": "recall", "safe": ["OV2"]}
            await r.handle(press("S2", "snapshot", recall))
            await self.settle()
            self.check(
                "Recall: OV1 back on air; recall safe leaves OV2 untouched",
                state(server, "OV1") == "In"
                and state(server, "OV2") == "Out1"
                and server.payload("OV2")["Name"] == "Changed",
            )
            await r.handle(press("S3", "snapshot", {**recall, "safe": []}))
            await self.settle()
            self.check(
                "Recall without safe: OV2 content and visibility restored",
                state(server, "OV2") == "In" and server.payload("OV2")["Name"] == "Ana",
            )
            reply = await self.request({"type": "scene.delete", "name": "Abertura"}, ctx="S1", action="snapshot")
            self.check(
                "a stored scene can be deleted (it may hold names: LGPD Art. 18)",
                not reply.get("error") and "Abertura" not in r.global_settings.get("scenes", {}),
                str(reply),
            )
            await r.close()

    async def test_shift_switches_the_knob_field(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            dial = {**TOKEN, "fieldComposite": "OV1::Score", "shiftFieldComposite": "OV1::Fouls", "channel": "3"}
            await r.handle(appear("D3", "dialvalue", dial, "Encoder"))
            await r.handle(appear("SH", "shift", {}))
            await self.settle(0.3)
            await r.handle(press("SH", "shift", {}, "keyDown"))
            for e in ("dialDown", "dialUp"):
                await r.handle(press("D3", "dialvalue", dial, e))
            await r.handle(press("D3", "dialvalue", dial, "dialRotate", ticks=2))
            for e in ("dialDown", "dialUp"):
                await r.handle(press("D3", "dialvalue", dial, e))
            await self.settle()
            shift_red = 'fill="#FF0000"' in last_image(sent, "SH")
            await r.handle(press("SH", "shift", {}, "keyUp"))
            await self.settle(0.3)
            self.check(
                "Shift held: the knob edits its Shift field",
                server.payload()["Fouls"] == 2 and server.payload()["Score"] == 1,
                str(server.payload()),
            )
            self.check("Shift red while held, white after", shift_red and 'fill="#FFFFFF" d=' in last_image(sent, "SH"))
            await r.close()

    async def test_edits_on_air_wait_for_the_typing_to_stop(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await self.set_global({}, liveEditDelay=800)
            await self.show("OV1")
            old = {**TOKEN, "overlayId": "OV1", "offAir": "true", "offAirDelay": "300"}  # removed in 2.0.0
            await r.handle(appear("K4", "toggle", old))
            await self.settle(0.3)
            self.backend.log.clear()
            edit = {"type": "uno.edit", "token": "TESTTOKEN", "id": "OV1", "slotNumber": 0, "slotId": ""}
            for i, text in enumerate(("Al", "Ali", "Aline")):
                await r.handle({"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K4",
                                "payload": {**edit, "patch": {"Title": text}, "requestId": f"e{i}"}})  # fmt: skip
                await asyncio.sleep(0.5)  # pauses shorter than the delay: nothing is sent yet
            early = list(self.backend.log)
            await asyncio.sleep(0.6)
            await self.settle()
            self.check("nothing sent while typing on air", not early, str(early))
            self.check(
                "one write with the whole word, straight on air (no hide/show)",
                self.backend.names() == ["SetOverlayContent"] and server.payload()["Title"] == "Aline",
                str(self.backend.log),
            )
            self.check(
                "the inspector is told the edit waits",
                any((e.get("payload") or {}).get("type") == "uno.waiting" for e in sent),
            )
            self.backend.log.clear()
            await r.handle({"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K4",
                            "payload": {**edit, "patch": {"Title": "Bia"}, "requestId": "e9"}})  # fmt: skip
            await r.handle({"event": "propertyInspectorDidDisappear", "action": PREFIX + "toggle", "context": "K4"})
            await self.settle(0.3)
            self.check("closing the inspector sends at once", server.payload()["Title"] == "Bia")
            await r.handle({"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K4",
                            "payload": {**edit, "patch": {"Title": "Caio"}, "requestId": "e10"}})  # fmt: skip
            await r.handle({"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K4",
                            "payload": {"type": "uno.flush"}})  # fmt: skip
            await self.settle(0.3)
            self.check("another field focused sends at once", server.payload()["Title"] == "Caio")
            await r.handle({"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K4",
                            "payload": {**edit, "patch": {"Title": "Davi"}, "requestId": "e11"}})  # fmt: skip
            await r.handle(press("PANIC", "panic", TOKEN))
            await self.settle(0.5)
            self.check("Panic saves the typed text instead of dropping it", server.payload()["Title"] == "Davi")
            await r.close()

    async def test_edits_off_air_keep_the_short_window(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            await self.set_global({}, liveEditDelay=5000)
            await r.handle(appear("K5", "toggle", {**TOKEN, "overlayId": "OV1"}))
            await self.settle(0.3)
            self.backend.log.clear()
            edit = {"type": "uno.edit", "token": "TESTTOKEN", "id": "OV1", "slotNumber": 0, "slotId": ""}
            await self.request({**edit, "patch": {"Title": "Off air"}}, ctx="K5")
            self.check(
                "off air the edit goes within the 0.4 s window, not after the live delay",
                self.backend.names() == ["SetOverlayContent"],
                str(self.backend.log),
            )
            await r.close()
