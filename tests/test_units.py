"""Pure rules, no I/O except temporary files: protocol ports, values, Clock, data sources, files, backup."""

import asyncio
import json
import os
import stat
import tempfile
import unittest
from decimal import Decimal

from support import UnoError  # first: puts the plugin on sys.path
from uno import PLUGIN_ID
from uno.api import token_value
from uno.automations import app_id
from uno.backup import export, restore
from uno.clock import Clock
from uno.datastore import decode
from uno.files import check_path, read_file, write_private
from uno.jsonpath import set_path
from uno.obs import auth, check_address
from uno.runtime.datasources import row_after
from uno.runtime.overlays import timecontrol
from uno.sources import column_of, table
from uno.timeouts import within
from uno.values import format_clock, increment, parse_hms, percent, render, typed


class ProtocolPorts(unittest.TestCase):
    def test_socket_io_decode_string(self):
        # socket.io-parser decodeString: type, namespace, ack id, JSON data.
        self.assertEqual(decode('20["login","ds","tok"]'), (2, "/", 0, ["login", "ds", "tok"]))
        self.assertEqual(decode("312[true]"), (3, "/", 12, [True]))
        self.assertEqual(decode('2/ns,5["e",1]'), (2, "/ns", 5, ["e", 1]))

    def test_update_json_object(self):
        # singular-datastore updateJsonObject: falsy intermediates become {}, an index at the end appends.
        data = {"a": 0, "l": [1]}
        set_path(data, "a.b", 1)
        set_path(data, "l.1", 2)
        self.assertEqual(data, {"a": {"b": 1}, "l": [1, 2]})

    def test_timecontrol_play_and_pause(self):
        # processPayloadCommand for timecontrol: play, then pause adds the elapsed milliseconds.
        running = timecontrol({}, "play", 1000)
        self.assertEqual(running, {"UTC": 1000, "isRunning": True, "value": 0})
        self.assertEqual(timecontrol(running, "pause", 3500), {"UTC": 3500, "isRunning": False, "value": 2500})
        self.assertIsNone(timecontrol(running, "play", 2000))

    def test_obs_websocket_auth(self):
        # base64(sha256(base64(sha256(password + salt)) + challenge)), computed independently here.
        import base64
        import hashlib

        secret = base64.b64encode(hashlib.sha256(b"p" + b"s").digest())
        expected = base64.b64encode(hashlib.sha256(secret + b"c").digest()).decode()
        self.assertEqual(auth("p", "s", "c"), expected)

    def test_obs_address_is_validated_before_it_reaches_a_url(self):
        check_address("127.0.0.1", 4455)
        check_address("obs-pc.local", 1)
        for host, port in (("a/b", 4455), ("h@x", 4455), ("", 4455), ("127.0.0.1", 0), ("127.0.0.1", 65536)):
            with self.subTest(host=host, port=port), self.assertRaises(UnoError):
                check_address(host, port)

    def test_token_is_validated_before_it_reaches_a_url(self):
        self.assertEqual(token_value("  abc_DEF-123 "), "abc_DEF-123")
        for bad in ("", "a/b", "https://app.overlays.uno/output/x", "a" * 257, "a b"):
            with self.subTest(bad), self.assertRaises(UnoError):
                token_value(bad)

    def test_app_id_names_a_control_app_without_the_token(self):
        self.assertEqual(len(app_id("TESTTOKEN")), 6)
        self.assertNotIn("TESTTOKEN", app_id("TESTTOKEN"))
        self.assertNotEqual(app_id("A"), app_id("B"))


class Values(unittest.TestCase):
    def test_increment_keeps_the_json_type(self):
        self.assertEqual(increment(1, 2), 3)
        self.assertEqual(increment("1,5", 1), "2.5")
        self.assertEqual(increment(1.5, Decimal("0.5")), 2)
        self.assertEqual(increment("abc", 1), "1")

    def test_typed_macro_values(self):
        self.assertIs(typed("yes", False), True)
        self.assertEqual(typed("7", 0), 7)
        self.assertEqual(typed("7.5", 0), 7.5)
        self.assertEqual(typed("x", 0), "x")

    def test_format_and_percent(self):
        # vMix Format 'Name: {0}'; unknown tokens stay; whole percent, half up.
        self.assertEqual(render("Name: {0} {x}", {"0": "Gary"}.get), "Name: Gary {x}")
        self.assertEqual(percent(2, 3), 67)
        self.assertEqual(percent(1, 8), 13)
        self.assertEqual(percent(1, 0), 0)

    def test_clock_text(self):
        # vMix hh:mm:ss values; stagetimer formats (minutes not capped) and overtime prefix.
        self.assertEqual(parse_hms("01:02:05"), 3725)
        self.assertEqual(parse_hms("62:05"), 3725)
        self.assertEqual(parse_hms("x"), 0)
        self.assertEqual(format_clock(3725), "62:05")
        self.assertEqual(format_clock(3725, "hh:mm:ss"), "1:02:05")
        self.assertEqual(format_clock(92, "sss"), "92")
        self.assertEqual(format_clock(-1, "mm:ss", "+"), "+0:01")


class ClockRules(unittest.TestCase):
    def test_pause_countdown_toggles_and_restarts_when_complete(self):
        clock = Clock({"duration": "00:00:10"})
        clock.apply("pause", None, 0)
        self.assertTrue(clock.running)
        clock.apply("pause", None, 4)
        self.assertEqual(clock.text(4), "0:06")
        clock.apply("pause", None, 5)
        self.assertTrue(clock.complete(11))
        self.assertFalse(clock.complete(12))  # OnCountdownCompleted fires once
        clock.apply("pause", None, 12)  # complete: start from the beginning
        self.assertEqual(clock.text(12), "0:10")

    def test_adjust_change_and_overtime_stop(self):
        clock = Clock({"duration": "60", "overtime": "stop"})
        clock.apply("adjust", "15", 0)
        self.assertEqual(clock.text(0), "1:15")
        clock.apply("change", "00:00:05", 0)
        clock.apply("start", None, 0)
        self.assertTrue(clock.complete(6))
        self.assertEqual(clock.text(9), "0:00")
        self.assertFalse(clock.running)

    def test_wrap_up_colors_and_flash(self):
        clock = Clock({"duration": "10", "yellowAt": "5", "redAt": "2", "flash": "2"})
        clock.apply("start", None, 0)
        self.assertEqual([clock.color(t) for t in (1, 6, 9)], ["#22C55D", "#F59E0C", "#EF4444"])
        clock.complete(10)
        self.assertEqual([clock.hidden(t) for t in (10.2, 10.7, 11.7, 12.7)], [False, True, True, False])

    def test_count_up_and_pause_off_air(self):
        clock = Clock({"mode": "countup"})
        clock.apply("start", None, 0)
        clock.follow_air(False, 3)
        self.assertFalse(clock.running)
        clock.follow_air(True, 10)
        self.assertEqual(clock.text(12), "0:05")


class DataSourceRules(unittest.TestCase):
    def test_vmix_mapping_auto_column(self):
        # Auto = the column named like the field (id or title), else the field's index.
        self.assertEqual(column_of(["Name", "Cargo"], "", ["Role", "Cargo"], 0), 1)
        self.assertEqual(column_of(["1"], "", ["Name"], 0), 0)
        self.assertIsNone(column_of(["Name"], "Missing", ["Name"], 0))

    def test_rows_next_previous_and_loop(self):
        self.assertEqual(row_after(None, "next", "", 3, False), 0)
        self.assertEqual(row_after(2, "next", "", 3, False), 2)
        self.assertEqual(row_after(2, "next", "", 3, True), 0)
        self.assertEqual(row_after(0, "prev", "", 3, True), 0)
        self.assertEqual(row_after(0, "select", "3", 3, False), 2)
        with self.assertRaises(UnoError):
            row_after(0, "select", "4", 3, False)

    def test_list_and_csv_tables(self):
        self.assertEqual(table({"text": "A\n\n B \n"}), (["1"], [["A"], ["B"]]))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "people.csv")
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write("Name;Cargo\nMaria;CEO\n;\nJoão\n")
            names, rows = table({"kind": "csv", "path": path, "header": "true", "delimiter": ";"})
            self.assertEqual(names, ["Name", "Cargo"])
            self.assertEqual(rows, [["Maria", "CEO"], ["João", ""]])


class Files(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.dir = self.folder.name

    def test_paths_must_be_absolute_with_the_expected_extension(self):
        with self.assertRaisesRegex(UnoError, "full path"):
            check_path("people.csv", (".csv",))
        with self.assertRaisesRegex(UnoError, ".csv"):
            check_path("/etc/passwd", (".csv",))
        self.assertTrue(check_path("~/x.csv", (".csv",)).startswith(os.path.expanduser("~")))

    def test_read_refuses_what_is_not_a_small_utf8_file(self):
        folder = os.path.join(self.dir, "rows.txt")
        os.mkdir(folder)
        with self.assertRaisesRegex(UnoError, "not a regular file"):
            read_file(folder, (".txt",))
        big = os.path.join(self.dir, "big.txt")
        with open(big, "w") as f:
            f.write("x" * 11)
        with self.assertRaisesRegex(UnoError, "larger"):
            read_file(big, (".txt",), limit=10)
        latin = os.path.join(self.dir, "latin.txt")
        with open(latin, "wb") as f:
            f.write("João".encode("latin-1"))
        with self.assertRaisesRegex(UnoError, "UTF-8"):
            read_file(latin, (".txt",))

    def test_backup_file_is_private_and_never_replaces_other_files(self):
        path = os.path.join(self.dir, "backup.json")
        write_private(path, {"plugin": PLUGIN_ID})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        write_private(path, {"plugin": PLUGIN_ID, "again": True})  # an earlier backup may be replaced
        other = os.path.join(self.dir, "other.json")
        with open(other, "w") as f:
            json.dump({"mine": 1}, f)
        with self.assertRaisesRegex(UnoError, "not a UNO Overlays backup"):
            write_private(other, {"plugin": PLUGIN_ID})
        link = os.path.join(self.dir, "link.json")
        os.symlink(path, link)
        with self.assertRaisesRegex(UnoError, "not a UNO Overlays backup"):
            write_private(link, {"plugin": PLUGIN_ID})


class Backup(unittest.TestCase):
    def test_global_automations_go_in_the_backup_and_tokens_only_with_secrets(self):
        settings = {
            "triggers": [{"event": "obsIn", "scene": "Cam", "function": "show", "app": "abc123", "overlay": "OV1"}],
            "groups": {"LT": {"delay": 0, "members": []}},
            "language": "pt-BR",
            "controlApps": {"abc123": {"token": "SECRETTOKEN", "name": "Placar"}},
        }
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "b.json")
            export(settings, path, secrets=False)
            with open(path) as f:
                plain = json.load(f)
            self.assertEqual((plain["triggers"], plain["groups"], plain["language"]), (settings["triggers"],
                             settings["groups"], "pt-BR"))  # fmt: skip
            self.assertNotIn("SECRETTOKEN", json.dumps(plain), "tokens of control apps only with secrets")
            export(settings, path, secrets=True)
            here = {"controlApps": {"def456": {"token": "OTHER", "name": ""}}}
            result, _ = restore(here, path)
            self.assertEqual(set(result["controlApps"]), {"abc123", "def456"}, "apps of this computer stay")

    SETTINGS = {
        "scenes": {"Abertura": {"token": "T1", "overlays": {}}},
        "goals": {"Meta": {"token": "T1", "goal": "10", "state": "active", "reached": True, "started": "x"}},
        "obsPassword": "secret",
        "apiCalls": {"date": "2026-09-29", "counts": {"a": 1}},
    }

    def test_round_trip_without_and_with_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "b.json")
            _, count = export(self.SETTINGS, path, secrets=False)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(count, 2)
            self.assertNotIn("obsPassword", data)
            self.assertNotIn("apiCalls", data)
            self.assertEqual(data["goals"]["Meta"], {"goal": "10"})
            with self.assertRaisesRegex(UnoError, "API token"):
                restore({}, path)
            result, _ = restore({"goals": {"Other": {}}}, path, token="T2")
            self.assertEqual(result["goals"]["Meta"], {"goal": "10", "token": "T2"})
            self.assertIn("Other", result["goals"])
            export(self.SETTINGS, path, secrets=True)
            result, _ = restore({}, path)
            self.assertEqual(result["obsPassword"], "secret")
            self.assertEqual(result["scenes"]["Abertura"]["token"], "T1")


if __name__ == "__main__":
    unittest.main()


class Timeouts(unittest.IsolatedAsyncioTestCase):
    async def test_a_cancel_is_never_lost_when_the_result_arrives_at_the_same_time(self):
        # CPython gh-86296: on 3.10 and 3.11, asyncio.wait_for returns the result instead of raising
        # CancelledError when both happen in the same loop turn; a reader then never stops.
        inner = asyncio.get_running_loop().create_future()
        outer = asyncio.ensure_future(within(inner, 10))
        await asyncio.sleep(0)
        inner.set_result("packet")
        outer.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await outer

    async def test_timeout_cancels_the_inner_wait(self):
        inner = asyncio.ensure_future(asyncio.sleep(10))
        with self.assertRaises(asyncio.TimeoutError):
            await within(inner, 0.05)
        self.assertTrue(inner.cancelled())
        self.assertEqual(await within(asyncio.sleep(0, "ok"), 1), "ok")
