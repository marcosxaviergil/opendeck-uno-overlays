"""Loopback emulators and helpers shared by the integration tests.

The emulators follow the contracts they were written from: Socket.IO 4.8.4 (an ack
function exists only when the packet carries an id), singular-datastore 1.0.1
(login/update with callbacks, rateLimitInfo, broadcast of update with userData),
the UNO App API commands the plugin uses, obs-websocket 5 authentication and the
OpenDeck event payloads (src-tauri/src/events/outbound). They are NOT the UNO or
OBS backends: tests prove the plugin keeps these contracts, not that the services do.
"""

import asyncio
import base64
import contextlib
import functools
import hashlib
import json
import logging
import os
import pathlib
import sys
import time
import unittest
from copy import deepcopy
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
sys.path[:0] = [str(PLUGIN), str(PLUGIN / "vendor")]

from websockets.asyncio.server import serve  # noqa: E402
from websockets.exceptions import ConnectionClosed  # noqa: E402

from uno import datastore, runtime  # noqa: E402
from uno.api import UnoError  # noqa: E402

if not os.environ.get("UNO_TEST_LOG"):  # the plugin's warnings are expected here; UNO_TEST_LOG=1 shows them
    logging.getLogger("uno").addHandler(logging.NullHandler())

PREFIX = "dev.br.consciencia.opendeck.uno-overlays."
TOKEN = {"token": "TESTTOKEN"}
RED, WHITE = "#FF0000", "#FFFFFF"
BASE = "compExtracts.CE.compositions.{}.dataSources.composition.controlNode.payload"


# ── UNO realtime datastore (Socket.IO over Engine.IO 4) ──


def js_set_path(data, path, value):
    """Independent copy of updateJsonObject (singular-datastore 1.0.1) for the server side."""
    keys = path.split(".")
    cur = data
    for k in keys[:-1]:
        nxt = cur[int(k)] if isinstance(cur, list) else cur.get(k)
        if not nxt:
            if isinstance(cur, list):
                cur[int(k)] = {}
            else:
                cur[k] = {}
        cur = cur[int(k)] if isinstance(cur, list) else cur[k]
    if isinstance(cur, list):
        i = int(keys[-1])
        if i == len(cur):
            cur.append(deepcopy(value))
        else:
            cur[i] = deepcopy(value)
    else:
        cur[keys[-1]] = deepcopy(value)


def parse(text):
    """socket.io-parser decodeString, the subset clients send: type, ack id, JSON data."""
    kind, i = int(text[0]), 1
    j = i
    while j < len(text) and text[j].isdigit():
        j += 1
    ack = int(text[i:j]) if j > i else None
    return kind, ack, json.loads(text[j:]) if j < len(text) else None


def initial(show):
    """Control app data. show=False: one overlay with one slot; show=True: the full broadcast desk."""
    ov1 = {"Title": "A", "Score": 1, "Fouls": 0}
    data = {
        "outputs": {"o1": {"compExtract": "CE"}},
        "compExtracts": {
            "CE": {
                "mainComposition": "MAIN",
                "compositions": {"OV1": {"dataSources": {"composition": {"controlNode": {"payload": ov1}}}}},
            }
        },
        "storage": {
            "Slots": {
                "OV1": {
                    "active": True,
                    "currentSlotId": "s1",
                    "data": [{"id": "s1", "name": "One", "payload": {"Title": "A", "Score": 1}}],
                }
            }
        },
    }
    if not show:
        return data
    ce = data["compExtracts"]["CE"]
    ce["compositionStates"] = {"OV1": "Out1", "OV2": "Out1"}
    ov1.update(
        Clock={"UTC": 0, "isRunning": False, "value": 0},
        Time="",
        Period="",
        TeamA="Home",
        TeamB="Away",
        ScoreB=0,
        VotesA=0,
        VotesB=0,
        PctA="",
        PctB="",
        Total=0,
        Raised=0,
        GoalPct="",
        GoalTitle="",
        GoalAmount="",
    )
    ce["compositions"]["OV1"]["dataSources"]["composition"]["controlNode"]["model"] = {
        "fields": [
            {"id": "Score", "type": "number", "max": "10", "min": "0", "resetValue": "0"},
            {"id": "Fouls", "type": "number"},
        ]
    }
    ce["compositions"]["OV2"] = {
        "dataSources": {
            "composition": {
                "controlNode": {
                    "payload": {"Name": "Ana", "Role": ""},
                    "model": {
                        "fields": [
                            {"id": "Name", "title": "Name", "type": "text"},
                            {"id": "Role", "title": "Cargo", "type": "text"},
                        ]
                    },
                }
            }
        }
    }
    data["storage"]["Slots"]["OV1"]["data"] += [
        {"id": "s2", "name": "Profa. Ana", "payload": {"Title": "B"}},
        {"id": "s3", "name": "Convidado", "payload": {"Title": "C"}},
    ]
    return data


class Server:
    """Datastore emulator. Options model event shapes and server reactions the protocol allows.

    variant: "normal", "v_string", "v_dict" or "group_strkeys" (update metadata shapes the
    official client ignores); lag: how many writes behind the /v1 snapshot is.
    """

    def __init__(
        self,
        *,
        show=False,
        max_payload=1_000_000,
        limits=None,
        echo_to_sender=True,
        login_info=True,
        variant="normal",
        lag=0,
    ):
        self.data, self.v = initial(show), 1
        self.max_payload = max_payload
        self.limits = limits or {"maxRequestsPerSec": 20, "maxBytesPerMin": 5_000_000}
        self.echo_to_sender, self.login_info = echo_to_sender, login_info
        self.variant, self.lag = variant, lag
        self.clients, self.errors, self.received, self.connections = set(), [], [], 0
        self.snapshots, self.history, self.update_times = 0, [], []
        self.drop_next_update = False  # close the socket instead of acknowledging the next update
        self.ignore_updates = False  # acknowledge updates without storing or broadcasting them
        self.dump()

    def dump(self):
        self.history.append(json.dumps({"data": self.data, "v": self.v}))
        self.snapshot_json = self.history[max(0, len(self.history) - 1 - self.lag)]

    def payload(self, overlay="OV1"):
        return self.data["compExtracts"]["CE"]["compositions"][overlay]["dataSources"]["composition"]["controlNode"][
            "payload"
        ]

    def slots(self, overlay="OV1"):
        return self.data["storage"]["Slots"][overlay]

    async def broadcast(self, data, meta, sender=None):
        for c in list(self.clients):
            if c is sender and not self.echo_to_sender:
                continue
            await c.send("42" + json.dumps(["update", data] + ([meta] if meta is not None else [])))

    async def mutate(self, data, meta=None, sender=None):
        if sender is not None:
            self.update_times.append(time.monotonic())
        for k, v in data.items():
            js_set_path(self.data, k, v)
        self.v += 1
        self.dump()
        m = None if meta is False else {"v": self.v, **(meta or {})}
        if m is not None and self.variant == "v_string":
            m["v"] = f"r{self.v}"
        elif m is not None and self.variant == "v_dict":
            m["v"] = {"n": self.v}
        payload = dict(data)
        if self.variant == "group_strkeys":
            payload["__group_update__"] = {"batch-a": list(data)}
        await self.broadcast(payload, m, sender)

    async def handler(self, ws):
        self.connections += 1
        await ws.send(
            "0"
            + json.dumps(
                {
                    "sid": "e",
                    "upgrades": [],
                    "pingInterval": 25000,
                    "pingTimeout": 20000,
                    "maxPayload": self.max_payload,
                }
            )
        )
        try:
            first = await ws.recv()
        except ConnectionClosed:  # the plugin may close a connection it no longer needs before connecting
            return
        if first != "40":
            self.errors.append("no Socket.IO connect packet")
            return
        await ws.send("40" + json.dumps({"sid": f"sock{self.connections}"}))
        logged = False
        try:
            async for text in ws:
                self.received.append(text)
                if text == "3":
                    continue
                _, ack, args = parse(text[1:])
                cb = None if ack is None else functools.partial(send_ack, ws, ack)
                if args[0] == "login":
                    if cb is None:
                        self.errors.append("login without callback")
                        continue
                    logged = True
                    self.clients.add(ws)
                    await cb({"rateLimitInfo": self.limits} if self.login_info else {"ok": True})
                elif args[0] == "update":
                    if cb is None or not logged:
                        self.errors.append("update without callback/login")
                        continue
                    if self.drop_next_update:  # the server dies before acknowledging
                        self.drop_next_update = False
                        await ws.close(1011)
                        return
                    if self.ignore_updates:
                        self.v += 1
                        self.dump()
                    else:
                        await self.mutate(args[1]["data"], {"userData": args[1]["userData"]}, sender=ws)
                    await cb({"success": True})
        finally:
            self.clients.discard(ws)


async def send_ack(ws, ack, *args):
    await ws.send("43" + str(ack) + json.dumps(list(args)))


@contextlib.asynccontextmanager
async def serving(server):
    """Point the plugin's Datastore at the emulator for the duration of the block."""

    def read(self, url, html=False):
        if html:
            return "<script>window.singularAppInstance = {\n  datastore: 'DS1',\n};</script>"
        server.snapshots += 1
        return json.loads(server.snapshot_json)

    async with serve(server.handler, "127.0.0.1", 0, max_size=server.max_payload) as srv:
        port = srv.sockets[0].getsockname()[1]
        url = f"ws://127.0.0.1:{port}/socket.io/?EIO=4&transport=websocket&ds="
        with (
            mock.patch.object(datastore.Datastore, "socket_url", url),
            mock.patch.object(datastore.Datastore, "_read", read),
        ):
            yield port


# ── UNO App API ──


class Backend:
    """The documented App API commands the runtime uses, applied to the emulator's data."""

    def __init__(self, server, latency=0.03):
        self.server, self.latency, self.fail = server, latency, False
        self.fail_tokens = set()  # control apps that answer every command with an error
        self.log = []  # (command, overlay id, content or values, monotonic time, token)

    def api(self, token):
        return FakeAPI(token, self)

    def calls(self):
        return [(c[0], c[1]) for c in self.log]

    def names(self):
        return [c[0] for c in self.log]


class FakeAPI:
    def __init__(self, token, backend):
        self.token, self.backend = token, backend

    async def call(self, command, **values):
        b, server = self.backend, self.backend.server
        target = values.get("id")
        if (b.fail and command == "GetOverlays") or self.token in b.fail_tokens:
            raise UnoError("UNO HTTP 500. Check the token or try again later.")
        states = server.data["compExtracts"]["CE"].get("compositionStates")
        if command == "GetOverlays":
            return [{"id": k, "name": k, "visible": v == "In"} for k, v in (states or {"OV1": "Out1"}).items()]
        detail = dict(values.get("content") or {})
        if command.startswith("TakeOverlay"):
            detail = {"value": values.get("value")}
        b.log.append((command, target, detail, time.monotonic(), self.token))
        await asyncio.sleep(b.latency)
        if command == "SetOverlayContent":
            await server.mutate({BASE.format(target) + "." + k: v for k, v in values["content"].items()})
        elif command in ("ShowOverlay", "HideOverlay") and states and target in states:
            await server.mutate(
                {f"compExtracts.CE.compositionStates.{target}": "In" if command == "ShowOverlay" else "Out1"}
            )
        elif command == "HideAllOverlays" and states:
            await server.mutate({f"compExtracts.CE.compositionStates.{k}": "Out1" for k in states})
        elif command in ("TakeOverlayNextSlot", "TakeOverlayPreviousSlot", "TakeOverlaySlotNumber"):
            slots = server.slots(target)
            ids = [s["id"] for s in slots["data"]]
            i = ids.index(slots["currentSlotId"])
            i = {"TakeOverlayNextSlot": i + 1, "TakeOverlayPreviousSlot": i - 1}.get(
                command, (values.get("value") or 1) - 1
            )
            await server.mutate({f"storage.Slots.{target}.currentSlotId": ids[i % len(ids)]})
        return True


# ── OBS Studio (obs-websocket 5) ──


class FakeObs:
    """obs-websocket 5 subset: Hello/Identify with SHA-256 auth, requests and CurrentProgramSceneChanged."""

    def __init__(self, password="secret"):
        self.password, self.scene, self.requests, self.clients = password, "Main", [], set()
        self.streaming, self.broken = False, set()
        # GetSceneItemList fields as obs-websocket 5 builds them (utils/Obs_ArrayHelper.cpp, since 5.0.0):
        # inputKind for inputs, isGroup for scenes and groups, null otherwise.
        self.items = {
            "Cam": [
                {"sourceName": "Lower", "inputKind": "browser_source", "isGroup": None},
                {"sourceName": "Webcam", "inputKind": "v4l2_input", "isGroup": None},
                {"sourceName": "Layers", "inputKind": None, "isGroup": True},
                {"sourceName": "Nested", "inputKind": None, "isGroup": False},
            ],
            "Layers": [{"sourceName": "Score", "inputKind": "browser_source", "isGroup": None}],
            "Nested": [
                {"sourceName": "Ticker", "inputKind": "browser_source", "isGroup": None},
                {"sourceName": "Lower", "inputKind": "browser_source", "isGroup": None},
                {"sourceName": "Cam", "inputKind": None, "isGroup": False},
            ],
        }

    async def handler(self, ws):
        try:
            await self.session(ws)
        except ConnectionClosed:  # a client may leave mid-handshake, as the plugin does when settings change
            pass
        finally:
            self.clients.discard(ws)

    async def session(self, ws):
        salt, challenge = "c2FsdA==", "Y2hhbGxlbmdl"
        hello = {
            "obsWebSocketVersion": "5.5.2",
            "rpcVersion": 1,
            "authentication": {"salt": salt, "challenge": challenge},
        }
        await ws.send(json.dumps({"op": 0, "d": hello}))
        ident = json.loads(await ws.recv())["d"]
        secret = base64.b64encode(hashlib.sha256((self.password + salt).encode()).digest()).decode()
        expected = base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()
        if ident.get("authentication") != expected:
            await ws.close(4009)
            return
        await ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        self.clients.add(ws)
        async for raw in ws:
            d = json.loads(raw)["d"]
            self.requests.append((d["requestType"], d.get("requestData")))
            data = {
                "GetCurrentProgramScene": {"sceneName": self.scene},
                "GetStreamStatus": {"outputActive": self.streaming},
                "GetRecordStatus": {"outputActive": False},
                "GetSceneList": {"scenes": [{"sceneName": "Main"}, {"sceneName": "Cam"}]},
                "GetInputList": {"inputs": [{"inputName": "UNO Browser"}]},
            }.get(d["requestType"], {})
            status = {"result": True, "code": 100}
            if d["requestType"] in ("GetSceneItemList", "GetGroupSceneItemList"):
                data = {"sceneItems": self.items.get((d.get("requestData") or {}).get("sceneName"), [])}
            if (d.get("requestData") or {}).get("inputName") in self.broken:
                status = {"result": False, "code": 600, "comment": "No source was found"}
            response = {"requestType": d["requestType"], "requestId": d["requestId"], "requestStatus": status}
            await ws.send(json.dumps({"op": 7, "d": {**response, "responseData": data}}))
            if d["requestType"] == "SetCurrentProgramScene":
                await self.switch(d["requestData"]["sceneName"])

    async def stream(self, active):
        self.streaming = active
        event = {"eventType": "StreamStateChanged", "eventIntent": 64, "eventData": {"outputActive": active}}
        for c in list(self.clients):
            await c.send(json.dumps({"op": 5, "d": event}))

    async def switch(self, scene):
        self.scene = scene
        event = {"eventType": "CurrentProgramSceneChanged", "eventIntent": 4, "eventData": {"sceneName": scene}}
        for c in list(self.clients):
            await c.send(json.dumps({"op": 5, "d": event}))


# ── OpenDeck events (src-tauri/src/events/outbound) ──


def _payload(ctx, settings, controller):
    return {
        "settings": settings,
        "coordinates": {"row": 0, "column": sum(map(ord, ctx)) % 5},
        "controller": controller,
        "state": 0,
        "isInMultiAction": False,
    }


def appear(ctx, action, settings, controller="Keypad", device="sd-test"):
    """willAppear as OpenDeck sends it (GenericInstancePayload)."""
    return {
        "event": "willAppear",
        "action": PREFIX + action,
        "context": ctx,
        "device": device,
        "payload": _payload(ctx, settings, controller),
    }


def disappear(ctx, action, settings, controller="Keypad", device="sd-test"):
    """willDisappear: OpenDeck sends it when the profile changes, the device goes away or the key is deleted."""
    return {**appear(ctx, action, settings, controller, device), "event": "willDisappear"}


def press(ctx, action, settings, event="keyDown", device="sd-test", **extra):
    """keyDown/keyUp, or dialDown/dialUp/dialRotate (Encoder payloads) with ticks=… for rotation."""
    if event.startswith("dial"):
        payload = {"controller": "Encoder", "settings": settings, "coordinates": {"row": 0, "column": 0}}
        if event == "dialRotate":
            payload.update(ticks=extra.pop("ticks", 1), pressed=False)
    else:
        payload = _payload(ctx, settings, "Keypad")
    return {
        "event": event,
        "action": PREFIX + action,
        "context": ctx,
        "device": device,
        "payload": {**payload, **extra},
    }


def dial(ctx, field="Score", ticks=1, **extra):
    """A Knob Control turned one click clockwise on OV1::<field>."""
    settings = {
        **TOKEN,
        "cwAction": "increment",
        "ccwAction": "decrement",
        "cwFieldComposite": f"OV1::{field}",
        "ccwFieldComposite": f"OV1::{field}",
        **extra,
    }
    return press(ctx, "knob", settings, "dialRotate", ticks=ticks)


def settings_changed(ctx, action, settings):
    return {
        "event": "didReceiveSettings",
        "action": PREFIX + action,
        "context": ctx,
        "device": "sd-test",
        "payload": _payload(ctx, settings, "Keypad"),
    }


# ── What the plugin sent back ──


def decoded_images(sent, ctx):
    return [
        base64.b64decode(e["payload"]["image"].split(",", 1)[1]).decode()
        for e in sent
        if e.get("event") == "setImage" and e.get("context") == ctx
    ]


def last_image(sent, ctx):
    images = decoded_images(sent, ctx)
    return images[-1] if images else ""


def background_of(sent, ctx):
    img = last_image(sent, ctx)
    return img.split('<rect width="144" height="144" fill="', 1)[1].split('"', 1)[0] if img else ""


def errors(sent):
    return [e["payload"]["error"] for e in sent if (e.get("payload") or {}).get("type") == "error"] + [
        e["context"] for e in sent if e.get("event") == "showAlert"
    ]


def state(server, overlay):
    return server.data["compExtracts"]["CE"]["compositionStates"][overlay]


# ── Test case ──


class Case(unittest.IsolatedAsyncioTestCase):
    """One scenario per test method; each named check is a subTest, so one failure does not hide the rest."""

    def check(self, name, condition, detail=""):
        with self.subTest(name):
            self.assertTrue(condition, detail)

    def runtime(self, server, backend=None):
        """A Runtime wired to the emulators; `self.sent` collects what it sends to OpenDeck."""
        self.backend = backend or Backend(server)
        self.sent = []

        async def send(event):
            self.sent.append(event)

        self.rt = runtime.Runtime(
            send, PREFIX + "sdPlugin", api_factory=self.backend.api, store_factory=datastore.Datastore
        )
        return self.rt

    async def idle(self, extra=0.3):
        """Wait until queued jobs are done. Clocks, Auto Next, watchers and blinking are background work."""
        r = self.rt
        await asyncio.sleep(0.2)

        def background():
            tasks = {r.worker, r.clock_task, r.source_task, r.ticker, r.arm_task, r.status_task, r.lock_task}
            return tasks | {st["auto"] for st in r.sources.values()}

        for _ in range(600):
            if not (any(r.queues) or r.accumulators or any(not t.done() for t in r.tasks if t not in background())):
                break
            await asyncio.sleep(0.05)
        await asyncio.sleep(extra)

    async def settle(self, seconds=0.6):
        await asyncio.sleep(seconds)
        await self.idle(0.2)

    async def show(self, *overlays):
        """Put overlays on air through the App API, as another operator would."""
        for overlay in overlays:
            await self.backend.api("TESTTOKEN").call("ShowOverlay", id=overlay)
        await self.settle(0.3)

    async def eventually(self, condition, timeout=5.0):
        """Poll a condition instead of sleeping a fixed time; returns its last value."""
        end = time.monotonic() + timeout
        while not (ok := condition()) and time.monotonic() < end:
            await asyncio.sleep(0.05)
        return ok

    async def request(self, payload, ctx="C1", action="toggle", timeout=40):
        """An inspector request (sendToPlugin) and the plugin's answer (sendToPropertyInspector)."""
        rid = f"r{time.monotonic_ns()}"
        await self.rt.handle(
            {
                "event": "sendToPlugin",
                "action": PREFIX + action,
                "context": ctx,
                "payload": {**payload, "requestId": rid},
            }
        )
        found = await self.eventually(
            lambda: next((e["payload"] for e in self.sent if (e.get("payload") or {}).get("requestId") == rid), None),
            timeout,
        )
        if not found:
            raise AssertionError(f"no answer to {payload.get('type')}")
        return found

    async def set_global(self, store, **changes):
        """OpenDeck's didReceiveGlobalSettings after the inspector saved `changes` into `store`."""
        store.update(changes)
        await self.rt.handle({"event": "didReceiveGlobalSettings", "payload": {"settings": deepcopy(store)}})

    async def enter(self, context):
        """An async context kept until the test ends (unittest's enterAsyncContext needs Python 3.11)."""
        value = await context.__aenter__()
        self.addAsyncCleanup(context.__aexit__, None, None, None)
        return value

    async def start_obs(self, obs, store):
        """The emulated OBS, connected through the global settings in `store`, as the settings page does."""
        server = await self.enter(serve(obs.handler, "127.0.0.1", 0))
        port = server.sockets[0].getsockname()[1]
        await self.set_global(store, obsEnabled=True, obsHost="127.0.0.1", obsPort=str(port), obsPassword="secret")
        await self.eventually(lambda: self.rt.obs and self.rt.obs.connected and self.rt.obs.scene, 3)
