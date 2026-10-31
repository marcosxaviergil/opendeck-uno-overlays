"""Realtime datastore: acknowledged login/update, slots, rate limits and update shapes (loopback)."""

import asyncio
import json
import time

from support import Case, Server, UnoError, datastore, dial, errors, serving

EDIT = {"type": "uno.edit", "token": "TESTTOKEN", "id": "OV1"}
SLOT = {"type": "uno.slot", "token": "TESTTOKEN", "id": "OV1"}


def new_store():
    return datastore.Datastore("TESTTOKEN", lambda s: asyncio.sleep(0))


class EditsAndSlots(Case):
    async def test_edits_and_slots_are_acknowledged_and_saved(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            await r.handle(
                {
                    "event": "willAppear",
                    "action": "dev.br.consciencia.opendeck.uno-overlays.toggle",
                    "context": "C1",
                    "payload": {"settings": {"token": "TESTTOKEN", "overlayId": "OV1"}},
                }
            )
            read = await self.request({"type": "uno.read", "token": "TESTTOKEN", "command": "GetSlots", "id": "OV1"})
            self.check("read slots", read.get("data", {}).get("currentSlotId") == "s1", str(read))
            login = [t for t in server.received if '"login"' in t]
            self.check(
                "login emitted with ack id 0 (singular-datastore contract)", login and login[0].startswith("420[")
            )

            res = await self.request({**EDIT, "slotNumber": 0, "slotId": "", "patch": {"Title": "Edited"}})
            live, slot = server.payload(), server.slots()["data"][0]["payload"]
            self.check(
                "editing Live in slot mode saves Live and the current slot",
                res.get("data") == {"saved": True} and live["Title"] == "Edited" and slot["Title"] == "Edited",
                f"{res} live={live} slot={slot}",
            )
            updates = [t for t in server.received if '"update"' in t]
            self.check(
                "update emitted with an ack id", updates and updates[-1][:2] == "42" and updates[-1][2].isdigit()
            )

            res = await self.request(
                {**SLOT, "operation": "add", "slotId": "s2", "name": "Two", "content": {"Title": "Second", "Score": 5}}
            )
            ids = [s["id"] for s in server.slots()["data"]]
            self.check(
                "add slot saved and returned",
                not res.get("error") and ids == ["s1", "s2"] and [s["id"] for s in res["data"]["data"]] == ["s1", "s2"],
                f"{res.get('error')} {ids}",
            )
            res = await self.request({**EDIT, "slotNumber": 2, "slotId": "s2", "patch": {"Score": 9}})
            s2 = server.slots()["data"][1]["payload"]
            self.check(
                "editing an inactive slot leaves Live alone",
                res.get("data") == {"saved": True} and s2["Score"] == 9 and live["Score"] == 1,
            )
            res = await self.request({**SLOT, "operation": "rename", "slotId": "s2", "name": "Renamed"})
            self.check("rename slot", not res.get("error") and server.slots()["data"][1]["name"] == "Renamed")

            store = r.stores["TESTTOKEN"]
            connections = server.connections
            await server.mutate({"storage.Slots.OV1.data.2": {"id": "s3", "name": "Web", "payload": {}}}, meta=False)
            await self.eventually(lambda: len(store.slots("OV1")["data"]) == 3, 2)
            self.check(
                "an external append without metadata is applied without reconnecting",
                [s["id"] for s in store.slots("OV1")["data"]] == ["s1", "s2", "s3"]
                and server.connections == connections
                and store.ready.is_set(),
            )

            snapshots = server.snapshots
            server.payload()["Title"] = "FromSet"
            server.dump()
            for c in list(server.clients):
                await c.send("42" + json.dumps(["set", {"partial": True}, {"v": server.v}]))
            await asyncio.sleep(0.5)
            self.check(
                "'set' is only logged, as in the official client (no snapshot read, data unchanged)",
                server.snapshots == snapshots
                and store.content("OV1")["Title"] == "Edited"
                and "partial" not in store.data,
            )

            res = await self.request(
                {**SLOT, "operation": "add", "slotId": "s4", "name": "Big", "content": {"Title": "x" * 1_100_000}}
            )
            self.check(
                "a write larger than maxPayload is refused before sending; connection kept",
                "too large" in (res.get("error") or "") and server.connections == connections and store.ready.is_set(),
                res.get("error"),
            )
            res = await self.request({**SLOT, "operation": "remove", "slotId": "s2"})
            self.check(
                "remove slot", not res.get("error") and [s["id"] for s in server.slots()["data"]] == ["s1", "s3"]
            )
            self.check("no server-side protocol errors", not server.errors, str(server.errors))
            await r.close()

    async def test_save_is_kept_when_the_sender_gets_no_broadcast(self):
        server = Server(echo_to_sender=False)
        async with serving(server):
            r = self.runtime(server)
            res = await self.request({**EDIT, "slotNumber": 1, "slotId": "s1", "patch": {"Title": "NoEcho"}})
            store = r.stores["TESTTOKEN"]
            self.check(
                "saved without a broadcast to the sender",
                res.get("data") == {"saved": True} and store.slots("OV1")["data"][0]["payload"]["Title"] == "NoEcho",
                str(res),
            )
            await r.close()


class Connection(Case):
    async def test_request_rate_limit_waits_instead_of_flooding(self):
        server = Server(limits={"maxRequestsPerSec": 1, "maxBytesPerMin": 5_000_000})
        async with serving(server):
            store = new_store()
            await store.ensure()
            t0 = time.monotonic()
            await store.write({"storage.Slots.OV1.data.0.name": "a"})
            await store.write({"storage.Slots.OV1.data.0.name": "b"})
            elapsed = time.monotonic() - t0
            self.check("second write waits for the next window", elapsed >= 1.0, f"{elapsed:.2f}s")
            self.check("both writes stored", server.slots()["data"][0]["name"] == "b")
            await store.close()

    async def test_login_without_rate_info_blocks_writes_with_a_clear_error(self):
        server = Server(login_info=False)
        async with serving(server):
            store = new_store()
            await store.ensure()
            with self.assertRaisesRegex(UnoError, "did not accept the realtime login"):
                await store.write({"storage.Slots.OV1.data.0.name": "a"})
            self.assertTrue(store.ready.is_set())
            await store.close()

    async def test_disconnect_before_ack_is_reported_and_not_retried(self):
        server = Server()
        server.drop_next_update = True
        async with serving(server):
            store = new_store()
            await store.ensure()
            with self.assertRaisesRegex(UnoError, "(?i)disconnected"):
                await store.write({"storage.Slots.OV1.data.0.name": "x"})
            await store.write({"storage.Slots.OV1.data.0.name": "y"})
            self.check("reconnects and the next write succeeds", server.slots()["data"][0]["name"] == "y")
            self.check("exactly one reconnection", server.connections == 2, str(server.connections))
            await store.close()

    async def test_ack_without_broadcast_keeps_the_accepted_values(self):
        # 1.1.2: the ack completes a write, as in the official client; without a broadcast
        # within ECHO_TIMEOUT the accepted values are stored locally.
        server = Server()
        server.ignore_updates = True
        async with serving(server):
            store = new_store()
            await store.ensure()
            await store.write({"storage.Slots.OV1.data.0.name": "z"})
            self.check("no error", True)
            self.check("local copy holds the accepted value", store.slots("OV1")["data"][0]["name"] == "z")
            self.check("nothing re-read from the snapshot", server.snapshots == 1, str(server.snapshots))
            await store.close()

    async def test_engine_io_ping_is_answered_with_pong(self):
        server = Server()
        async with serving(server):
            store = new_store()
            await store.ensure()  # ready after the snapshot; the login ack may still be on its way
            self.assertTrue(await self.eventually(lambda: server.clients, 2))
            mark = len(server.received)
            await next(iter(server.clients)).send("2")
            self.assertTrue(await self.eventually(lambda: "3" in server.received[mark:], 2))
            await store.close()


class UpdateShapes(Case):
    """Update events the 1.1.1 code refused, and stale /v1 snapshots: a knob must still count every tick."""

    async def test_every_tick_counts_with_any_update_shape(self):
        for variant, lag in [
            ("normal", 0),
            ("v_string", 0),
            ("v_dict", 0),
            ("group_strkeys", 0),
            ("normal", 3),
            ("v_string", 3),
            ("group_strkeys", 3),
        ]:
            server = Server(variant=variant, lag=lag)
            async with serving(server):
                r = self.runtime(server)
                for _ in range(10):
                    await r.handle(dial("K1"))
                    await asyncio.sleep(0.15)  # a person turning a knob
                await self.idle()
                self.check(
                    f"{variant}/lag {lag}: Score 11, no alerts",
                    server.payload()["Score"] == 11 and not errors(self.sent),
                )
                await r.close()
