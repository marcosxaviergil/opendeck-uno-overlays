"""Keys and knobs: icons, tally, Auto Close badge, slots, Slot Wheel + Visor, Dial Value, Timer (loopback)."""

import asyncio

from support import RED, TOKEN, WHITE, Case, Server, appear, last_image, press, serving


class Keys(Case):
    async def test_tally_badge_and_auto_close(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            tog = {**TOKEN, "overlayId": "OV1", "autoClose": "3"}
            await r.handle(appear("T1", "toggle", tog))
            await self.settle()
            img = last_image(sent, "T1")
            self.check(
                "icon: Material Symbols glyph, white off air", "<path" in img and WHITE in img and RED not in img
            )
            await r.handle(press("T1", "toggle", tog))
            await asyncio.sleep(0.8)  # idle() would wait for the Auto Close ticker
            img = last_image(sent, "T1")
            self.check("tally: bright red on air (from the datastore state)", 'fill="#FF0000"' in img)
            self.check(
                "badge: iOS-style red oval with the seconds left",
                'rx="22" fill="#FF4245"' in img and (">3<" in img or ">2<" in img),
            )
            await asyncio.sleep(3.5)
            await self.settle()
            img = last_image(sent, "T1")
            self.check(
                "Auto Close hid it: white, badge gone",
                'fill="#FFFFFF" d=' in img and "FF4245" not in img and self.backend.names().count("HideOverlay") == 1,
            )
            await r.close()

    async def test_next_and_previous_slot(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            key = {**TOKEN, "overlayId": "OV1"}
            await r.handle(appear("N1", "nextslot", key))
            await self.settle()
            self.backend.log.clear()
            await r.handle(press("N1", "nextslot", key))
            await self.settle()
            self.check(
                "Next slot: Take next, then Show",
                self.backend.names() == ["TakeOverlayNextSlot", "ShowOverlay"]
                and server.slots()["currentSlotId"] == "s2",
                str(self.backend.log),
            )
            await r.handle(press("N1", "prevslot", key))
            await self.settle()
            self.check("Previous slot: back to s1", server.slots()["currentSlotId"] == "s1")
            await r.close()

    async def test_slot_wheel_and_visor(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            wheel = {**TOKEN, "overlayId": "OV1", "channel": "1"}
            await r.handle(appear("W1", "slotwheel", wheel, "Encoder"))
            await r.handle(appear("V1", "visor", {"channel": "1"}))
            await self.settle()
            self.check("Visor shows the cued slot, starting at the current one", ">One<" in last_image(sent, "V1"))
            await r.handle(press("W1", "slotwheel", wheel, "dialRotate", ticks=1))
            await self.settle(0.3)
            self.check("turning shows the next slot name", "Profa. Ana" in last_image(sent, "V1"))
            await r.handle(press("W1", "slotwheel", wheel, "dialRotate", ticks=2))
            await self.settle(0.3)
            self.check("the wheel wraps around", ">One<" in last_image(sent, "V1"))
            await r.handle(press("W1", "slotwheel", wheel, "dialRotate", ticks=-1))
            self.backend.log.clear()
            await r.handle(press("W1", "slotwheel", wheel, "dialDown"))
            await r.handle(press("W1", "slotwheel", wheel, "dialUp"))
            await self.settle()
            self.check(
                "click: Take the cued slot (3), then Show",
                any(c[:3] == ("TakeOverlaySlotNumber", "OV1", {"value": 3}) for c in self.backend.log)
                and "ShowOverlay" in self.backend.names(),
                str(self.backend.log),
            )
            self.check("Visor red: the cued slot is on air", 'fill="#FF0000"' in last_image(sent, "V1"))
            self.check("no setImage to the screenless knob", last_image(sent, "W1") == "")
            await r.close()

    async def test_dial_value_edit_mode(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            dial = {**TOKEN, "fieldComposite": "OV1::Score", "channel": "2"}
            await r.handle(appear("D1", "dialvalue", dial, "Encoder"))
            await r.handle(appear("V2", "visor", {"channel": "2"}))
            await self.settle(0.3)
            self.backend.log.clear()
            await r.handle(press("D1", "dialvalue", dial, "dialRotate", ticks=5))
            await self.settle(0.3)
            self.check(
                "turning outside edit mode changes nothing",
                not self.backend.log and ">1<" in last_image(sent, "V2"),
            )
            for e in ("dialDown", "dialUp"):
                await r.handle(press("D1", "dialvalue", dial, e))
            await r.handle(press("D1", "dialvalue", dial, "dialRotate", ticks=3))
            await self.settle(0.3)
            self.check(
                "click = edit mode; turning shows the pending value on the Visor",
                "→ 4" in last_image(sent, "V2") and not self.backend.log,
            )
            await r.handle(press("V2", "visor", {"channel": "2"}))  # Visor press = knob click
            await self.settle()
            sets = [c for c in self.backend.log if c[0] == "SetOverlayContent"]
            self.check(
                "second click sends one value",
                len(sets) == 1 and sets[0][2] == {"Score": 4} and server.payload()["Score"] == 4,
                str(sets),
            )
            self.backend.log.clear()
            for e in ("dialDown", "dialUp"):
                await r.handle(press("D1", "dialvalue", dial, e))
            await r.handle(press("D1", "dialvalue", dial, "dialRotate", ticks=9))
            await r.handle(press("D1", "dialvalue", dial, "dialDown"))
            await asyncio.sleep(2.2)
            await r.handle(press("D1", "dialvalue", dial, "dialUp"))
            await self.settle()
            self.check(
                "holding 2 s cancels; nothing sent",
                not [c for c in self.backend.log if c[0] == "SetOverlayContent"] and ">4<" in last_image(sent, "V2"),
            )
            await r.close()

    async def test_timer_on_a_timecontrol_field(self):
        server = Server(show=True)
        async with serving(server):
            r, sent = self.runtime(server), self.sent
            timer = {**TOKEN, "fieldComposite": "OV1::Clock", "operation": "toggle"}
            await r.handle(appear("C1", "timer", timer))
            await r.handle(press("C1", "timer", timer))
            await self.settle()
            clock = server.payload()["Clock"]
            self.check(
                "play writes {UTC, isRunning, value}; key red",
                clock["isRunning"] is True and 'fill="#FF0000"' in last_image(sent, "C1"),
            )
            await asyncio.sleep(1.1)
            await r.handle(press("C1", "timer", timer))
            await self.settle()
            clock = server.payload()["Clock"]
            self.check(
                "pause accumulates the elapsed ms; key white",
                clock["isRunning"] is False
                and 1000 <= clock["value"] < 3000
                and 'fill="#FFFFFF" d=' in last_image(sent, "C1"),
                str(clock),
            )
            await r.close()
