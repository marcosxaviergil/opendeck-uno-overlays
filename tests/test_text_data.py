"""Text and data: Auto Close press-again option, data sources, text template, poll, goal (loopback)."""

import asyncio
import os
import tempfile
import time

from support import TOKEN, Case, Server, appear, last_image, press, serving, settings_changed, state


def name(server):
    return server.payload("OV2")["Name"]


class AutoCloseOption(Case):
    async def test_press_again_adds_time_only_when_chosen(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            extend = {**TOKEN, "overlayId": "OV1", "autoClose": "3", "pressAgain": "add"}
            await r.handle(appear("K1", "toggle", extend))
            await self.settle()
            await r.handle(press("K1", "toggle", extend))
            await self.settle()
            await asyncio.sleep(0.5)
            before = r.timers[("TESTTOKEN", "OV1")][2]
            await r.handle(press("K1", "toggle", extend))
            await self.settle()
            added = r.timers[("TESTTOKEN", "OV1")][2] - before
            self.check(
                "option on: pressing again adds the Auto Close time",
                state(server, "OV1") == "In" and abs(added - 3) < 0.2,
                f"{added:.2f}",
            )
            plain = {**extend, "pressAgain": ""}
            await r.handle(settings_changed("K1", "toggle", plain))
            await r.handle(press("K1", "toggle", plain))
            await self.settle()
            self.check(
                "default unchanged: pressing again hides",
                state(server, "OV1") == "Out1" and ("TESTTOKEN", "OV1") not in r.timers,
            )
            await r.close()


class DataSources(Case):
    async def test_typed_list_next_previous_select_and_loop(self):
        server = Server(show=True)
        async with serving(server):
            r, glob = self.runtime(server), {}
            ticker = {**TOKEN, "kind": "list", "text": "A\nB\n\nC\n", "map": [{"field": "OV2::Name"}]}
            await self.set_global(glob, dataSources={"Ticker": ticker})
            key, seen = {"source": "Ticker"}, []
            for operation, row in (("next", ""), ("next", ""), ("prev", ""), ("select", "3"), ("next", "")):
                await r.handle(press("D1", "datasource", {**key, "operation": operation, "row": row}))
                await self.settle()
                seen.append(name(server))
            self.check(
                "Next / Previous / Select row; blank lines skipped; the last row stays without Loop",
                seen == ["A", "B", "A", "C", "C"],
                str(seen),
            )
            ticker["loop"] = "true"
            await self.set_global(glob)
            await r.handle(press("D1", "datasource", {**key, "operation": "next"}))
            await self.settle()
            self.check("Loop: after the last row, back to the first", name(server) == "A", name(server))
            ticker["text"] = "Z\nB\nC"
            await self.set_global(glob)
            self.check(
                "an edited list updates the selected row (vMix: sources update automatically)",
                await self.eventually(lambda: name(server) == "Z", 4),
                name(server),
            )
            await r.close()

    async def test_csv_mapping_format_template_and_file_watch(self):
        server = Server(show=True)
        folder = tempfile.mkdtemp()
        path = os.path.join(folder, "people.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Name;Cargo\nMaria;CEO\nJoão;CTO\n")
        async with serving(server):
            r, glob = self.runtime(server), {}
            people = {
                **TOKEN,
                "kind": "csv",
                "path": path,
                "header": "true",
                "delimiter": ";",
                "map": [
                    {"field": "OV2::Name", "format": "Nome: {0}"},
                    {"field": "OV2::Role"},
                    {"field": "OV1::Title", "format": "{Name} – {Cargo}"},
                    {"field": "OV1::Period", "column": "Name", "row": "1"},
                ],
            }
            await self.set_global(glob, dataSources={"People": people})
            await r.handle(press("D2", "datasource", {"source": "People", "operation": "select", "row": "2"}))
            await self.settle()
            ov1, ov2 = server.payload(), server.payload("OV2")
            self.check(
                "Format 'Nome: {0}' on the column named like the field", ov2["Name"] == "Nome: João", ov2["Name"]
            )
            self.check("Auto maps by the field title (Cargo)", ov2["Role"] == "CTO", ov2["Role"])
            self.check("template of columns", ov1["Title"] == "João – CTO", ov1["Title"])
            self.check("fixed row", ov1["Period"] == "Maria", ov1["Period"])
            self.backend.log.clear()
            await asyncio.sleep(1.1)  # a new modification time
            with open(path, "w", encoding="utf-8") as f:
                f.write("Name;Cargo\nMaria;CEO\nJoão;Diretor\n")
            await self.eventually(lambda: server.payload("OV2")["Role"] == "Diretor", 4)
            await self.settle()
            writes = [c for c in self.backend.log if c[0] == "SetOverlayContent"]
            self.check(
                "a saved file rewrites only the changed fields",
                server.payload("OV2")["Role"] == "Diretor"
                and server.payload()["Title"] == "João – Diretor"
                and all("Name" not in c[2] for c in writes),
                str(writes),
            )
            await r.close()

    async def test_auto_next_and_knob_with_visor(self):
        server = Server(show=True)
        async with serving(server):
            r, sent, glob = self.runtime(server), self.sent, {}
            auto_source = {**TOKEN, "kind": "list", "text": "1\n2\n3", "seconds": "1", "map": [{"field": "OV2::Name"}]}
            ticker = {**TOKEN, "kind": "list", "text": "A\nB\nC", "map": [{"field": "OV2::Name"}]}
            await self.set_global(glob, dataSources={"Auto": auto_source, "Ticker": ticker})
            auto = {"source": "Auto", "operation": "autonext"}
            await r.handle(appear("A1", "datasource", auto))
            await r.handle(press("A1", "datasource", auto))
            await asyncio.sleep(0.4)
            first, red = name(server), 'fill="#FF0000"' in last_image(sent, "A1")
            await asyncio.sleep(2.3)
            await self.settle()
            self.check(
                "Auto Next: the first row now, one row per second, stops at the last; key red while on",
                first == "1"
                and name(server) == "3"
                and red
                and r.sources["Auto"]["auto"] is None
                and 'fill="#FFFFFF" d=' in last_image(sent, "A1"),
                f"{first} {name(server)} {red}",
            )
            wheel = {"source": "Ticker", "channel": "5"}
            await r.handle(appear("DK", "datasource", wheel, "Encoder"))
            await r.handle(appear("V5", "visor", {"channel": "5"}))
            await r.handle(press("DK", "datasource", wheel, "dialRotate", ticks=1))
            await asyncio.sleep(0.3)
            preview = last_image(sent, "V5")
            await r.handle(press("DK", "datasource", wheel, "dialDown"))
            await self.settle()
            self.check(
                "knob: turning shows the next row on the Visor, pressing selects it",
                ">2 B<" in preview and name(server) == "B",
                f"{preview[-80:]} {name(server)}",
            )
            await r.close()


class TemplatePollGoal(Case):
    async def test_text_template(self):
        server = Server(show=True)
        async with serving(server):
            r = self.runtime(server)
            template = {
                **TOKEN,
                "fieldComposite": "OV1::Title",
                "text": "{OV1::TeamA} {OV1::Score} x {OV1::ScoreB} {OV1::TeamB} {x}",
            }
            await r.handle(press("T1", "template", template))
            await self.settle()
            self.check(
                "fields replaced, unknown tokens kept",
                server.payload()["Title"] == "Home 1 x 0 Away {x}",
                server.payload()["Title"],
            )
            await r.close()

    async def test_poll_votes_total_percentages_and_undo(self):
        server = Server(show=True)
        async with serving(server):
            r, glob = self.runtime(server), {}
            poll = {
                **TOKEN,
                "format": "{0}%",
                "total": "OV1::Total",
                "options": [
                    {"votes": "OV1::VotesA", "percent": "OV1::PctA"},
                    {"votes": "OV1::VotesB", "percent": "OV1::PctB"},
                ],
            }
            await self.set_global(glob, polls={"Enquete": poll})
            for option in ("1", "1", "2"):
                await r.handle(press("P" + option, "vote", {"poll": "Enquete", "option": option}))
                await self.settle(0.2)
            await self.settle()
            p = server.payload()
            self.check(
                "votes, total and percentages (half up)",
                (p["VotesA"], p["VotesB"], p["Total"], p["PctA"], p["PctB"]) == (2, 1, 3, "67%", "33%"),
                str((p["VotesA"], p["VotesB"], p["Total"], p["PctA"], p["PctB"])),
            )
            await r.handle(press("U1", "undo", TOKEN))
            await self.settle()
            p = server.payload()
            self.check(
                "undo a vote: the percentages follow",
                (p["VotesB"], p["Total"], p["PctA"], p["PctB"]) == (0, 2, "100%", "0%"),
                str(p),
            )
            await r.close()

    async def test_goal_like_streamlabs_tip_goal(self):
        server = Server(show=True)
        async with serving(server):
            r, sent, glob = self.runtime(server), self.sent, {}
            future = time.strftime("%Y-%m-%dT%H:%M", time.localtime(time.time() + 86400))
            goal = {
                **TOKEN,
                "title": "Meta do dia",
                "goal": "100",
                "start": "10",
                "end": future,
                "titleField": "OV1::GoalTitle",
                "current": "OV1::Raised",
                "goalField": "OV1::GoalAmount",
                "goalFormat": "R$ {0}",
                "percent": "OV1::GoalPct",
                "percentFormat": "{0}%",
                "reachedFunction": "show",
                "reachedTarget": "OV2",
            }
            await self.set_global(glob, goals={"Meta": goal})
            start = {"goal": "Meta", "operation": "start"}
            add = {"goal": "Meta", "operation": "add", "amount": "50"}
            await r.handle(appear("G1", "goal", start))
            await r.handle(press("G1", "goal", start))
            await self.settle()
            p = server.payload()
            self.check(
                "start: title, goal, starting amount and percent; key red while active",
                (p["GoalTitle"], p["GoalAmount"], p["Raised"], p["GoalPct"]) == ("Meta do dia", "R$ 100", 10, "10%")
                and 'fill="#FF0000"' in last_image(sent, "G1"),
                str((p["GoalTitle"], p["GoalAmount"], p["Raised"], p["GoalPct"])),
            )
            for _ in range(2):
                await r.handle(press("G2", "goal", add))
                await self.settle(0.3)
            await self.eventually(lambda: state(server, "OV2") == "In", 3)
            await self.settle()
            live = r.global_settings["goals"]["Meta"]
            self.check(
                "amounts add up; reaching the goal shows the chosen overlay",
                server.payload()["Raised"] == 110
                and server.payload()["GoalPct"] == "110%"
                and state(server, "OV2") == "In"
                and live.get("reached"),
                f"{server.payload()['Raised']} {state(server, 'OV2')}",
            )
            stale = {**live, "state": "", "reached": False, "percentFormat": "{0} %"}
            await self.set_global(glob, goals={"Meta": stale})  # an inspector saving an old copy of the goal
            live = r.global_settings["goals"]["Meta"]
            self.check(
                "an inspector edit never undoes start/reached, but its own change is kept",
                live.get("reached") is True and live.get("state") == "active" and live.get("percentFormat") == "{0} %",
            )
            await r.handle(press("G3", "goal", {"goal": "Meta", "operation": "end"}))
            await self.settle()
            mark = len(sent)
            await r.handle(press("G2", "goal", add))
            await self.settle()
            self.check(
                "an ended goal refuses amounts with an alert; key white",
                server.payload()["Raised"] == 110
                and any(e.get("event") == "showAlert" and e.get("context") == "G2" for e in sent[mark:])
                and 'fill="#FFFFFF" d=' in last_image(sent, "G1"),
            )
            past = time.strftime("%Y-%m-%dT%H:%M", time.localtime(time.time() - 120))
            glob["goals"] = r.global_settings["goals"]
            glob["goals"]["Meta"].update(end=past)
            await self.set_global(glob)
            await r.handle(press("G1", "goal", start))
            await self.settle()
            mark = len(sent)
            await r.handle(press("G2", "goal", {**add, "amount": "5"}))
            await self.settle()
            self.check(
                "after End After, adding is refused",
                server.payload()["Raised"] == 10
                and any(e.get("event") == "showAlert" and e.get("context") == "G2" for e in sent[mark:]),
                str(server.payload()["Raised"]),
            )
            await r.close()
