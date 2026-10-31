"""obs-websocket 5.x client (OBS Studio 28+), protocol per obs-websocket docs/generated/protocol.md.

Hello(0) -> Identify(1, SHA256 auth) -> Identified(2); Event(5); Request(6)/RequestResponse(7).
Only Scenes (1 << 2) and Outputs (1 << 6) events are subscribed.
"""

import asyncio
import base64
import hashlib
import itertools
import json
import logging
import re

from uno.api import UnoError
from uno.i18n import tr
from uno.timeouts import within

__all__ = ["Obs", "auth", "check_address"]

log = logging.getLogger(__name__)

SUBSCRIPTIONS = (1 << 2) | (1 << 6)
HOST = re.compile(r"[A-Za-z0-9.-]{1,253}")  # a host name or IPv4 address: it becomes ws://host:port


def check_address(host, port):
    """Settings come from the settings page and from backups: never build a URL from anything else."""
    if not HOST.fullmatch(host):
        raise UnoError(tr("Type the OBS host name or IPv4 address, for example 127.0.0.1."))
    if not 1 <= port <= 65535:
        raise UnoError(tr("Type the OBS WebSocket port, 1 to 65535 (OBS uses 4455)."))


def auth(password, salt, challenge):
    secret = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()


class Obs:
    def __init__(self, host, port, password, on_event):
        self.url = f"ws://{host}:{port}"
        self.password, self.on_event = password, on_event
        self.ws, self.pending, self.ids = None, {}, itertools.count()
        self.scene, self.streaming, self.recording = None, False, False
        self.runner = asyncio.create_task(self.run())

    @property
    def connected(self):
        return self.ws is not None

    async def request(self, kind, data=None):
        if self.ws is None:
            raise UnoError(tr("OBS is not connected. Check Tools → WebSocket Server Settings in OBS."))
        request_id = str(next(self.ids))
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        try:
            await self.ws.send(
                json.dumps({"op": 6, "d": {"requestType": kind, "requestId": request_id, "requestData": data or {}}})
            )
            response = await within(future, 10)
        except asyncio.TimeoutError:
            raise UnoError(tr("OBS did not answer {request}.", request=kind)) from None
        finally:
            self.pending.pop(request_id, None)
        status = response.get("requestStatus") or {}
        if not status.get("result"):
            raise UnoError(
                tr("OBS refused {request}: {reason}.", request=kind, reason=status.get("comment") or status.get("code"))
            )
        return response.get("responseData") or {}

    async def run(self):
        from websockets.asyncio.client import connect

        backoff = 1
        while True:
            try:
                async with connect(
                    self.url, subprotocols=["obswebsocket.json"], open_timeout=10, max_size=16_000_000, proxy=None
                ) as ws:
                    hello = json.loads(await within(ws.recv(), 10))["d"]
                    identify = {"rpcVersion": 1, "eventSubscriptions": SUBSCRIPTIONS}
                    if "authentication" in hello:
                        challenge = hello["authentication"]
                        identify["authentication"] = auth(self.password, challenge["salt"], challenge["challenge"])
                    await ws.send(json.dumps({"op": 1, "d": identify}))
                    if json.loads(await within(ws.recv(), 10)).get("op") != 2:
                        raise UnoError(tr("OBS did not identify the connection."))
                    self.ws, backoff = ws, 1
                    reader = asyncio.create_task(self.receive(ws))
                    try:
                        self.scene = (await self.request("GetCurrentProgramScene")).get("sceneName")
                        self.streaming = (await self.request("GetStreamStatus")).get("outputActive", False)
                        self.recording = (await self.request("GetRecordStatus")).get("outputActive", False)
                        log.info("OBS connected: program scene %r.", self.scene)
                        await self.on_event("connected", None)
                        await reader
                    finally:
                        reader.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - reconnect loop survives any failure
                log.warning("OBS connection lost: %s", exc if isinstance(exc, UnoError) else type(exc).__name__)
            finally:
                self.ws = None
                for future in self.pending.values():
                    future.cancel()
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

    async def receive(self, ws):
        async for raw in ws:
            message = json.loads(raw)
            data = message.get("d") or {}
            if message.get("op") == 7:
                future = self.pending.get(data.get("requestId"))
                if future and not future.done():
                    future.set_result(data)
            elif message.get("op") == 5:
                kind, event = data.get("eventType"), data.get("eventData") or {}
                attribute, value = {
                    "CurrentProgramSceneChanged": ("scene", event.get("sceneName")),
                    "StreamStateChanged": ("streaming", bool(event.get("outputActive"))),
                    "RecordStateChanged": ("recording", bool(event.get("outputActive"))),
                }.get(kind, (None, None))
                if attribute and getattr(self, attribute) != value:
                    before = getattr(self, attribute)
                    setattr(self, attribute, value)
                    await self.on_event(kind, before)

    async def close(self):
        self.runner.cancel()
        await asyncio.gather(self.runner, return_exceptions=True)
