"""Global queue: one UNO operation at a time, ticks merged, order kept per overlay (loopback)."""

import asyncio
import time

from support import TOKEN, Case, Server, dial, disappear, errors, press, serving, settings_changed

SCORE_KEY = {**TOKEN, "overlayId": "OV1", "fieldId": "Score", "operation": "increment"}
FOULS_KEY = {**TOKEN, "overlayId": "OV1", "fieldId": "Fouls", "operation": "decrement"}


class GlobalQueue(Case):
    async def test_burst_from_five_controls_on_two_devices(self):
        server = Server(limits={"maxRequestsPerSec": 3, "maxBytesPerMin": 500_000})
        async with serving(server):
            r = self.runtime(server)
            events = []
            for _ in range(20):
                events += [dial("devA-K1"), dial("devA-K2"), dial("devB-K1", field="Fouls")]
                events.append(press("devB-B1", "numericfields", SCORE_KEY))
                events.append(press("devA-B2", "numericfields", FOULS_KEY))
            for e in events:  # five controls turned/pressed together, ~100 commands in ~2 s
                await r.handle(e)
                await asyncio.sleep(0.02)
            await self.idle()
            sets = self.backend.names().count("SetOverlayContent")
            times = server.update_times
            worst = max((sum(1 for t in times if s <= t < s + 1.0) for s in times), default=0)
            p = server.payload()
            self.check("totals exact", p["Score"] == 61 and p["Fouls"] == 0, f"{p['Score']} {p['Fouls']}")
            self.check("ticks merged: far fewer writes than commands", sets < len(events) / 4, str(sets))
            self.check("datastore limit of 3 writes/s respected", worst <= 3, str(worst))
            self.check("no errors", not errors(self.sent))
            await r.close()

    async def test_order_is_kept_across_a_toggle_of_the_same_overlay(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            self.backend.latency = 0.2
            toggle = press("T1", "toggle", {**TOKEN, "overlayId": "OV1"})
            for e in (dial("K1"), dial("K1"), toggle, dial("K1"), dial("K1")):
                await r.handle(e)
            await self.idle()
            names = [n for n in self.backend.names() if n in ("SetOverlayContent", "ShowOverlay", "HideOverlay")]
            self.check(
                "set, toggle, set: no merge across the toggle",
                names[-1] == "SetOverlayContent" and "ShowOverlay" in names and names.index("ShowOverlay") > 0,
                str(names),
            )
            self.check("all four ticks applied", server.payload()["Score"] == 5)
            await r.close()

    async def test_ticks_during_a_delay_merge_into_one_update(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            for _ in range(6):
                await r.handle(dial("K1", cwDelay="1"))
                await asyncio.sleep(0.1)
            await asyncio.sleep(1.5)
            await self.idle()
            names = self.backend.names()
            self.check(
                "one show, one update, total 6",
                names.count("ShowOverlay") == 1
                and names.count("SetOverlayContent") == 1
                and server.payload()["Score"] == 7,
                f"{names} {server.payload()['Score']}",
            )
            await r.close()

    async def test_reconfiguring_a_control_drops_only_its_queued_ticks(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            self.backend.latency = 0.5
            await r.handle(dial("K1", field="Fouls"))  # starts running
            await asyncio.sleep(0.05)
            for _ in range(3):
                await r.handle(dial("K2"))  # queued
            changed = {**dial("K2")["payload"]["settings"], "cwDelay": "2"}
            await r.handle(settings_changed("K2", "knob", changed))
            t0 = time.monotonic()
            await self.idle()
            self.check(
                "queued ticks of the reconfigured control dropped; the running job finished",
                server.payload()["Score"] == 1 and server.payload()["Fouls"] == 1,
                f"{server.payload()} {time.monotonic() - t0:.1f}s",
            )
            await r.close()

    async def test_a_control_that_disappears_keeps_its_queued_ticks(self):
        server = Server()
        async with serving(server):
            r = self.runtime(server)
            self.backend.latency = 0.5
            await r.handle(dial("K1", field="Fouls"))
            await asyncio.sleep(0.05)
            for _ in range(3):
                await r.handle(dial("K2"))
            # A profile switch: OpenDeck cannot tell it from a deleted key (events/frontend/profiles.rs).
            await r.handle(disappear("K2", "knob", dial("K2")["payload"]["settings"], "Encoder"))
            await self.idle()
            self.check("turns already made are applied", server.payload()["Score"] == 4, str(server.payload()))
            await r.close()
