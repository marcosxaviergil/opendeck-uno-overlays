"""UNO Control App storage adapter, isolated from the public command API.

This is the website's internal interface, not a documented UNO REST endpoint.
Every part of the wire contract follows published code (docs/SOURCES.md):

- Engine.IO v4 packets and the open packet (pingInterval, pingTimeout,
  maxPayload): engine.io-parser 5.2.3 commons.js, engine.io 6.6.11 socket.js.
  engine.io passes maxPayload to its WebSocket server, which closes the
  connection when a client message is larger (server.js, "maxPayload").
- Socket.IO v5 packet strings, including acknowledgement ids:
  socket.io-parser 4.2.7 encodeAsString()/decodeString().
- login and update, both emitted WITH an acknowledgement callback,
  userData.sender, rateLimitInfo and dot-path updates: official
  singular-datastore 1.0.1 client (npm, maintainer "singularlive"),
  index.js connect(), updateJsonObject() and createRateLimiter().
  That client reads the /v1 snapshot once per connection, applies EVERY
  "update" event with updateJsonObject() (no version or group checks), only
  logs "set", and treats the update acknowledgement as completion.
- Datastore id in the Control App page, ds query and storage.Slots paths:
  UNO Control App captures used by 1.1.0.
"""

import asyncio
import contextlib
import http.client
import json
import logging
import math
import re
import time
import urllib.request
from copy import deepcopy

from uno import VERSION
from uno.api import NoRedirect, UnoError, token_value
from uno.i18n import tr
from uno.jsonpath import Skip, ancestors, get_path, js_order, set_path
from uno.timeouts import within
from uno.values import merge

__all__ = ["Datastore", "component", "decode"]

log = logging.getLogger(__name__)

ACK_TIMEOUT = 15  # seconds for a Socket.IO acknowledgement
ECHO_TIMEOUT = 1.5  # seconds for the broadcast of an acknowledged change


def bootstrap(html):
    # Read one inert assignment; never evaluate downloaded JavaScript.
    match = re.search(r"window\.singularAppInstance\s*=\s*\{(.*?)\n\s*};", html, re.S)
    if not match:
        raise UnoError(tr("UNO did not expose the Control App connection. Check the control token."))
    match = re.search(r"\bdatastore\s*:\s*['\"]([A-Za-z0-9_-]+)['\"]", match[1])
    if not match:
        raise UnoError(tr("This Control App does not expose a supported datastore. Changes were not saved."))
    return match[1]


def decode(text):
    """Socket.IO packet without the Engine.IO "4" prefix (socket.io-parser decodeString)."""
    kind = int(text[0]) if text[:1].isascii() and text[:1].isdigit() else -1
    if not 0 <= kind <= 6:
        raise ValueError("unknown packet type")
    if kind in (5, 6):
        raise ValueError("binary packets are not used by the datastore client")
    i, nsp = 1, "/"
    if text.startswith("/", i):
        end = text.find(",", i)
        end = len(text) if end < 0 else end
        nsp, i = text[i:end], end + 1
    j = i
    while j < len(text) and "0" <= text[j] <= "9":
        j += 1
    ack = int(text[i:j]) if j > i else None
    data = json.loads(text[j:]) if j < len(text) else None
    return kind, nsp, ack, data


def component(value):
    value = str(value)
    if not value or any(c in value for c in "./\\\x00"):
        raise UnoError(tr("UNO returned an unsupported storage identifier."))
    return value


def positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 and not isinstance(value, bool) else None


def describe(exc):
    """Log text without URLs, tokens or response bodies."""
    if isinstance(exc, UnoError):
        return str(exc)
    name = type(exc).__name__
    if name.startswith("ConnectionClosed") or name == "InvalidStatus":
        return f"{name}: {exc}"
    return name


def shape(value):
    """Type summary for logs; values themselves are never logged."""
    if isinstance(value, dict):
        return "object{" + ",".join(sorted(map(str, value))[:8]) + ("…" if len(value) > 8 else "") + "}"
    if isinstance(value, list):
        return f"array[{len(value)}]"
    return type(value).__name__


def consume(future):
    # Avoid "exception was never retrieved" when nobody writes on this connection.
    if not future.cancelled():
        future.exception()


# The server counts messages when they arrive: a delay on the way can push one of a window into the next.
# Starting the next window this much later keeps the server's count within the limit.
JITTER = 0.1


class RateLimiter:
    """createRateLimiter(limit, interval) from the official singular-datastore client."""

    def __init__(self, limit, interval):
        self.limit, self.interval = limit, interval
        self.calls, self.start = 0, None

    def _window(self, now):
        if self.start is None:
            self.start = now
        if now - self.start > self.interval:
            self.calls, self.start = 0, now

    def allow(self, by=1):
        self._window(time.monotonic())
        self.calls += by
        return self.calls <= self.limit

    def delay(self, by=1):
        """Seconds until allow(by) can pass in the next window; 0 when it can pass now."""
        now = time.monotonic()
        self._window(now)
        if self.calls + by <= self.limit:
            return 0
        return max(0.0, self.start + self.interval - now) + JITTER


class Datastore:
    control_url = "https://app.overlays.uno/control/"
    snapshot_url = "https://datastore.singular.live/v1/"
    socket_url = "wss://datastore.singular.live/socket.io/?EIO=4&transport=websocket&ds="

    def __init__(self, token, on_change):
        self.token = token_value(token)
        self.on_change = on_change
        self.data = {}
        self.ready = asyncio.Event()
        self.changed = asyncio.Condition()
        self.runner = None
        self.ws = None
        self.error = "Connecting to UNO…"
        self.pending = []
        self.buffering = True
        self.write_lock = asyncio.Lock()
        self.acks, self.next_ack = {}, 0
        self.login = None
        self.max_payload = None
        self.events = 0  # applied update events
        self.touched = {}  # path -> event number that last set it
        self.logged_meta = False

    def _read(self, url, html=False):
        # Fixed https hosts (snapshot_url / Control App page); the token is validated by token_value().
        req = urllib.request.Request(url, headers={"User-Agent": f"OpenDeck-UNO-Overlays/{VERSION}"})  # noqa: S310
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=15) as response:
                raw = response.read(16_000_001)
            if len(raw) > 16_000_000:
                raise ValueError("oversized response")
            return raw.decode() if html else json.loads(raw)
        except (OSError, ValueError, http.client.HTTPException):
            raise UnoError(
                tr("Unable to read the UNO Control App datastore. Check the token and connection.")
            ) from None

    async def ensure(self):
        if self.runner is None:
            self.runner = asyncio.create_task(self.run())
        try:
            await within(self.ready.wait(), 25)
        except asyncio.TimeoutError:
            raise UnoError(self.error) from None
        return self

    async def snapshot(self):
        # Read once per connection, like the official client. Events received
        # while reading are replayed in order; replaying sets is idempotent.
        result = await asyncio.to_thread(self._read, self.snapshot_url + self.store_id)
        if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
            raise UnoError(tr("UNO returned an invalid datastore snapshot."))
        self.data = result["data"]
        queued, self.pending = self.pending, []
        self.buffering = False
        for value, meta in queued:
            self.apply(value, meta)

    def apply(self, value, meta):
        """socket.on('update', (msg, metadata)) of the official client: every key is applied."""
        if not self.logged_meta:
            self.logged_meta = True
            log.info(
                "UNO realtime update format: metadata %s, group key %s.",
                shape(meta),
                shape(value.get("__group_update__")) if "__group_update__" in value else "absent",
            )
        self.events += 1
        for path in js_order(value):
            if path == "__group_update__":
                continue  # the official client would store it as a plain key; nothing reads it
            try:
                set_path(self.data, path, value[path])
            except Skip as exc:
                log.warning("UNO realtime path skipped (%s): %s", exc, path)
                continue
            self.touched[path] = self.events

    def touched_since(self, path, mark):
        return any(self.touched.get(p, 0) > mark for p in ancestors(path))

    async def notify(self):
        async with self.changed:
            self.changed.notify_all()
        await self.on_change(self)

    def accept_login(self, args):
        # singular-datastore enables writes only inside the login callback,
        # after reading response.rateLimitInfo.maxBytesPerMin/maxRequestsPerSec.
        info = args[0].get("rateLimitInfo") if args and isinstance(args[0], dict) else None
        if not isinstance(info, dict):
            raise UnoError(tr("UNO did not accept the realtime login. Check the control token."))
        requests, size = positive(info.get("maxRequestsPerSec")), positive(info.get("maxBytesPerMin"))
        if requests is None or size is None:
            raise UnoError(tr("UNO returned unsupported realtime rate limits. Changes were not sent."))
        log.info("UNO realtime login acknowledged: %g requests/s, %g bytes/min.", requests, size)
        return RateLimiter(requests, 1.0), RateLimiter(size, 60.0)

    def acknowledge(self, ack_id, args):
        entry = self.acks.pop(ack_id, None)
        if entry is None:
            return  # socket.io-client ignores an unknown ack id
        future, accept = entry
        if future.done():
            return
        try:
            future.set_result(accept(args if isinstance(args, list) else []))
        except UnoError as exc:
            future.set_exception(exc)

    async def event(self, args):
        if not isinstance(args, list) or not args:
            return
        name = args[0]
        if name == "update" and len(args) >= 2 and isinstance(args[1], dict):
            meta = args[2] if len(args) >= 3 else None
            if self.buffering:
                self.pending.append((args[1], meta))
            else:
                self.apply(args[1], meta)
                await self.notify()
        elif name == "set":
            # socket.on('set') in the official client only logs the message.
            log.info("UNO realtime 'set' event received and ignored, as in the official client.")
        elif name in ("error", "unauthorized"):
            raise UnoError(tr("UNO refused datastore access. Check the control token."))

    async def receive(self):
        while True:
            packet = await within(self.ws.recv(), self.heartbeat)
            if not isinstance(packet, str):
                continue
            if packet == "2":
                await self.ws.send("3")
                continue
            if packet == "1":
                raise UnoError(tr("UNO closed the realtime session."))
            if not packet.startswith("4"):
                continue  # pong, upgrade and noop carry no data here
            try:
                kind, nsp, ack, data = decode(packet[1:])
            except ValueError:
                raise UnoError(tr("UNO sent an unsupported realtime packet.")) from None
            if nsp != "/":
                continue
            if kind == 3:
                self.acknowledge(ack, data)
            elif kind == 2:
                await self.event(data)
            elif kind in (1, 4):
                raise UnoError(tr("UNO disconnected the datastore session."))

    async def run(self):
        from websockets.asyncio.client import connect

        backoff = 1
        while True:
            reader = None
            try:
                html = await asyncio.to_thread(self._read, self.control_url + self.token, True)
                self.store_id = bootstrap(html)
                async with connect(
                    self.socket_url + self.store_id, open_timeout=15, ping_interval=None, max_size=16_000_000
                ) as ws:
                    self.ws = ws
                    packet = await within(ws.recv(), 15)
                    if not isinstance(packet, str) or not packet.startswith("0"):
                        raise UnoError(tr("Unsupported UNO realtime handshake."))
                    hello = json.loads(packet[1:])
                    self.heartbeat = (hello["pingInterval"] + hello["pingTimeout"]) / 1000 + 5
                    limit = hello.get("maxPayload")
                    self.max_payload = (
                        limit if isinstance(limit, int) and not isinstance(limit, bool) and limit > 0 else None
                    )
                    await ws.send("40")
                    packet = await within(ws.recv(), 15)
                    if not isinstance(packet, str) or not packet.startswith("40"):
                        raise UnoError(tr("UNO refused the realtime connection."))
                    self.sid = json.loads(packet[2:])["sid"]
                    self.buffering, self.pending = True, []
                    self.acks, self.next_ack = {}, 1
                    self.login = asyncio.get_running_loop().create_future()
                    self.login.add_done_callback(consume)
                    self.acks[0] = (self.login, self.accept_login)
                    # socket.emit('login', appId, writeToken, callback) -> ack id 0.
                    await ws.send("420" + json.dumps(["login", self.store_id, self.token], separators=(",", ":")))
                    reader = asyncio.create_task(self.receive())
                    await self.snapshot()
                    if reader.done():
                        await reader
                    self.ready.set()
                    await self.notify()
                    backoff = 1
                    await reader
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - reconnect loop / websocket send: any failure becomes a safe message
                self.error = (
                    str(exc) if isinstance(exc, UnoError) else "UNO realtime connection interrupted. Reconnecting…"
                )
                log.warning("UNO realtime connection lost: %s", describe(exc))
            finally:
                self.ready.clear()
                self.ws = None
                acks, self.acks = self.acks, {}
                for future, _ in acks.values():
                    if not future.done():
                        future.set_exception(
                            UnoError(
                                tr(
                                    "UNO disconnected before acknowledging the request. "
                                    "Reload to verify; nothing is retried automatically."
                                )
                            )
                        )
                if reader and reader is not asyncio.current_task():
                    reader.cancel()
                    await asyncio.gather(reader, return_exceptions=True)
                async with self.changed:
                    self.changed.notify_all()
                await self.on_change(self)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

    def locate(self, overlay_id):
        for extract_id, extract in self.data.get("compExtracts", {}).items():
            composition_id = extract.get("mainComposition") if overlay_id == extract_id else overlay_id
            node = (
                extract.get("compositions", {})
                .get(composition_id, {})
                .get("dataSources", {})
                .get("composition", {})
                .get("controlNode")
            )
            if isinstance(node, dict):
                return (
                    extract,
                    composition_id,
                    node,
                    (
                        f"compExtracts.{component(extract_id)}.compositions.{component(composition_id)}.dataSources.composition.controlNode"
                    ),
                )
        raise UnoError(tr("The overlay is absent from the UNO datastore. Reload the overlay list."))

    def node(self, overlay_id):
        _, _, node, path = self.locate(overlay_id)
        return path, node

    def on_air(self, overlay_id):
        # compositionStates: "In", "Out1" or "Out2" (singular-datastore getControl(),
        # Singular REST "Get a control app's control data").
        try:
            extract, composition_id, _, _ = self.locate(overlay_id)
        except UnoError:
            return False
        return (extract.get("compositionStates") or {}).get(composition_id) == "In"

    def content(self, overlay_id):
        return deepcopy(self.node(overlay_id)[1].get("payload") or {})

    def slots(self, overlay_id):
        return deepcopy(
            self.data.get("storage", {}).get("Slots", {}).get(overlay_id)
            or {"active": False, "currentSlotId": "", "data": []}
        )

    def slot(self, overlay_id, number=0, slot_id=""):
        slots = self.slots(overlay_id)
        items = slots.get("data") or []
        if not number and not slot_id:
            if not slots.get("active"):
                return None
            slot_id = slots.get("currentSlotId")
            if not slot_id:
                return None
        for index, slot in enumerate(items):
            if not isinstance(slot, dict):
                continue  # a JavaScript array hole is stored as null
            if (slot_id and slot.get("id") == slot_id) or (not slot_id and index + 1 == number):
                return index, slot
        raise UnoError(tr("The selected server slot no longer exists. Reload and select it again."))

    async def limits(self, login):
        if login is None:
            raise UnoError(tr("UNO realtime login has not started. Reload and try again."))
        try:
            return await within(asyncio.shield(login), ACK_TIMEOUT)
        except asyncio.TimeoutError:
            raise UnoError(tr("UNO did not acknowledge the realtime login. Changes were not sent.")) from None

    async def settle(self, updates, mark):
        """After an accepted change, wait briefly for its broadcast, then keep the accepted values.

        The official client never re-reads the snapshot after connecting. A value
        broadcast after `mark` wins (the server may normalize it); otherwise the
        accepted value is stored locally, as the broadcast would have done.
        """

        def settled(path, value):
            return get_path(self.data, path) == value or self.touched_since(path, mark)

        async with self.changed:
            with contextlib.suppress(asyncio.TimeoutError):  # no broadcast in time: stored locally below
                await within(
                    self.changed.wait_for(
                        lambda: not self.ready.is_set() or all(settled(p, v) for p, v in updates.items())
                    ),
                    ECHO_TIMEOUT,
                )
        missing = {p: v for p, v in updates.items() if not settled(p, v)}
        if missing and self.ready.is_set():
            self.apply(missing, None)
            await self.notify()

    async def write(self, updates):
        if not updates:
            return
        async with self.write_lock:
            await self.ensure()
            ws = self.ws
            requests, size_limit = await self.limits(self.login)
            # socket.emit('update', {data, userData: {sender: socket.id}}, callback)
            body = json.dumps(
                ["update", {"data": updates, "userData": {"sender": self.sid}}],
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            ack_id, self.next_ack = self.next_ack, self.next_ack + 1
            frame = f"42{ack_id}{body}"
            size = len(frame.encode())
            if self.max_payload and size > self.max_payload:
                # engine.io would close the WebSocket for a larger message.
                raise UnoError(
                    tr(
                        "This change is too large for one UNO realtime message ({size} of {limit} bytes). "
                        "Nothing was sent.",
                        size=size,
                        limit=self.max_payload,
                    )
                )
            payload_size = len(body.encode())
            if payload_size > size_limit.limit:
                raise UnoError(
                    tr(
                        "Rate limit exceeded. {limit} bytes per minute. Nothing was sent.",
                        limit=f"{size_limit.limit:g}",
                    )
                )
            # The queue waits for the next window instead of dropping the change.
            await asyncio.sleep(requests.delay())
            await asyncio.sleep(size_limit.delay(payload_size))
            if not requests.allow():
                raise UnoError(
                    tr(
                        "Rate limit exceeded. {limit} requests per second. Nothing was sent.",
                        limit=f"{requests.limit:g}",
                    )
                )
            if not size_limit.allow(payload_size):
                raise UnoError(
                    tr(
                        "Rate limit exceeded. {limit} bytes per minute. Nothing was sent.",
                        limit=f"{size_limit.limit:g}",
                    )
                )
            if ws is None or ws is not self.ws or not self.ready.is_set():
                raise UnoError(tr("UNO disconnected before the save was sent. Nothing was sent."))
            future = asyncio.get_running_loop().create_future()
            self.acks[ack_id] = (future, lambda args: args)
            mark = self.events
            try:
                try:
                    await ws.send(frame)
                except Exception:  # noqa: BLE001 - reconnect loop / websocket send: any failure becomes a safe message
                    raise UnoError(
                        tr("UNO disconnected while saving. Reload to verify; the write was not retried.")
                    ) from None
                response = await within(asyncio.shield(future), ACK_TIMEOUT)
            except asyncio.TimeoutError:
                raise UnoError(
                    tr("UNO did not acknowledge the save. Reload to verify; the write was not retried.")
                ) from None
            finally:
                self.acks.pop(ack_id, None)
            first = response[0] if response else None
            if isinstance(first, dict) and (first.get("success") is False or first.get("error")):
                # The official client does not inspect the response; never report success on an explicit failure.
                log.warning("UNO realtime save answered with failure: %s", shape(first))
                raise UnoError(tr("UNO refused the save. Reload to verify; the write was not retried."))
            await self.settle(updates, mark)

    async def save_slot(self, overlay_id, patch, number=0, slot_id=""):
        selected = self.slot(overlay_id, number, slot_id)
        if selected is None:
            return
        index, slot = selected
        prefix = f"storage.Slots.{component(overlay_id)}.data.{index}.payload"
        # Whole field values preserve structured field types; sibling fields,
        # other slots, names and current selection stay untouched.
        updates = {
            prefix + "." + component(key): merge(slot.get("payload", {}).get(key), value)
            for key, value in patch.items()
        }
        await self.write(updates)

    async def sync_content(self, overlay_id, patch, mark):
        """Keep the local copy current after SetOverlayContent returned status 200."""
        path = self.node(overlay_id)[0] + ".payload"
        await self.settle({f"{path}.{component(key)}": value for key, value in patch.items()}, mark)

    async def close(self):
        if self.runner:
            self.runner.cancel()
            await asyncio.gather(self.runner, return_exceptions=True)
