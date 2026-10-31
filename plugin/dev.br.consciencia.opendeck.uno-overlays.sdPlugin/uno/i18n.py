"""Languages: the plugin speaks the language chosen on its settings page, else OpenDeck's.

Catalogs are i18n/<code>.json in gettext style: the English text is the key, so English needs no
catalog and a missing translation falls back to English instead of showing a key. Keys that are not
English text (help texts, action names) start with "?" or "@" and live in en.json too.

OpenDeck 2.14 (src-tauri/src/store/mod.rs) keeps its language in settings.json, in the folder that
also holds plugins/ (shared::config_dir), and starts each plugin with that plugin's folder as the
working directory (plugins/mod.rs). Its registration info carries the language too, but only for
en, es, zh_CN, fr, de, ja and ko: every other one, pt_BR included, arrives as "en"
(plugins/info_param.rs). So settings.json is read first and the registration value is the fallback.
"""

import json
import os
import pathlib

__all__ = ["LANGUAGES", "opendeck_language", "resolve", "set_language", "tr"]

LANGUAGES = ("pt-BR", "en", "es", "it", "de", "ja", "zh-CN", "ko", "fr")
# OpenDeck's language list (SettingsView.svelte) mapped to ours; sv and uk are not among ours: English.
OPENDECK = {"pt_BR": "pt-BR", "zh_CN": "zh-CN", "en": "en", "es": "es", "fr": "fr", "de": "de", "ja": "ja", "ko": "ko"}
CATALOGS = pathlib.Path(__file__).resolve().parents[1] / "i18n"
MAX_SETTINGS = 1_000_000  # OpenDeck's settings.json is a few hundred bytes; never read a huge file

_cache = {}
_current = {"code": "en", "catalog": {}}


def catalog(code):
    """The translations of one language (cached); English and unknown codes have none."""
    if code not in _cache:
        path = CATALOGS / f"{code}.json"
        try:
            _cache[code] = json.loads(path.read_text(encoding="utf-8")) if code in LANGUAGES else {}
        except (OSError, ValueError):
            _cache[code] = {}
    return _cache[code]


def set_language(code):
    code = code if code in LANGUAGES else "en"
    _current.update(code=code, catalog=catalog(code))
    return code


def tr(text, **values):
    """Text in the current language; {name} placeholders are filled after translating."""
    text = _current["catalog"].get(text) or (catalog("en").get(text) if text[:1] in "?@" else None) or text
    return text.format(**values) if values else text


def plugin_folder():
    """The plugin folder as OpenDeck sees it: launch.sh exports it before symbolic links are resolved."""
    return pathlib.Path(os.environ.get("UNO_PLUGIN_DIR") or os.getcwd())


def opendeck_language(folder=None):
    """Our code for OpenDeck's language, from <OpenDeck config>/settings.json; None when unreadable."""
    path = (folder or plugin_folder()).parent.parent / "settings.json"
    try:
        if path.stat().st_size > MAX_SETTINGS:
            return None
        value = json.loads(path.read_text(encoding="utf-8")).get("language")
    except (OSError, ValueError, AttributeError):
        return None
    return OPENDECK.get(value, "en") if isinstance(value, str) and value else None


def resolve(choice, info_language="", folder=None):
    """Settings page choice, else OpenDeck's settings.json, else its registration info, else English."""
    if choice in LANGUAGES:
        return choice
    return opendeck_language(folder) or OPENDECK.get(info_language or "", "en")
