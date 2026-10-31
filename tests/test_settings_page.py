"""Plugin settings page: OpenDeck's gear (showSettingsInterface) opens it; one OBS connection for every key."""

import asyncio
import http.client
import json
from unittest import mock

from support import Case, FakeObs, Server, serve, serving


def http_call(host, method, path, body=None, headers=None):
    """A browser request to the settings page (blocking: run it in a thread)."""
    connection = http.client.HTTPConnection(host, timeout=20)
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    connection.request(method, path, body=data, headers={"Host": host, **(headers or {})})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


class SettingsPage(Case):
    async def open_page(self, r):
        """OpenDeck sends showSettingsInterface; the plugin opens its page in the default browser."""
        with mock.patch("webbrowser.open", return_value=True) as browser:
            await r.handle({"event": "showSettingsInterface"})
        url = browser.call_args.args[0]
        host, token = url.removeprefix("http://").split("/#")
        self.addCleanup(r.page.close)
        return host, token

    async def api(self, host, token, method="GET", body=None, headers=None, path="/api/settings"):
        auth = {"X-UNO-Token": token, **({"Content-Type": "application/json"} if body is not None else {})}
        status, _, data = await asyncio.to_thread(http_call, host, method, path, body, {**auth, **(headers or {})})
        return status, json.loads(data)

    async def test_gear_opens_a_protected_page_and_saving_connects_every_key(self):
        server, obs = Server(show=True), FakeObs()
        async with serving(server), serve(obs.handler, "127.0.0.1", 0) as osrv:
            obs_port = osrv.sockets[0].getsockname()[1]
            r, sent = self.runtime(server), self.sent
            await self.set_global({})  # OpenDeck answers getGlobalSettings at start
            host, token = await self.open_page(r)
            self.check(
                "loopback only, random port, token in the fragment", host.startswith("127.0.0.1:") and len(token) >= 40
            )

            status, headers, page = await asyncio.to_thread(http_call, host, "GET", "/")
            self.check("the page is served", status == 200 and b"UNO Overlays settings" in page)
            self.check(
                "strict CSP, no caching, no referrer",
                "script-src 'self'" in headers.get("Content-Security-Policy", "")
                and "frame-ancestors 'none'" in headers["Content-Security-Policy"]
                and headers.get("Cache-Control") == "no-store"
                and headers.get("Referrer-Policy") == "no-referrer",
                str(headers),
            )
            status, _, _ = await asyncio.to_thread(http_call, host, "GET", "/../manifest.json")
            self.check("only the page's own files are served", status == 404)

            status, _ = await self.api(host, "wrong")
            self.check("API without the token is refused", status == 403)
            status, _, _ = await asyncio.to_thread(
                http_call, host, "GET", "/api/settings", None, {"X-UNO-Token": token, "Host": "evil.example:80"}
            )
            self.check("another Host (DNS rebinding) is refused", status == 403)

            obs_settings = {"enabled": True, "host": "127.0.0.1", "port": obs_port, "password": "secret"}
            status, _ = await self.api(host, token, "POST", {"obs": obs_settings}, {"Origin": "http://evil.example"})
            self.check("a request from another site is refused", status == 403 and r.obs is None)
            status, state = await self.api(host, token, "POST", {"obs": obs_settings})
            self.check("saved", status == 200 and state["obs"]["enabled"] is True, str(state))
            self.check(
                "the password never goes back to the page",
                "secret" not in json.dumps(state) and state["obs"]["hasPassword"],
            )
            self.check("the plugin connects to OBS", await self.eventually(lambda: r.obs and r.obs.connected, 5))
            saved = [e["payload"] for e in sent if e.get("event") == "setGlobalSettings"]
            self.check(
                "stored in the plugin's global settings, shared by every key",
                saved and saved[-1]["obsHost"] == "127.0.0.1" and saved[-1]["obsPort"] == str(obs_port),
            )
            _, state = await self.api(host, token)
            self.check("the page shows the connection", state["status"] == "connected", str(state))

            await self.set_global({"obsEnabled": False, "obsHost": "old", "obsPort": "1"})  # an inspector's old copy
            self.check(
                "an inspector's old copy never replaces the connection",
                r.global_settings["obsEnabled"] is True and r.global_settings["obsHost"] == "127.0.0.1",
            )

            status, _ = await self.api(host, token, "POST", {"obs": {**obs_settings, "password": ""}})
            self.check(
                "an empty password keeps the saved one", status == 200 and r.global_settings["obsPassword"] == "secret"
            )
            status, _ = await self.api(host, token, "POST", {"obs": {**obs_settings, "clearPassword": True}})
            self.check("Remove the saved password", status == 200 and r.global_settings["obsPassword"] == "")
            status, _ = await self.api(host, token, "POST", {"obs": {**obs_settings, "enabled": "false"}})
            self.check(
                "only JSON true turns it on (the text 'false' does not)", r.global_settings["obsEnabled"] is False
            )

            for bad, word in (({"host": "evil/path"}, "host"), ({"port": 70000}, "port")):
                status, reply = await self.api(host, token, "POST", {"obs": {**obs_settings, **bad}})
                self.check(
                    f"invalid {word} refused with a message", status == 400 and word in reply["error"], str(reply)
                )
            status, _, _ = await asyncio.to_thread(
                http_call,
                host,
                "POST",
                "/api/settings",
                b"x" * 70_000,
                {"X-UNO-Token": token, "Content-Type": "application/json"},
            )
            self.check("oversized body refused", status == 400)
            status, _, _ = await asyncio.to_thread(
                http_call, host, "POST", "/api/settings", b"{}", {"X-UNO-Token": token, "Content-Type": "text/plain"}
            )
            self.check("only JSON is accepted", status == 400)
            log = "\n".join(r.log)
            self.check(
                "log without the token or password",
                token not in log and "secret" not in log and "OBS settings saved." in log,
            )

            await r.close()
            await asyncio.sleep(1.5)  # the page's thread notices within its 1 s timeout
            with self.assertRaises(ConnectionRefusedError, msg="closing the plugin closes the page"):
                await self.api(host, token)

    async def test_a_backup_with_an_invalid_host_never_connects(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            await self.set_global({"obsEnabled": True, "obsHost": "evil/path", "obsPort": "4455"})
            self.check("no connection is attempted", r.obs is None)
            await r.close()

    async def test_control_apps_triggers_groups_language_and_live_edit_delay(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await self.set_global({})
            host, token = await self.open_page(r)
            self.backend.fail_tokens = {"REFUSED"}
            status, reply = await self.api(host, token, "POST", {"addToken": "REFUSED"})
            self.check("a token UNO refuses is not kept", status == 400 and not r.apps(), str(reply))
            status, state = await self.api(host, token, "POST", {"addToken": "TESTTOKEN", "addName": "Placar"})
            app = state["apps"][0]["id"] if state.get("apps") else ""
            self.check(
                "a working token is registered; the page gets its id and name, never the token",
                status == 200
                and state["apps"] == [{"id": app, "name": "Placar"}]
                and "TESTTOKEN" not in json.dumps(state),
                str(state),
            )
            status, overlays = await self.api(host, token, "POST", {"app": app}, path="/api/overlays")
            self.check(
                "overlays of a registered app, for the lists",
                status == 200 and {"id": "OV1", "name": "OV1"} in overlays,
                str(overlays),
            )
            status, reply = await self.api(host, token, "POST", {"app": "nope"}, path="/api/overlays")
            self.check("an unknown app is refused", status == 400, str(reply))
            triggers = [
                {"event": "obsIn", "scene": "Cam", "function": "show", "app": app, "overlay": "OV1", "delay": 99999},
                {"event": "bogus", "function": "show"},
                {"event": "unoOut", "sourceApp": app, "sourceOverlay": "OV1", "function": "hide", "app": app,
                 "overlay": "OV2", "on": False, "extra": "<script>"},
            ]  # fmt: skip
            groups = {"LT": {"delay": 99, "members": [{"app": app, "overlay": "OV1"}, {"app": app, "overlay": "OV1"}]}}
            body = {"triggers": triggers, "groups": groups, "language": "pt-BR", "liveEditDelay": 50000}
            status, state = await self.api(host, token, "POST", body)
            saved = r.global_settings
            self.check(
                "triggers are cleaned: invalid ones dropped, delay at most 30 000 ms, unknown fields gone",
                status == 200
                and [t["event"] for t in saved["triggers"]] == ["obsIn", "unoOut"]
                and saved["triggers"][0]["delay"] == 30000
                and saved["triggers"][1]["on"] is False
                and "extra" not in saved["triggers"][1],
                str(saved.get("triggers")),
            )
            self.check(
                "groups: time limited to ±30 s, each member once",
                saved["groups"] == {"LT": {"delay": 30.0, "members": [{"app": app, "overlay": "OV1"}]}},
                str(saved.get("groups")),
            )
            self.check(
                "language and live edit delay (at most 10 000 ms) saved",
                saved["language"] == "pt-BR"
                and saved["liveEditDelay"] == 10000
                and state["language"]["current"] == "pt-BR",
                str(state.get("language")),
            )
            await self.set_global({"triggers": [], "language": "en"})  # an inspector's old copy of the globals
            self.check("an inspector's old copy never replaces them", len(r.global_settings["triggers"]) == 2)
            status, state = await self.api(host, token, "POST", {"apps": []})
            self.check("an app left out of the list is forgotten", status == 200 and not state["apps"] and not r.apps())
            log = "\n".join(r.log)
            self.check("the log never has a token", "TESTTOKEN" not in log and "REFUSED" not in log, log)
            self.check("saved to OpenDeck", any(e.get("event") == "setGlobalSettings" for e in sent))
            await r.close()
