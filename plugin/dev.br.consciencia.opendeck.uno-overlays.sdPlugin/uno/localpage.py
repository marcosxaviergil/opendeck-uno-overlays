"""The plugin's own settings page, opened from OpenDeck: Plugins → UNO Overlays → Settings (gear).

OpenDeck has no menu API for plugins. With "HasSettingsInterface": true in the manifest it shows a
gear on the plugin and sends showSettingsInterface; the plugin shows its own GUI (OpenDeck
src-tauri/src/events/frontend/plugins.rs, events/outbound/settings.rs). The standard library has
no GUI toolkit that is always installed, so the page opens in the default browser (webbrowser)
and is served by http.server on 127.0.0.1 only, while it is in use.

Protection (the page can change where the plugin connects):
- loopback address, random port, stops after IDLE seconds without requests;
- a random token travels in the URL fragment, which browsers never send to the server, and every
  API call must repeat it in X-UNO-Token; a custom header also makes browsers preflight
  cross-site calls, and this server never answers a preflight;
- Host must be this server (DNS rebinding); Origin, when sent, too; JSON bodies up to MAX_BODY;
- strict Content-Security-Policy, no caching, no referrer; no request logging.
"""

import asyncio
import http.server
import json
import logging
import secrets
import threading
import time
import webbrowser

from uno.api import UnoError
from uno.values import integer

__all__ = ["LocalPage"]

log = logging.getLogger(__name__)

IDLE = 600  # ponytail: fixed 10-minute lifetime without requests; the gear starts it again
MAX_BODY = 65536  # the trigger and group lists; anything larger is not a settings change
SCRIPT = "text/javascript; charset=utf-8"
FILES = {  # the only paths served: no file system lookups from the URL
    "/": ("settings.html", "text/html; charset=utf-8"),
    "/js/i18n.js": ("js/i18n.js", SCRIPT),
    "/js/lang.js": ("js/lang.js", SCRIPT),
    "/js/tips.js": ("js/tips.js", SCRIPT),
    "/js/settings.js": ("js/settings.js", SCRIPT),
    "/css/styles.css": ("css/styles.css", "text/css; charset=utf-8"),
}
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class LocalPage:
    """routes: {(method, path): coroutine function}. GET handlers take no argument, POST handlers the JSON
    object sent; they raise UnoError with a message for the user."""

    def __init__(self, root, routes):
        self.root, self.routes = root, routes
        self.server = self.loop = None

    def open(self, loop):
        """Start the page if needed and show it in the default browser. Blocking: run it in a thread."""
        server = self.server
        if server is None or not server.token or not server.thread.is_alive():
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            server.page, server.timeout = self, 1
            server.token, server.host = secrets.token_urlsafe(32), f"127.0.0.1:{server.server_address[1]}"
            server.thread = threading.Thread(target=serve, args=(server,), name="uno-settings-page", daemon=True)
            self.server, self.loop = server, loop
            server.last = time.monotonic()  # before the thread reads it
            server.thread.start()
        server.last = time.monotonic()  # a page opened again starts its 10 minutes again
        return webbrowser.open(f"http://{server.host}/#{server.token}")

    def close(self):
        if self.server is not None:
            self.server.token = ""  # its thread ends within server.timeout

    def call(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(30)  # a control app test reads UNO


def serve(server):
    with server:
        while server.token and time.monotonic() - server.last < IDLE:
            server.handle_request()  # returns after server.timeout without a request
    server.token = ""


class Handler(http.server.BaseHTTPRequestHandler):
    server_version, sys_version = "UNO-Overlays", ""

    def do_GET(self):
        page = self.server.page
        if not self.trusted():
            return
        if self.path.startswith("/api/"):
            if self.authorized():
                self.answer(("GET", self.path), None)
            return
        name, kind = FILES.get(self.path, (None, None))
        if name is None:
            return self.reply(404, {"error": "Not found."})
        self.reply(200, (page.root / name).read_bytes(), kind)

    def do_POST(self):
        if not (self.trusted() and self.authorized()):
            return
        size = integer(self.headers.get("Content-Length"))
        if not self.headers.get("Content-Type", "").startswith("application/json") or not 0 < size <= MAX_BODY:
            return self.reply(400, {"error": "Send the settings as JSON."})
        try:
            data = json.loads(self.rfile.read(size))
        except ValueError:
            return self.reply(400, {"error": "Send the settings as JSON."})
        self.answer(("POST", self.path), data if isinstance(data, dict) else {})

    def answer(self, route, data):
        page = self.server.page
        handler = page.routes.get(route)
        if handler is None:
            return self.reply(404, {"error": "Not found."})
        try:
            self.reply(200, page.call(handler() if data is None else handler(data)))
        except UnoError as exc:
            self.reply(400, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - boundary: the page gets a safe message, the log the type
            log.warning("UNO settings page: %s", type(exc).__name__)
            self.reply(500, {"error": "Unable to save. Try again."})

    def trusted(self):
        server, origin = self.server, self.headers.get("Origin")
        if not server.token or self.headers.get("Host") != server.host or origin not in (None, "http://" + server.host):
            self.reply(403, {"error": "Open the settings again from OpenDeck: Plugins → UNO Overlays → Settings."})
            return False
        server.last = time.monotonic()
        return True

    def authorized(self):
        # bytes: compare_digest refuses non-ASCII str, and a header can carry anything
        if secrets.compare_digest(self.headers.get("X-UNO-Token", "").encode(), self.server.token.encode()):
            return True
        self.reply(403, {"error": "Open the settings again from OpenDeck: Plugins → UNO Overlays → Settings."})
        return False

    def reply(self, status, body, kind="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        for key, value in {**HEADERS, "Content-Type": kind, "Content-Length": str(len(data))}.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # requests are not logged
        pass
