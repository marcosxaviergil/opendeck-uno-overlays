"""OBS Studio through obs-websocket 5: authentication, scene keys, vMix-style triggers, refresh (loopback)."""

from support import TOKEN, Case, FakeObs, Server, appear, last_image, press, serve, serving


class Obs(Case):
    async def test_scene_keys_triggers_and_refresh(self):
        server, obs = Server(show=True), FakeObs()
        async with serving(server), serve(obs.handler, "127.0.0.1", 0) as osrv:
            port = osrv.sockets[0].getsockname()[1]
            r, sent = self.runtime(server), self.sent
            obs_settings = {"obsEnabled": True, "obsHost": "127.0.0.1", "obsPort": str(port), "obsPassword": "secret"}
            await self.set_global({}, **obs_settings)
            await self.eventually(lambda: r.obs.connected and r.obs.scene, 3)
            self.check("SHA-256 auth and Identify; initial scene read", r.obs.connected and r.obs.scene == "Main")
            lists = await self.request({"type": "obs.list"}, ctx="O1", action="obsscene")
            self.check(
                "scene and browser source lists",
                lists.get("data") == {"scenes": ["Main", "Cam"], "browsers": ["UNO Browser"]},
                str(lists),
            )
            scene_key = {**TOKEN, "sceneName": "Cam", "overlayId": "OV1"}
            await r.handle(appear("O1", "obsscene", scene_key))
            trig = {
                **TOKEN,
                "overlayId": "OV1",
                "obsScene": "Cam",
                "obsInFunction": "show",
                "obsInDelay": "300",
                "obsOutFunction": "hide",
                "obsOutDelay": "0",
                "obsOnlyScenes": "Cam",
            }
            await r.handle(appear("T2", "toggle", trig))
            await self.settle()
            self.check("scene key white while Cam is not in program", 'fill="#FFFFFF" d=' in last_image(sent, "O1"))
            await r.handle(press("T2", "toggle", trig))
            await self.settle()
            self.check(
                "protection: the key is blocked outside the allowed scene",
                "ShowOverlay" not in self.backend.names() and any(e.get("event") == "showAlert" for e in sent),
            )
            self.backend.log.clear()
            await r.handle(press("O1", "obsscene", scene_key))
            await self.settle(1.0)
            self.check(
                "combined key: SetCurrentProgramScene, then ShowOverlay",
                ("SetCurrentProgramScene", {"sceneName": "Cam"}) in obs.requests
                and self.backend.names().count("ShowOverlay") >= 1,
            )
            self.check("scene key red while its scene is in program", 'fill="#FF0000"' in last_image(sent, "O1"))
            self.check(
                "vMix-style trigger: scene in program shows after the delay",
                self.backend.names().count("ShowOverlay") == 2,
                str(self.backend.log),
            )
            self.backend.log.clear()
            await obs.switch("Main")
            await self.settle(0.5)
            self.check(
                "trigger: scene leaves program hides", self.backend.names() == ["HideOverlay"], str(self.backend.log)
            )
            refresh = {"inputName": "UNO Browser"}
            await r.handle(appear("R1", "obsrefresh", refresh))
            await r.handle(press("R1", "obsrefresh", refresh))
            await self.settle(0.5)
            self.check(
                "refresh browser: PressInputPropertiesButton refreshnocache",
                ("PressInputPropertiesButton", {"inputName": "UNO Browser", "propertyName": "refreshnocache"})
                in obs.requests,
            )
            macro = {**TOKEN, "steps": [{"type": "obsscene", "sceneName": "Cam"}]}
            await r.handle(press("M1", "macro", macro))
            self.check(
                "macro step OBS scene switches the program scene",
                await self.eventually(lambda: obs.scene == "Cam", 3),
                obs.scene,
            )
            await r.close()
