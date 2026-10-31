"""Languages (item 8 of 2.0.0): catalogs, OpenDeck's language, the order of choice, translated messages."""

import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from support import PLUGIN, ROOT, Case, Server, serving
from uno.api import token_value
from uno.i18n import resolve, set_language, tr


class Catalogs(unittest.TestCase):
    def test_every_message_shown_to_the_user_passes_through_tr(self):
        """UnoError texts reach keys, the inspector and the settings page: an English literal is never translated."""
        untranslated = []
        for path in sorted((PLUGIN / "uno").rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                literal = ast.Constant | ast.JoinedStr | ast.Dict | ast.Subscript | ast.BinOp
                if getattr(getattr(node, "func", None), "id", "") == "UnoError" and isinstance(node.args[0], literal):
                    untranslated.append(f"{path.relative_to(PLUGIN)}:{node.lineno}")
        self.assertEqual(untranslated, [], "wrap these messages in tr()")

    def test_every_text_is_translated_and_the_generated_files_are_current(self):
        result = subprocess.run(  # noqa: S603 - the project's own script
            [sys.executable, "-B", "scripts/build_i18n.py", "--check"], cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])

    def test_opendeck_gets_the_action_names_in_its_languages(self):
        manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
        for name in ("pt_BR", "es", "de", "fr", "ja", "zh_CN", "ko"):  # OpenDeck's names (SettingsView.svelte)
            with self.subTest(name):
                data = json.loads((PLUGIN / f"{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(data["Name"], "UNO Overlays")
                for action in manifest["Actions"]:
                    self.assertTrue(data[action["UUID"]]["Name"] and data[action["UUID"]]["Tooltip"])
        self.assertEqual(json.loads((PLUGIN / "pt_BR.json").read_text())[manifest["Actions"][0]["UUID"]]["Name"],
                         "Mostrar todos")  # fmt: skip


class Resolution(unittest.TestCase):
    def setUp(self):
        self.addCleanup(set_language, "en")
        self.config = pathlib.Path(tempfile.mkdtemp())
        self.folder = self.config / "plugins" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
        self.folder.mkdir(parents=True)

    def opendeck(self, language):
        (self.config / "settings.json").write_text(json.dumps({"version": "2.14.0", "language": language}))

    def test_settings_page_choice_then_opendeck_settings_then_registration_then_english(self):
        self.opendeck("pt_BR")
        self.assertEqual(resolve("it", "en", self.folder), "it", "the choice on the settings page wins")
        self.assertEqual(resolve("", "en", self.folder), "pt-BR", "OpenDeck sends pt_BR as en: settings.json decides")
        self.opendeck("zh_CN")
        self.assertEqual(resolve(None, "en", self.folder), "zh-CN")
        self.opendeck("sv")
        self.assertEqual(resolve("", "es", self.folder), "en", "a language the plugin does not have is English")
        (self.config / "settings.json").unlink()
        self.assertEqual(resolve("", "de", self.folder), "de", "without settings.json, the registration value")
        self.assertEqual(resolve("", "", self.folder), "en")

    def test_messages_are_translated_and_keep_their_values(self):
        set_language("pt-BR")
        self.assertEqual(tr("Channel {n}", n=3), "Canal 3")
        with self.assertRaises(Exception) as caught:
            token_value("https://app.overlays.uno/output/x")
        self.assertEqual(str(caught.exception), "Coloque o token de controle da API, não a URL de saída.")
        set_language("ja")
        self.assertIn("UNO", tr("UNO HTTP {code}. Check the token or try again later.", code=429))
        self.assertEqual(set_language("xx"), "en", "an unknown code speaks English")


class InspectorLanguage(Case):
    async def test_the_inspector_asks_and_gets_opendecks_language(self):
        config = pathlib.Path(tempfile.mkdtemp())
        folder = config / "plugins" / "x.sdPlugin"
        folder.mkdir(parents=True)
        (config / "settings.json").write_text(json.dumps({"language": "pt_BR"}))
        server = Server(show=True)
        with mock.patch.dict(os.environ, {"UNO_PLUGIN_DIR": str(folder)}):
            async with serving(server):
                r = self.runtime(server)
                await self.set_global({})
                reply = await self.request({"type": "i18n.get"}, ctx="K1", action="toggle")
                self.check("pt_BR in OpenDeck → pt-BR", reply.get("data") == {"language": "pt-BR"}, str(reply))
                (config / "settings.json").write_text(json.dumps({"language": "ko"}))
                reply = await self.request({"type": "i18n.get"}, ctx="K1", action="toggle")
                self.check("read again when an inspector opens", reply.get("data") == {"language": "ko"}, str(reply))
                await self.set_global({}, language="fr")
                reply = await self.request({"type": "i18n.get"}, ctx="K1", action="toggle")
                self.check("the settings page choice wins", reply.get("data") == {"language": "fr"}, str(reply))
                await r.close()
        set_language("en")
