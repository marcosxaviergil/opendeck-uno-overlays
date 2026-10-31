"""2.0.0 actions: Show/Hide All on several control apps, the Numeric Fields step icon, OBS Refresh Browser
for several sources or a whole scene, the Slot Wheel carousel and Reveal Answer (loopback)."""

from support import (
    RED,
    TOKEN,
    WHITE,
    Case,
    FakeObs,
    Server,
    appear,
    errors,
    last_image,
    press,
    serving,
    state,
)


class ShowHideAll(Case):
    async def test_every_control_app_of_the_key_and_one_failure_does_not_stop_the_rest(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            self.backend.fail_tokens = {"BROKEN"}
            key = {**TOKEN, "tokens": ["BROKEN", "SECOND", "TESTTOKEN", " "]}
            await r.handle(press("H1", "hideall", key))
            await self.settle()
            hides = [c[4] for c in self.backend.log if c[0] == "HideAllOverlays"]
            self.check("one Hide All per app, in order, each once", hides == ["TESTTOKEN", "SECOND"], str(hides))
            failure = [e["payload"]["error"] for e in sent if (e.get("payload") or {}).get("type") == "error"]
            self.check("the failure alerts the key", "H1" in errors(sent), str(errors(sent)))
            self.check("the message names the app, never the token", "BROKEN" not in str(failure + list(r.log)))
            knob = {**TOKEN, "pressAction": "showAll", "pressTokens": ["SECOND"]}
            self.backend.log.clear()
            await r.handle(press("KN", "knob", knob, "dialDown"))
            await self.settle()
            shows = [c[4] for c in self.backend.log if c[0] == "ShowAllOverlays"]
            self.check("Knob Control gesture: same list", shows == ["TESTTOKEN", "SECOND"], str(shows))
            macro = {**TOKEN, "steps": [{"type": "hideall", "tokens": ["SECOND"]}]}
            self.backend.log.clear()
            await r.handle(press("M1", "macro", macro))
            await self.settle()
            hides = [c[4] for c in self.backend.log if c[0] == "HideAllOverlays"]
            self.check("Macro step: same list", hides == ["TESTTOKEN", "SECOND"], str(hides))
            await r.close()


class NumericIcon(Case):
    async def test_the_key_shows_what_one_press_adds(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            fixed = {**TOKEN, "overlayId": "OV1", "fieldId": "Score", "step": "3"}
            await r.handle(appear("N3", "numericfields", fixed))
            minus = {**TOKEN, "overlayId": "OV1", "fieldId": "Score", "operation": "decrement"}
            await r.handle(appear("NM", "numericfields", minus))
            await self.settle(0.3)
            self.check(
                "Fixed step 3: +3 in white", ">+3<" in last_image(sent, "N3") and WHITE in last_image(sent, "N3")
            )
            self.check("Decrement without a step: −1 (multiplier)", ">−1<" in last_image(sent, "NM"))
            await r.handle(press("MU", "multiplier", {"multiplier": "5"}))
            await self.settle(0.3)
            self.check("a new multiplier redraws it: −5", ">−5<" in last_image(sent, "NM"))
            await self.show("OV1")
            self.check("tally: red on air", f'fill="{RED}"' in last_image(sent, "N3"))
            await r.close()


class RefreshBrowsers(Case):
    async def start(self):
        server, obs = Server(show=True), FakeObs()
        await self.enter(serving(server))
        r = self.runtime(server)
        await self.start_obs(obs, {})
        return r, obs

    def refreshed(self, obs):
        return [d["inputName"] for kind, d in obs.requests if kind == "PressInputPropertiesButton"]

    async def test_list_of_sources_and_one_failure_does_not_stop_the_rest(self):
        r, obs = await self.start()
        obs.broken = {"Broken"}
        key = {"inputName": "Lower", "inputNames": ["Broken", "Score", "Lower"]}
        await r.handle(press("R1", "obsrefresh", key))
        await self.settle()
        self.check("each source once, in order", self.refreshed(obs) == ["Lower", "Broken", "Score"])
        self.check("the failure alerts the key", "R1" in errors(self.sent))
        await r.close()

    async def test_every_browser_source_of_a_scene_with_groups_and_nested_scenes(self):
        r, obs = await self.start()
        await r.handle(press("R2", "obsrefresh", {"refreshMode": "scene", "refreshScene": "Cam"}))
        await self.settle()
        self.check(
            "browser sources of the scene, its group and its nested scene, once each, no loop",
            self.refreshed(obs) == ["Lower", "Score", "Ticker"],
            str(obs.requests),
        )
        self.check(
            "groups read with GetGroupSceneItemList",
            ("GetGroupSceneItemList", {"sceneName": "Layers"}) in obs.requests,
        )
        await r.close()


class Quiz(Case):
    async def test_carousel_takes_slots_while_turning_and_press_toggles(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            wheel = {**TOKEN, "overlayId": "OV1", "carousel": "true", "channel": "1"}
            await r.handle(appear("W1", "slotwheel", wheel, "Encoder"))
            await r.handle(appear("V1", "visor", {"channel": "1"}))
            await self.settle(0.3)
            self.backend.log.clear()
            for _ in range(2):  # two quick clicks: one take
                await r.handle(press("W1", "slotwheel", wheel, "dialRotate", ticks=1))
            await self.settle(0.6)
            takes = [c for c in self.backend.log if c[0].startswith("TakeOverlay")]
            self.check(
                "two ticks become one TakeOverlaySlotNumber to the slot two ahead",
                [(c[0], c[2]) for c in takes] == [("TakeOverlaySlotNumber", {"value": 3})]
                and server.slots()["currentSlotId"] == "s3",
                str(takes),
            )
            self.check("the Visor shows the slot on air", ">Convidado<" in last_image(sent, "V1"))
            await r.handle(press("W1", "slotwheel", wheel, "dialRotate", ticks=1))
            await self.settle(0.6)
            self.check("it wraps around to the first slot", server.slots()["currentSlotId"] == "s1")
            for event in ("dialDown", "dialUp"):
                await r.handle(press("W1", "slotwheel", wheel, event))
            await self.settle()
            self.check("press shows the overlay", state(server, "OV1") == "In")
            for event in ("dialDown", "dialUp"):
                await r.handle(press("W1", "slotwheel", wheel, event))
            await self.settle()
            self.check("press again hides it", state(server, "OV1") == "Out1")
            await r.close()

    async def test_reveal_answer_toggles_highlights_and_hides_on_a_new_slot(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            server.payload()["Correct"] = "B"
            server.payload()["Highlight"] = ""
            server.payload()["Show"] = False
            server.dump()  # the snapshot the plugin reads when it connects
            reveal = {
                **TOKEN,
                "fieldComposite": "OV1::Show",
                "copyFrom": "OV1::Correct",
                "copyTo": "OV1::Highlight",
            }
            await r.handle(appear("RV", "reveal", reveal))
            await self.settle(0.3)
            await r.handle(press("RV", "reveal", reveal))
            await self.settle()
            self.check(
                "revealed: the field is true (its JSON type kept) and the correct answer is highlighted",
                server.payload()["Show"] is True and server.payload()["Highlight"] == "B",
                str(server.payload()),
            )
            self.check("tally red while revealed", f'fill="{RED}"' in last_image(sent, "RV"))
            await r.handle(press("RV", "reveal", reveal))
            await self.settle()
            self.check(
                "press again hides it",
                server.payload()["Show"] is False and server.payload()["Highlight"] == "",
            )
            await r.handle(press("RV", "reveal", reveal))
            await self.settle()
            await r.handle({**appear("RV", "reveal", reveal), "event": "willDisappear"})
            await self.backend.api("TESTTOKEN").call("TakeOverlayNextSlot", id="OV1")
            await self.settle(0.8)
            self.check(
                "a new slot hides the answer again, with no Reveal key visible",
                server.payload()["Show"] is False,
                str(server.payload()),
            )
            await r.close()
