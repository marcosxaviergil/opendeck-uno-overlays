"""Clock (vMix countdown functions, stagetimer looks) and scoreboard tools (loopback)."""

import asyncio
import time

from support import BASE, TOKEN, Case, Server, appear, disappear, last_image, press, serving, state

TIME = ("TESTTOKEN", "OV1", "Time")
PERIOD = ("TESTTOKEN", "OV1", "Period")
COUNTDOWN = {
    **TOKEN,
    "fieldComposite": "OV1::Time",
    "mode": "countdown",
    "duration": "00:00:03",
    "yellowAt": "2",
    "redAt": "1",
    "countdownFunction": "hide",
    "flash": "1",
    "operation": "pause",
}


def color(sent, ctx):
    img = last_image(sent, ctx)
    for name, code in (("green", "#22C55D"), ("yellow", "#F59E0C"), ("red", "#EF4444"), ("white", "#FFFFFF")):
        if f'fill="{code}" d=' in img:
            return name
    return img[-120:]


def seconds(text):
    minutes, secs = text.split(":")
    return int(minutes) * 60 + int(secs)


class Clocks(Case):
    async def test_countdown_wrap_up_completion_and_stop(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await self.show("OV1")
            await r.handle(appear("C1", "clock", COUNTDOWN))
            await r.handle(press("C1", "clock", COUNTDOWN))
            seen, colors = set(), []
            for _ in range(24):
                await asyncio.sleep(0.2)
                seen.add(server.payload()["Time"])
                colors.append(color(sent, "C1"))
            self.check(
                "writes the field each second (M:SS) and runs into overtime",
                {"0:03", "0:02", "0:01", "0:00", "-0:01"} <= seen,
                str(sorted(seen)),
            )
            self.check(
                "wrap-up colors green → yellow → red",
                "green" in colors
                and "yellow" in colors
                and colors.index("yellow") > colors.index("green")
                and "red" in colors[colors.index("yellow") :],
                str(colors),
            )
            self.check("OnCountdownCompleted: Hide the clock's overlay", state(server, "OV1") == "Out1")
            clock = r.clocks[TIME]
            self.check("flash once at 0:00 on the key", clock.flash_until > clock.flash_start > 0)
            await r.handle(press("C1", "clock", {**COUNTDOWN, "operation": "stop"}))
            await self.eventually(lambda: server.payload()["Time"] == "0:03", 2)
            self.check(
                "StopCountdown: stop and reset shows the duration",
                server.payload()["Time"] == "0:03" and not clock.running,
            )
            await r.close()

    async def test_knob_adjusts_and_sets_the_countdown(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            knob = {
                **TOKEN,
                "fieldComposite": "OV1::Time",
                "mode": "countdown",
                "duration": "00:05:00",
                "knobStep": "10",
                "channel": "4",
                "operation": "pause",
            }
            await r.handle(appear("CK", "clock", knob, "Encoder"))
            await r.handle(appear("V4", "visor", {"channel": "4"}))
            await r.handle(press("CK", "clock", knob, "dialRotate", ticks=2))
            await self.eventually(lambda: server.payload()["Time"] == "5:20", 2)
            self.check(
                "turning = AdjustCountdown (+2 × 10 s), shown on the Visor",
                server.payload()["Time"] == "5:20" and "5:20" in last_image(sent, "V4"),
                server.payload()["Time"],
            )
            await r.handle(press("CK", "clock", {**knob, "operation": "set", "value": "00:10:00"}, "dialDown"))
            await r.handle(press("CK", "clock", {**knob, "operation": "stop"}, "dialDown"))
            await self.eventually(lambda: server.payload()["Time"] == "10:00", 2)
            self.check("SetCountdown, then Stop: the new duration", server.payload()["Time"] == "10:00")
            await r.close()

    async def test_count_up_stops_at_its_duration(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            up = {
                **TOKEN,
                "fieldComposite": "OV1::Period",
                "mode": "countup",
                "duration": "2",
                "overtime": "stop",
                "operation": "start",
            }
            await r.handle(appear("C2", "clock", up))
            await r.handle(press("C2", "clock", up))
            await asyncio.sleep(3.0)
            self.check(
                "count up stops at its duration",
                server.payload()["Period"] == "0:02" and not r.clocks[PERIOD].running,
                server.payload()["Period"],
            )
            await r.close()

    async def test_time_of_day_runs_without_a_press_and_across_pages(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            tod = {**TOKEN, "fieldComposite": "OV1::Title", "mode": "timeofday", "format": "hh:mm:ss"}
            await r.handle(appear("C3", "clock", tod))
            await asyncio.sleep(0.8)
            now = (time.strftime("%H:%M:%S"), time.strftime("%H:%M:%S", time.localtime(time.time() - 1)))
            self.check("time of day written without pressing", server.payload()["Title"] in now)
            await r.handle(disappear("C3", "clock", tod))
            await r.handle(appear("C3", "clock", tod))  # page back: keeps running, no restart
            await r.handle(press("C3", "clock", tod))  # PauseCountdown: stop writing
            await asyncio.sleep(0.3)
            frozen = server.payload()["Title"]
            await asyncio.sleep(1.5)
            self.check(
                "runs across page changes; a press pauses it",
                server.payload()["Title"] == frozen and not r.clocks[("TESTTOKEN", "OV1", "Title")].running,
            )
            await r.close()

    async def test_until_finish_time_fixes_the_duration_at_start(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            target = time.strftime("%H:%M", time.localtime(time.time() + 180))
            until = {**TOKEN, "fieldComposite": "OV2::Name", "mode": "until", "until": target, "operation": "start"}
            await r.handle(appear("C4", "clock", until))
            await r.handle(press("C4", "clock", until))
            await asyncio.sleep(0.8)
            left = server.payload("OV2")["Name"]
            self.check("counts down to the time of day", 120 <= seconds(left) <= 180, left)
            await r.handle(press("C4", "clock", {**until, "operation": "suspend"}))
            await asyncio.sleep(2.6)
            self.check(
                "stagetimer: the duration is fixed at start, so it can pause",
                abs(seconds(server.payload("OV2")["Name"]) - seconds(left)) <= 1,
                server.payload("OV2")["Name"],
            )
            await r.close()

    async def test_pause_while_off_air(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            toggle = {**TOKEN, "overlayId": "OV1"}
            await r.handle(appear("K1", "toggle", toggle))
            await r.handle(press("K1", "toggle", toggle))  # on air
            await self.settle()
            follow = {
                **TOKEN,
                "fieldComposite": "OV1::Period",
                "mode": "countdown",
                "duration": "01:00",
                "pauseOffAir": "true",
                "operation": "start",
            }
            await r.handle(press("C5", "clock", follow))
            await asyncio.sleep(0.5)
            await r.handle(press("K1", "toggle", toggle))  # off air
            paused = await self.eventually(lambda: not r.clocks[PERIOD].running, 3)
            await r.handle(press("K1", "toggle", toggle))  # on air
            resumed = await self.eventually(lambda: r.clocks[PERIOD].running, 3)
            self.check("pauses off air and resumes on air", paused and resumed)
            await r.close()


class Scoreboard(Case):
    async def test_step_limits_undo_lock_and_point_graphic(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            score = {**TOKEN, "overlayId": "OV1", "fieldId": "Score", "fieldComposite": "OV1::Score", "step": "3"}
            await r.handle(appear("S1", "numericfields", score))
            await self.settle()
            await r.handle(press("S1", "numericfields", score))
            await self.settle()
            self.check("fixed step +3", server.payload()["Score"] == 4, str(server.payload()["Score"]))
            await r.handle(press("S1", "numericfields", {**score, "max": "5"}))
            await self.settle()
            alerts = [e for e in sent if e.get("event") == "showAlert" and e.get("context") == "S1"]
            self.check("max 5 clamps, with an alert on the key", server.payload()["Score"] == 5 and alerts)
            await r.handle(press("S1", "numericfields", {**score, "step": "20", "modelLimits": "true"}))
            await self.settle()
            self.check("model max (10) applied like the official client", server.payload()["Score"] == 10)
            await r.handle(press("U1", "undo", TOKEN))
            await self.settle()
            self.check("Undo restores the previous value", server.payload()["Score"] == 5)
            await r.handle(press("L1", "lock", TOKEN))
            mark = len(sent)
            await r.handle(press("S1", "numericfields", score))
            await self.settle()
            locked_alert = any(e.get("event") == "showAlert" and e.get("context") == "S1" for e in sent[mark:])
            self.check(
                "Lock blocks score changes; lock key red",
                server.payload()["Score"] == 5 and locked_alert and 'fill="#FF0000"' in last_image(sent, "L1"),
            )
            await r.handle(press("L1", "lock", TOKEN))
            point = {**score, "step": "1", "pointOverlayId": "OV2", "pointSeconds": "1"}
            self.backend.log.clear()
            await r.handle(press("S1", "numericfields", point))
            shown = await self.eventually(lambda: ("ShowOverlay", "OV2") in self.backend.calls(), 2)
            hidden = await self.eventually(lambda: ("HideOverlay", "OV2") in self.backend.calls(), 3)
            self.check(
                "a point shows the graphic for N seconds",
                shown and hidden and server.payload()["Score"] == 6,
                str(self.backend.calls()),
            )
            await r.close()

    async def test_swap_sides_and_undo(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            await server.mutate({BASE.format("OV1") + ".Score": 6})
            swap = {**TOKEN, "pairs": [{"a": "OV1::TeamA", "b": "OV1::TeamB"}, {"a": "OV1::Score", "b": "OV1::ScoreB"}]}
            await r.handle(press("W1", "swap", swap))
            await self.settle()
            p = server.payload()
            self.check(
                "swap every pair at once",
                (p["TeamA"], p["TeamB"], p["Score"], p["ScoreB"]) == ("Away", "Home", 0, 6),
                str(p),
            )
            await r.handle(press("U1", "undo", TOKEN))
            await self.settle()
            p = server.payload()
            self.check("one Undo reverts the whole swap", p["TeamA"] == "Home" and p["ScoreB"] == 0 and p["Score"] == 6)
            await r.close()

    async def test_cycle_steps_through_values_and_resets_a_clock(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            periods = {
                **TOKEN,
                "fieldComposite": "OV1::Period",
                "values": "1º tempo\n2º tempo\nProrrogação",
                "resetClock": "OV1::Time",
            }
            clock = {**COUNTDOWN, "duration": "00:10:00", "operation": "start", "countdownFunction": ""}
            await r.handle(press("C1", "clock", clock))
            await asyncio.sleep(1.3)
            await r.handle(press("P1", "cycle", periods))
            await self.settle()
            first = server.payload()["Period"]
            await r.handle(press("P1", "cycle", periods))
            await self.settle()
            self.check(
                "next value of the list; the clock stops and resets",
                first == "1º tempo"
                and server.payload()["Period"] == "2º tempo"
                and server.payload()["Time"] == "10:00"
                and not r.clocks[TIME].running,
                f"{first} {server.payload()['Period']} {server.payload()['Time']}",
            )
            await r.close()

    async def test_reset_needs_a_two_second_hold(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            await server.mutate({BASE.format("OV1") + ".Fouls": 4, BASE.format("OV1") + ".Score": 6})
            reset = {**TOKEN, "fields": ["OV1::Score", "OV1::TeamA", "OV1::Fouls"]}
            await r.handle(appear("R1", "reset", reset))
            await r.handle(press("R1", "reset", reset, "keyDown"))
            await asyncio.sleep(0.5)
            await r.handle(press("R1", "reset", reset, "keyUp"))
            await self.settle()
            early = server.payload()["TeamA"] == "Home" and server.payload()["Score"] == 6
            await r.handle(press("R1", "reset", reset, "keyDown"))
            await asyncio.sleep(1.0)
            held_red = 'fill="#FF0000" d=' in last_image(sent, "R1")
            await asyncio.sleep(1.3)
            await r.handle(press("R1", "reset", reset, "keyUp"))
            await self.settle()
            p = server.payload()
            self.check("releasing early does nothing", early)
            self.check("red while held", held_red)
            self.check(
                "holding 2 s resets: model resetValue, else 0 or empty",
                p["Score"] == 0 and p["TeamA"] == "" and p["Fouls"] == 0,
                str(p),
            )
            await r.close()
