"""Safety and diagnostics: second-press confirm, Lock Desk, Status key, API count, log, backup (loopback)."""

import asyncio
import json
import os
import stat
import tempfile

from support import (
    TOKEN,
    Case,
    Server,
    appear,
    background_of,
    decoded_images,
    disappear,
    press,
    serving,
    settings_changed,
    state,
)


class Confirm(Case):
    async def test_second_press_confirmation_is_optional(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            safe = {**TOKEN, "overlayId": "OV1", "confirmSeconds": "2"}
            await r.handle(appear("K1", "toggle", safe))
            await self.settle()
            await r.handle(press("K1", "toggle", safe))
            await asyncio.sleep(0.8)
            blinked = any('fill="#FF0000" d=' in img for img in decoded_images(sent, "K1"))
            first = state(server, "OV1")
            await r.handle(press("K1", "toggle", safe))
            await self.settle()
            self.check("the first press only arms: nothing runs", first == "Out1")
            self.check("the armed key blinks", blinked)
            self.check("a second press in time runs", state(server, "OV1") == "In")
            await r.handle(press("K1", "toggle", safe))
            await asyncio.sleep(2.4)
            await r.handle(press("K1", "toggle", safe))
            await self.settle()
            self.check(
                "without a second press in time the key disarms",
                state(server, "OV1") == "In" and "K1" in r.armed,
            )
            await asyncio.sleep(2.3)
            plain = {**TOKEN, "overlayId": "OV1"}
            await r.handle(settings_changed("K1", "toggle", plain))
            await r.handle(press("K1", "toggle", plain))
            await self.settle()
            self.check("confirm off (default): one press runs", state(server, "OV1") == "Out1")
            await r.close()


class LockDesk(Case):
    async def test_lock_unlock_and_auto_lock(self):
        server = Server(show=True)
        async with serving(server):
            r, sent, glob = self.runtime(server), self.sent, {}
            await self.set_global(glob)  # OpenDeck answers getGlobalSettings at start
            plain = {**TOKEN, "overlayId": "OV1"}
            knob = {**TOKEN, "cwAction": "toggle", "cwOverlayId": "OV1"}
            await r.handle(appear("LD", "lockdesk", {}))
            await r.handle(press("LD", "lockdesk", {}, "keyDown"))
            await r.handle(press("LD", "lockdesk", {}, "keyUp"))
            mark = len(sent)
            await r.handle(press("K1", "toggle", plain))
            await r.handle(appear("KN", "knob", knob, "Encoder"))
            await r.handle(press("KN", "knob", knob, "dialRotate", ticks=1))
            await self.settle()
            alerts = {e.get("context") for e in sent[mark:] if e.get("event") == "showAlert"}
            self.check(
                "locked: keys and knobs only alert; the lock key is red",
                state(server, "OV1") == "Out1"
                and alerts >= {"K1", "KN"}
                and 'fill="#FF0000" d=' in decoded_images(sent, "LD")[-1],
                str(alerts),
            )
            await r.handle(press("LD", "lockdesk", {}, "keyDown"))
            await asyncio.sleep(0.6)
            await r.handle(press("LD", "lockdesk", {}, "keyUp"))
            early = r.desk_locked
            await r.handle(press("LD", "lockdesk", {}, "keyDown"))
            await asyncio.sleep(2.2)
            await r.handle(press("LD", "lockdesk", {}, "keyUp"))
            await r.handle(press("K1", "toggle", plain))
            await self.settle()
            self.check("releasing early keeps it locked", early)
            self.check("holding 2 s unlocks", not r.desk_locked and state(server, "OV1") == "In")
            await self.set_global(glob, lockAfter="1")
            auto = await self.eventually(lambda: r.desk_locked, 3)
            await r.handle(press("LD", "lockdesk", {}, "keyDown"))
            await asyncio.sleep(2.2)
            await r.handle(press("LD", "lockdesk", {}, "keyUp"))
            await r.handle(disappear("LD", "lockdesk", {}))
            await asyncio.sleep(2.3)
            self.check("auto lock after N s without use (Companion Pin Timeout)", auto)
            self.check("no auto lock without a Lock Desk key on a device", not r.desk_locked)
            await r.close()


class StatusAndBackup(Case):
    async def status(self, payload):
        return await self.request(payload, ctx="ST", action="status")

    async def test_status_key_count_and_log(self):
        server = Server(show=True)
        async with serving(server):
            r, sent, glob = self.runtime(server), self.sent, {}
            await self.set_global(glob)
            await r.handle(press("K1", "toggle", {**TOKEN, "overlayId": "OV1"}))  # one App API call
            await self.settle()
            await r.handle(appear("ST", "status", {}))
            green = await self.eventually(lambda: background_of(sent, "ST") == "#00C800", 3)
            counts = (r.global_settings.get("apiCalls") or {}).get("counts") or {}
            total = sum(counts.values())
            self.check(
                "green with today's App API calls on the key",
                green and total > 0 and f">{total}<" in decoded_images(sent, "ST")[-1],
                f"{background_of(sent, 'ST')} {counts}",
            )
            await self.set_global(glob, apiCap=str(total))
            self.check(
                "yellow near the daily cap",
                await self.eventually(lambda: background_of(sent, "ST") == "#FFFF00", 3),
                background_of(sent, "ST"),
            )
            await self.set_global(glob, apiCap="")
            self.backend.fail = True
            await r.handle(press("ST", "status", {}))
            self.check(
                "a press tests the connection; an API error turns it red",
                await self.eventually(lambda: background_of(sent, "ST") == "#C80000", 3),
                background_of(sent, "ST"),
            )
            self.backend.fail = False
            reply = await self.status({"type": "status.test"})
            self.check(
                "test from the inspector; back to green",
                reply.get("data")
                and "API OK" in reply["data"][0]
                and await self.eventually(lambda: background_of(sent, "ST") == "#00C800", 3),
                str(reply),
            )
            await r.handle(appear("LD", "lockdesk", {}))
            await r.handle(press("LD", "lockdesk", {}, "keyDown"))
            await r.handle(press("LD", "lockdesk", {}, "keyUp"))
            reply = await self.status({"type": "status.get"})
            log = "\n".join(reply["data"]["log"])
            self.check("log: API calls with their result", "GetOverlays → OK" in log, log[:300])
            self.check("log: errors and the lock", "UNO HTTP 500" in log and "Desk locked." in log)
            self.check("log: never the token", "TESTTOKEN" not in log)
            await self.set_global(glob, apiCalls={"date": "2000-01-01", "counts": {"x": 1}})
            kept = r.global_settings["apiCalls"]["counts"]
            self.check(
                "an inspector's old copy never replaces the plugin's counts",
                kept == counts or sum(kept.values()) >= total,
            )
            await self.status({"type": "log.clear"})
            reply = await self.status({"type": "status.get"})
            self.check("Clear log empties it (LGPD Art. 16)", reply["data"]["log"] == [], str(reply["data"]["log"]))
            await asyncio.sleep(9)
            saved = [
                e for e in sent if e.get("event") == "setGlobalSettings" and "apiCalls" in (e.get("payload") or {})
            ]
            self.check("counts saved in the global settings (at most every 10 s)", bool(saved))
            await r.close()

    async def test_backup_export_and_import(self):
        server = Server(show=True)
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "backup.json")
        async with serving(server):
            r, glob = self.runtime(server), {}
            await self.set_global(
                glob,
                dataSources={"Ticker": {**TOKEN, "kind": "list", "text": "A", "map": [{"field": "OV2::Name"}]}},
                goals={"Meta": {**TOKEN, "goal": "10", "state": "active"}},
                obsHost="127.0.0.1",
                obsPassword="secret",
            )
            reply = await self.status({"type": "backup.export", "path": path})
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.check("export counts the named items", reply.get("data", {}).get("count") == 2, str(reply))
            self.check("export file is private (0600)", stat.S_IMODE(os.stat(path).st_mode) == 0o600)
            self.check(
                "no tokens, OBS password or live goal state by default",
                "TESTTOKEN" not in text and "secret" not in text and '"state"' not in text and "Ticker" in text,
            )
            reply = await self.status({"type": "backup.import", "path": path})
            self.check("import without tokens asks for one", "API token" in str(reply.get("error")), str(reply))
            await self.set_global(glob, dataSources={}, goals={})
            reply = await self.status({"type": "backup.import", "path": path, "token": "NEWTOKEN"})
            self.check(
                "import fills the missing tokens and restores the items",
                reply.get("data", {}).get("count") == 2
                and r.global_settings["dataSources"]["Ticker"]["token"] == "NEWTOKEN"
                and r.global_settings["goals"]["Meta"].get("state") is None,
                str(reply),
            )
            await self.status({"type": "backup.export", "path": path, "secrets": True})
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.check("export with secrets keeps tokens and the OBS password", "NEWTOKEN" in text and "secret" in text)
            other = os.path.join(folder, "notes.json")
            with open(other, "w", encoding="utf-8") as f:
                json.dump({"hello": 1}, f)
            reply = await self.status({"type": "backup.import", "path": other, "token": "X"})
            self.check("a file that is not a backup is refused", "not a UNO Overlays backup" in str(reply.get("error")))
            reply = await self.status({"type": "backup.export", "path": other})
            with open(other, encoding="utf-8") as f:
                untouched = json.load(f) == {"hello": 1}
            self.check(
                "export never overwrites a file that is not a backup",
                "not a UNO Overlays backup" in str(reply.get("error")) and untouched,
                str(reply),
            )
            reply = await self.status({"type": "backup.export", "path": "backup.json"})
            self.check("a relative path is refused", "full path" in str(reply.get("error")), str(reply))
            await r.close()
