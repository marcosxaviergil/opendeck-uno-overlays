"""UNO App API v2. Command bodies follow the user's working API client.

Only the fixed UNO host is used. Errors deliberately omit URLs and response
bodies, since the control token is a credential embedded in the path.
"""

import asyncio
import json
import re
import urllib.error
import urllib.request

from uno import VERSION
from uno.i18n import tr

__all__ = ["NoRedirect", "UnoAPI", "UnoError", "token_value"]


class UnoError(Exception):
    """An error safe to show in the inspector and OpenDeck logs."""


def token_value(value):
    token = str(value or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", token):
        raise UnoError(tr("Enter the control API token, not the output URL."))
    return token


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class UnoAPI:
    def __init__(self, token):
        self.token = token_value(token)

    def _request(self, command):
        request = urllib.request.Request(
            f"https://app.overlays.uno/apiv2/controlapps/{self.token}/api",
            data=json.dumps(command, ensure_ascii=False, allow_nan=False).encode(),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"OpenDeck-UNO-Overlays/{VERSION}",
            },
            method="PUT",
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise UnoError(tr("UNO returned an oversized response."))
            data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise UnoError(tr("UNO HTTP {code}. Check the token or try again later.", code=exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise UnoError(tr("UNO connection failed or timed out. Check Internet access.")) from None
        except (ValueError, UnicodeError):
            raise UnoError(tr("UNO returned invalid JSON.")) from None
        if not isinstance(data, dict):
            raise UnoError(tr("UNO returned an invalid response."))
        if data.get("status", 200) != 200:
            raise UnoError(tr("UNO rejected the command. Check the overlay and API token."))
        return data.get("payload")

    def _metadata(self):
        request = urllib.request.Request(
            f"https://app.overlays.uno/apiv2/controlapps/{self.token}",
            headers={
                "Accept": "application/json",
                "User-Agent": f"OpenDeck-UNO-Overlays/{VERSION}",
            },
            method="GET",
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise UnoError(tr("UNO returned an oversized response."))
            data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise UnoError(tr("UNO HTTP {code}. Check the token or try again later.", code=exc.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise UnoError(tr("UNO connection failed or timed out. Check Internet access.")) from None
        except (ValueError, UnicodeError):
            raise UnoError(tr("UNO returned invalid JSON.")) from None
        if not isinstance(data, dict):
            raise UnoError(tr("UNO returned an invalid response."))
        return data

    async def metadata(self):
        task = asyncio.create_task(asyncio.to_thread(self._metadata))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def call(self, command, **values):
        # Do not retry writes. A timeout may occur after the server applied them.
        task = asyncio.create_task(asyncio.to_thread(self._request, {"command": command, **values}))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # Finish the in-flight request before releasing a transaction lock.
            await asyncio.gather(task, return_exceptions=True)
            raise