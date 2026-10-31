#!/usr/bin/env python3
"""OpenDeck Linux entrypoint. No package installation required at runtime."""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "vendor"))
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from uno import PLUGIN_ID, VERSION
from uno.runtime import Runtime

log = logging.getLogger(__name__)


async def run(args):
    async with connect(
        f"ws://127.0.0.1:{args.port}",
        proxy=None,
        compression=None,
        open_timeout=10,
        close_timeout=2,
        max_size=4_000_000,
    ) as ws:
        lock = asyncio.Lock()

        async def send(event):
            async with lock:
                await ws.send(json.dumps(event, ensure_ascii=False, allow_nan=False))

        await send({"event": args.registerEvent, "uuid": args.pluginUUID})
        await send({"event": "getGlobalSettings", "context": args.pluginUUID})
        runtime = Runtime(send, args.pluginUUID, info=registration_info(args.info))
        current = asyncio.current_task()
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_running_loop().add_signal_handler(sig, current.cancel)
        try:
            async for raw in ws:
                try:
                    await runtime.handle(json.loads(raw))
                except (ValueError, TypeError, AttributeError):
                    log.warning("Ignored malformed OpenDeck message")
        finally:
            await runtime.close()


def registration_info(raw):
    """OpenDeck's -info JSON (plugins/info_param.rs); {} when it is not an object, so the plugin still starts."""
    try:
        info = json.loads(raw)
    except ValueError:
        log.warning("Ignored malformed OpenDeck -info argument")
        return {}
    return info if isinstance(info, dict) else {}


def main():
    parser = argparse.ArgumentParser(description="UNO Overlays for OpenDeck")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("-port", required=True, type=int)
    parser.add_argument("-pluginUUID", required=True)
    parser.add_argument("-registerEvent", required=True, choices=["registerPlugin"])
    parser.add_argument("-info", default="{}")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.pluginUUID != PLUGIN_ID + ".sdPlugin":
        parser.error("Unexpected OpenDeck launch arguments")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run(args))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except (OSError, ConnectionClosed):
        log.error("OpenDeck connection closed. Restart OpenDeck to reconnect.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
