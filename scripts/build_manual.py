"""Build dist/UNO-Overlays-<version>-Manual.pdf: one PDF with the manual in every language.

Structure: a first page with the languages, each a link to that language's contents; then, per
language, its contents (links with page numbers) and the manual. PDF bookmarks mirror the contents.

Sources (one per language, docs/manual/<code>/manual.md) use a small Markdown subset:
"# ", "## ", "### " headings, paragraphs, "- " and "1. " lists, **bold**, `code`, [text](#id) links,
![alt](name.jpg) images and two blocks generated from the plugin's own catalogs, so the manual and the
"?" help of the inspector are the same text in every language:
    {{actions}}   every action with its help and the help of each of its fields;
    {{settings}}  the fields of the settings page (Plugins → UNO Overlays → gear).
Images: docs/manual/imagens/<code>/<name> first, then docs/manual/imagens/<name>; when neither exists a
visible placeholder box with "<name>" takes its place, and the build lists every missing image. Put the
file there and build again to replace it.

Security (WeasyPrint 57.2 in Debian 12 has CVE-2025-68616, CVE-2026-49452 and CVE-2026-55073 open):
the HTML is built only from files of this repository; the fetcher allows only files under docs/manual
(no network, no redirects); the CSS is inline, not passed through write_pdf(stylesheets=…), and no
xmp_metadata or presentational hints are used, so none of the three code paths is reached.

    python3 -B scripts/build_manual.py   # needs WeasyPrint (Debian: apt install weasyprint) and Noto CJK fonts
"""

import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin" / "dev.br.consciencia.opendeck.uno-overlays.sdPlugin"
MANUAL = ROOT / "docs" / "manual"
IMAGES = MANUAL / "imagens"
sys.path.insert(0, str(PLUGIN))
from uno.i18n import LANGUAGES, catalog, set_language, tr  # noqa: E402 - the plugin's own catalogs and order

NATIVE = {"pt-BR": "Português (Brasil)", "en": "English", "es": "Español", "it": "Italiano", "de": "Deutsch",
          "ja": "日本語", "zh-CN": "简体中文", "ko": "한국어", "fr": "Français"}  # fmt: skip
PREFIX = "dev.br.consciencia.opendeck.uno-overlays."

# Fields of each action, in the inspector's order. The help is "?<action>.<field>", else "?<field>".
COMMON = ["token", "reload"]
ACTION_FIELDS = {
    "showall": [*COMMON, "tokens", "safety", "confirmSeconds"],
    "hideall": [*COMMON, "tokens", "safety", "confirmSeconds"],
    "toggle": [*COMMON, "autoClose", "pressAgain", "overlayId", "slotNumber", "slotsEnabled", "slotName", "form",
               "group", "liveEdits", "liveEditDelay", "triggers", "obsOnlyScenes", "safety", "confirmSeconds"],
    "numericfields": [*COMMON, "delay", "autoClose", "operation", "fieldComposite", "scoreOptions", "step", "min",
                      "max", "modelLimits", "pointOverlayId", "pointSeconds", "safety", "confirmSeconds"],
    "multiplier": ["multiplier", "safety", "confirmSeconds"],
    "knob": [*COMMON, "ccw", "press", "cw", "action", "overlayId", "slotNumber", "fieldComposite", "delay",
             "autoClose", "tokens"],
    "display": [*COMMON, "fieldComposite"],
    "nextslot": [*COMMON, "autoClose", "overlayId", "safety", "confirmSeconds"],
    "prevslot": [*COMMON, "autoClose", "overlayId", "safety", "confirmSeconds"],
    "slotwheel": [*COMMON, "autoClose", "overlayId", "carousel", "channel", "shiftOverlayId", "safety",
                  "confirmSeconds"],
    "reveal": [*COMMON, "fieldComposite", "shownValue", "hiddenValue", "highlight", "copyFrom", "copyTo", "safety",
               "confirmSeconds"],
    "dialvalue": [*COMMON, "fieldComposite", "channel", "shiftFieldComposite", "safety", "confirmSeconds"],
    "visor": ["channel", "safety", "confirmSeconds"],
    "timer": [*COMMON, "fieldComposite", "operation", "safety", "confirmSeconds"],
    "obsscene": [*COMMON, "sceneName", "overlayId", "autoClose", "safety", "confirmSeconds"],
    "obsrefresh": ["refreshMode", "refreshScene", "inputName", "inputNames", "safety", "confirmSeconds"],
    "macro": [*COMMON, "steps", "safety", "confirmSeconds"],
    "panic": ["token", "safety", "confirmSeconds"],
    "restore": ["token", "safety", "confirmSeconds"],
    "snapshot": [*COMMON, "name", "operation", "safe", "delete", "safety", "confirmSeconds"],
    "shift": [],
    "clock": [*COMMON, "fieldComposite", "mode", "duration", "until", "format", "operation", "value", "wrapUp",
              "yellowAt", "redAt", "overtime", "overtimeSign", "flash", "flashField", "countdownFunction",
              "countdownTarget", "countdownDelay", "pauseOffAir", "channel", "knobStep", "safety", "confirmSeconds"],
    "undo": [*COMMON, "fieldComposite", "safety", "confirmSeconds"],
    "lock": [*COMMON, "safety", "confirmSeconds"],
    "swap": [*COMMON, "pairs", "safety", "confirmSeconds"],
    "cycle": [*COMMON, "fieldComposite", "values", "resetClock", "safety", "confirmSeconds"],
    "reset": [*COMMON, "fields"],
    "datasource": [*COMMON, "definition", "def.kind", "def.text", "def.path", "def.header", "def.delimiter",
                   "def.map", "def.seconds", "def.loop", "operation", "row", "channel", "safety", "confirmSeconds"],
    "template": [*COMMON, "fieldComposite", "text", "insert", "safety", "confirmSeconds"],
    "vote": [*COMMON, "definition", "def.options", "def.total", "def.format", "option", "safety", "confirmSeconds"],
    "goal": [*COMMON, "definition", "def.title", "def.goal", "def.start", "def.end", "def.titleField", "def.current",
             "def.goalField", "def.goalFormat", "def.percent", "def.percentFormat", "def.reachedFunction",
             "def.reachedTarget", "def.reachedDelay", "operation", "amount", "safety", "confirmSeconds"],
    "status": ["connections", "test", "apiCap", "log", "backup", "safety", "confirmSeconds"],
    "lockdesk": ["lockAfter"],
}  # fmt: skip
SETTINGS_FIELDS = ["language", "obs", "host", "port", "password", "liveEditDelay", "apps", "addToken", "triggers",
                   "groups", "newGroup"]  # fmt: skip
# The label of each field as the inspector shows it (a catalog text), by field, or by action and field.
LABELS = {
    "token": "API Token", "reload": "Connect / Reload", "tokens": "More control apps (optional)",
    "safety": "Safety (optional)", "confirmSeconds": "Confirm with a second press", "autoClose": "Auto Close",
    "pressAgain": "Press again while Auto Close counts", "overlayId": "Overlay", "slotNumber": "Server Slot",
    "slotsEnabled": "Mode", "slotName": "Server Slot Name", "form": "Overlay content",
    "group": "Exclusive group (optional)", "liveEdits": "Edits while on air (optional)",
    "liveEditDelay": "Wait after the last change (ms, empty = settings page)", "triggers": "Triggers and chains",
    "obsOnlyScenes": "Key shows only while OBS program scene is (comma-separated, optional)", "delay": "Delay",
    "operation": "Operation", "fieldComposite": "Numeric Field", "scoreOptions": "Score options (optional)",
    "step": "Fixed step (e.g. 2 or 3; empty = global multiplier)", "min": "Minimum", "max": "Maximum",
    "modelLimits": "Overlay model min/max", "pointOverlayId": "After a point, show overlay", "pointSeconds": "for",
    "multiplier": "Multiplier", "ccw": "Counterclockwise", "press": "Press", "cw": "Clockwise", "action": "Action",
    "carousel": "Turning", "channel": "Visor channel", "shiftOverlayId": "While Shift is held (optional)",
    "shiftFieldComposite": "While Shift is held (optional)", "shownValue": "Value when revealed",
    "hiddenValue": "Value when hidden", "highlight": "Highlight the correct answer (optional)",
    "copyFrom": "Field with the correct answer", "copyTo": "Field that receives it while revealed",
    "sceneName": "OBS scene", "refreshMode": "Refresh", "refreshScene": "Scene", "inputName": "Browser source",
    "inputNames": "More browser sources", "steps": "Steps (in order; Wait delays the rest)", "name": "Scene name",
    "safe": "Recall safe: overlays left unchanged (Ctrl+click)", "delete": "Delete stored scene",
    "mode": "Appearance", "duration": "Duration (hh:mm:ss)", "until": "Finish time (HH:MM or HH:MM:SS)",
    "format": "Format", "value": "Value for Set / Change (hh:mm:ss) or Adjust (± seconds)",
    "wrapUp": "Wrap-up and end (optional)", "yellowAt": "Yellow at (time left, e.g. 1:00)",
    "redAt": "Red at (time left, e.g. 0:30)", "overtime": "At 0:00", "overtimeSign": "Overtime shows",
    "flash": "Flash at 0:00", "flashField": "Flash in the overlay too", "countdownFunction": "When it completes",
    "countdownTarget": "Overlay", "countdownDelay": "Delay (ms, max 30000)",
    "pauseOffAir": "While the overlay is off air", "knobStep": "Knob step (seconds per tick)", "pairs": "Pairs",
    "values": "Values, one per line", "resetClock": "Also stop and reset the clock of (optional)",
    "fields": "Fields to reset (Ctrl+click)", "def.kind": "Type",
    "def.text": "Rows", "def.path": "File path on this computer", "def.header": "Use first row as column names",
    "def.delimiter": "Separator", "def.map": "Mapping", "def.seconds": "Auto Next: seconds between rows",
    "def.loop": "Loop", "row": "Row for Select row (1 = first)",
    "text": "Text: {Overlay::Field} is replaced by the field value",
    "insert": "Insert a field into the text", "def.options": "Options", "def.total": "Total votes field (optional)",
    "def.format": "Percent format", "option": "Votes for option", "def.title": "Title", "def.goal": "Goal Amount",
    "def.start": "Starting Amount", "def.end": "End After", "def.titleField": "Title field",
    "def.current": "Current amount field (numbers)", "def.goalField": "Goal amount field",
    "def.goalFormat": "Goal format", "def.percent": "Percent field", "def.percentFormat": "Percent format",
    "def.reachedFunction": "When the goal is reached", "def.reachedTarget": "Overlay",
    "def.reachedDelay": "Delay (ms, max 30000)", "amount": "Amount (knob: per tick)", "connections": "Connections",
    "test": "Test connection", "apiCap": "Daily App API cap (uno free plan: 10000; yellow from 90%, 0 = no warning)",
    "log": "Log (newest first, no tokens)", "backup": "Backup of shared settings",
    "lockAfter": "Lock after N seconds without use (0 = off; Companion Pin Timeout)",
    ("reveal", "fieldComposite"): "Field that shows the answer",
    ("timer", "fieldComposite"): "Timer Field", ("clock", "fieldComposite"): "Text field",
    ("undo", "fieldComposite"): "Only this field (optional)", ("cycle", "fieldComposite"): "Field",
    ("template", "fieldComposite"): "Field that receives the text", ("clock", "operation"): "Press",
    ("snapshot", "operation"): "Press to", ("datasource", "operation"): "Press", ("goal", "operation"): "Press",
    ("clock", "channel"): "Visor channel (knob)", ("datasource", "channel"): "Visor channel (knob)",
    ("visor", "channel"): "Channel",
    ("settings", "language"): "Language", ("settings", "obs"): "Connect to OBS", ("settings", "host"): "Host",
    ("settings", "port"): "Port", ("settings", "password"): "Password",
    ("settings", "liveEditDelay"): "Wait after the last change (ms, 0 to 10000; 0 = send while typing)",
    ("settings", "apps"): "Control apps", ("settings", "addToken"): "Add a control app: API token",
    ("settings", "triggers"): "Triggers", ("settings", "groups"): "Exclusive groups",
    ("settings", "newGroup"): "New group name",
}  # fmt: skip
DEFINITION_NAMES = {"datasource": "Data source", "vote": "Poll", "goal": "Goal"}


class Catalog:
    """The plugin's texts in one language (uno.i18n), plus where the manual finds each label and help."""

    def __init__(self, code):
        self.code = code

    def t(self, text, **values):
        set_language(self.code)  # languages are rendered one after the other
        return tr(text, **values)

    def help(self, action, field):
        for key in (f"?{action}.{field}", f"?{field}") if field else (f"?{action}",):
            if key in catalog("en"):
                return self.t(key)
        return ""

    def label(self, action, field):
        if field == "definition":
            return self.t("{name} (shared by every key)", name=self.t(DEFINITION_NAMES[action]))
        return self.t(LABELS.get((action, field)) or LABELS.get(field) or field)


# ── a small Markdown subset ──


def inline(text, code):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\((https://[\w./-]+)\)", r'<a href="\2">\1</a>', text)
    return re.sub(r"\[([^\]]+)\]\(#([\w.-]+)\)", lambda m: f'<a href="#{code}-{m[2]}">{m[1]}</a>', text)


def slug(text):
    return re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-")[:60] or "s"


class Page:
    def __init__(self, code, catalog):
        self.code, self.catalog, self.missing, self.toc, self.ids = code, catalog, [], [], set()

    def anchor(self, text, wanted=None):
        base = f"{self.code}-{wanted or slug(text)}"
        anchor, n = base, 1
        while anchor in self.ids:
            n += 1
            anchor = f"{base}-{n}"
        self.ids.add(anchor)
        return anchor

    def heading(self, level, text, wanted=None, raw=False):
        anchor = self.anchor(text, wanted)
        body = text if raw else inline(text, self.code)
        self.toc.append((level, body, anchor))
        return f'<h{level} id="{anchor}">{body}</h{level}>'

    def image(self, alt, name):
        if not re.fullmatch(r"[\w.-]+\.(jpg|jpeg|png)", name):
            raise SystemExit(f"manual: unsupported image name {name!r} ({self.code})")
        caption = f"<figcaption>{html.escape(alt)}</figcaption></figure>"
        for path in (IMAGES / self.code / name, IMAGES / name):
            if path.is_file():
                return f'<figure><img src="{path.as_uri()}" alt="{html.escape(alt)}">{caption}'
        self.missing.append(name)
        box = f'<div class="placeholder" role="img" aria-label="{html.escape(alt)}">&lt;{html.escape(name)}&gt;</div>'
        return f"<figure>{box}{caption}"

    def render(self, source):
        out, items, kind = [], [], None

        def close():
            nonlocal items, kind
            if items:
                tag = "ol" if kind == "1" else "ul"
                out.append(f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>")
            items, kind = [], None

        paragraph = []

        def flush():
            if paragraph:
                out.append("<p>" + inline(" ".join(paragraph), self.code) + "</p>")
                paragraph.clear()

        for line in source.splitlines():
            stripped = line.strip()
            heading = re.match(r"(#{1,3}) (.+?)(?: \{#([\w-]+)\})?$", stripped)
            bullet = re.match(r"(-|\d+\.) (.+)$", stripped)
            image = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if not stripped or heading or image or stripped in ("{{actions}}", "{{settings}}"):
                flush()
                close()
            if not stripped:
                continue
            if heading:
                out.append(self.heading(len(heading[1]) + 1, heading[2], heading[3]))  # "#" in a source is h2
            elif image:
                out.append(self.image(image[1], image[2]))
            elif stripped == "{{actions}}":
                out.append(self.actions())
            elif stripped == "{{settings}}":
                out.append(self.fields("settings", SETTINGS_FIELDS))
            elif bullet:
                flush()
                new = "1" if bullet[1] != "-" else "-"
                if kind not in (None, new):
                    close()
                kind = new
                items.append(inline(bullet[2], self.code))
            elif items:
                items[-1] += " " + inline(stripped, self.code)
            else:
                paragraph.append(stripped)
        flush()
        close()
        return "\n".join(out)

    def fields(self, action, fields):
        rows = []
        for field in fields:
            text = self.catalog.help(action, field)
            if not text:
                raise SystemExit(f"manual: no help text for {action}.{field}")
            label = html.escape(self.catalog.label(action, field))
            rows.append(f"<dt>{label}</dt><dd>{html.escape(text)}</dd>")
        return '<dl class="fields">' + "".join(rows) + "</dl>" if rows else ""

    def actions(self):
        manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
        parts = []
        for action in manifest["Actions"]:
            kind = action["UUID"].removeprefix(PREFIX)
            name = self.catalog.t(action["Name"])
            parts.append(self.heading(4, html.escape(name), f"action-{kind}", raw=True))
            parts.append(f"<p>{html.escape(self.catalog.help(kind, ''))}</p>")
            parts.append(self.fields(kind, ACTION_FIELDS[kind]))
        return "\n".join(parts)


def document(version):
    """(HTML, {language: [missing images]})."""
    sections, missing, index = [], {}, []
    for code in LANGUAGES:
        source = (MANUAL / code / "manual.md").read_text(encoding="utf-8")
        title, contents, *body = source.splitlines()  # "% Title of the manual", "% Contents", the manual
        title, contents = title.removeprefix("% ").strip(), contents.removeprefix("% ").strip()
        page = Page(code, Catalog(code))
        body = page.render("\n".join(body))
        toc = "".join(
            f'<li class="level{level}"><a href="#{anchor}">{text}</a></li>' for level, text, anchor in page.toc
        )
        sections.append(
            f'<section class="language" lang="{code}">'
            f'<h1 id="{code}">{html.escape(title)}</h1>'
            f'<nav class="toc" id="{code}-toc"><h2 class="toc-title">{html.escape(contents)}</h2><ul>{toc}</ul></nav>'
            f"{body}</section>"
        )
        index.append(f'<li><a href="#{code}-toc">{NATIVE[code]}</a></li>')
        missing[code] = page.missing
    set_language("en")  # Catalog switched the plugin's language while rendering; leave its default
    cover = (
        f'<section class="cover"><p class="product">UNO Overlays {html.escape(version)}</p>'
        f'<p class="kind">Manual</p><ul class="languages">{"".join(index)}</ul></section>'
    )
    css = (MANUAL / "manual.css").read_text(encoding="utf-8")
    page_html = (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>UNO Overlays {html.escape(version)}'
        f"</title><style>{css}</style></head><body>{cover}{''.join(sections)}</body></html>"
    )
    return page_html, missing


def fetcher(url):
    """Only image files under docs/manual: no network, no other file (see the module docstring)."""
    from weasyprint import default_url_fetcher

    allowed = MANUAL.resolve().as_uri() + "/"
    if not url.startswith(allowed) or ".." in url:
        raise ValueError(f"manual: refused to load {url}")
    return default_url_fetcher(url)


def render(version):
    from weasyprint import HTML

    page_html, missing = document(version)
    return HTML(string=page_html, base_url=str(MANUAL), url_fetcher=fetcher).render(), missing


def check_fonts():
    """Japanese, Chinese and Korean need Noto CJK: without it they would print as empty boxes."""
    try:
        found = subprocess.run(["fc-list", ":lang=ja", "family"], capture_output=True, text=True, check=False).stdout  # noqa: S603, S607
    except OSError:
        sys.exit("manual: fontconfig (fc-list) is missing. Debian: sudo apt install fontconfig")
    if not found.strip():
        sys.exit("manual: no CJK font. Debian: sudo apt install fonts-noto-cjk")


def main():
    check_fonts()
    manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["Version"]
    try:
        doc, missing = render(version)
    except ImportError:
        sys.exit("manual: WeasyPrint is missing. Debian: sudo apt install weasyprint fonts-noto-cjk fonts-dejavu-core")
    out = ROOT / "dist" / f"UNO-Overlays-{version}-Manual.pdf"
    out.parent.mkdir(exist_ok=True)
    doc.write_pdf(out)
    for code, names in missing.items():
        if names:
            print(f"manual: {code}: placeholder for {', '.join(sorted(set(names)))}")
    print(f"{out.relative_to(ROOT)}  {len(doc.pages)} pages")


if __name__ == "__main__":
    main()
