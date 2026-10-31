"""The real entry point: launch.sh started the way OpenDeck starts plugins, against a local OpenDeck socket."""

import asyncio
import json

from support import PLUGIN, PREFIX, Case, appear, press, serve


class Launch(Case):
    async def test_registers_and_handles_events(self):
        got, saved, answered = [], asyncio.Event(), asyncio.Event()

        async def opendeck(ws):
            async for raw in ws:
                msg = json.loads(raw)
                got.append(msg)
                if msg.get("event") == "registerPlugin":
                    await ws.send(json.dumps(appear("D1", "display", {})))
                    await ws.send(json.dumps(press("M1", "multiplier", {"multiplier": "7"})))
                    ask = {"type": "i18n.get", "requestId": "lang"}  # the inspector asks its language
                    await ws.send(
                        json.dumps(
                            {"event": "sendToPlugin", "action": PREFIX + "toggle", "context": "K1", "payload": ask}
                        )
                    )
                if msg.get("event") == "setGlobalSettings":
                    saved.set()
                if (msg.get("payload") or {}).get("requestId") == "lang":
                    answered.set()

        async with serve(opendeck, "127.0.0.1", 0) as srv:
            port = srv.sockets[0].getsockname()[1]
            # OpenDeck (plugins/mod.rs) runs the CodePath with -port, -pluginUUID, -registerEvent and -info.
            proc = await asyncio.create_subprocess_exec(
                str(PLUGIN / "launch.sh"),
                "-port",
                str(port),
                "-pluginUUID",
                PREFIX + "sdPlugin",
                "-registerEvent",
                "registerPlugin",
                "-info",
                # info_param.rs: the language OpenDeck passes at registration. No OpenDeck settings.json is
                # beside this checkout (<plugin>/../../settings.json), so this is what the plugin speaks.
                json.dumps({"application": {"language": "de", "platform": "linux"}}),
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(asyncio.gather(saved.wait(), answered.wait()), 15)
            finally:
                proc.terminate()
                _, err = await proc.communicate()
        events = [m["event"] for m in got]
        self.check(
            "registers first, with the plugin UUID", got[0] == {"event": "registerPlugin", "uuid": PREFIX + "sdPlugin"}
        )
        self.check("asks for its global settings", "getGlobalSettings" in events)
        saved = next(m for m in got if m["event"] == "setGlobalSettings")
        self.check(
            "Multiplier key saves the shared multiplier", saved["payload"].get("multiplier") in (7, "7"), str(saved)
        )
        answer = next(m for m in got if (m.get("payload") or {}).get("requestId") == "lang")["payload"]
        self.check(
            "speaks the language of the registration info",
            (answer.get("data") or {}).get("language") == "de",
            str(answer),
        )
        self.check("stops cleanly on SIGTERM", proc.returncode == 0, err.decode()[-300:])
