"""asyncio.wait_for without the race that loses a cancellation on Python 3.10 and 3.11.

There, when the awaited result and a cancel arrive in the same loop turn, wait_for returns the result
and the cancel is gone (CPython gh-86296, fixed in 3.12 by gh-96764). A datastore reader cancelled
while a packet arrives would then keep reading forever and the plugin would never close.
asyncio.wait never swallows the caller's cancellation, so this is built on it.
"""

import asyncio

__all__ = ["within"]


async def within(awaitable, seconds):
    """The result of `awaitable`, or asyncio.TimeoutError after `seconds` (the inner wait is cancelled)."""
    task = asyncio.ensure_future(awaitable)
    try:
        done, _ = await asyncio.wait({task}, timeout=seconds)
    except asyncio.CancelledError:
        task.cancel()
        raise
    if not done:
        task.cancel()
        await asyncio.wait({task})
        raise asyncio.TimeoutError
    return task.result()
