"""Numeric fields: merged increments with delay, Auto Close, limits, undo and point graphic."""

import asyncio

from uno.api import UnoError
from uno.i18n import tr
from uno.values import increment, seconds, visible

__all__ = ["NumericMixin"]


class NumericMixin:
    def queue_numeric(self, ctx, api, settings, delta):
        overlay_id, field_id = settings.get("overlayId"), settings.get("fieldId")
        if not overlay_id or not field_id:
            raise UnoError(tr("Select a numeric field."))
        self.check_lock(api.token)
        delay, auto = seconds(settings.get("delay")), seconds(settings.get("autoClose"))
        limits = (str(settings.get("min") or ""), str(settings.get("max") or ""), bool(settings.get("modelLimits")))
        point = (settings.get("pointOverlayId") or "", seconds(settings.get("pointSeconds")) or 5)
        key = (api.token, overlay_id, field_id, delay, auto, limits, point)
        job = self.accumulators.get(key)
        if job is not None and self.mergeable(job):
            deltas = job.numeric["deltas"]
            deltas[ctx] = deltas.get(ctx, 0) + delta
            return
        numeric = {
            "key": key,
            "api": api,
            "deltas": {ctx: delta},
            "owner": ctx,
            "phase": "show" if delay else "update",
            "timer": None,
        }
        self.accumulators[key] = self.submit(
            self.run_numeric, token=api.token, overlay=overlay_id, numeric=numeric, barrier=False
        )

    async def run_numeric(self, job):
        n = job.numeric
        token, overlay_id, field_id, delay, auto, limits, point = n["key"]
        api = n["api"]
        if n["phase"] == "show":
            # Delay: show now, update after the delay; ticks keep merging meanwhile.
            self.cancel_hide(token, overlay_id)
            if not visible(await self.overlay(api, overlay_id)):
                await self.show(api, overlay_id)
            n["phase"] = "update"
            if not job.dropped:
                n["timer"] = asyncio.get_running_loop().call_later(delay, self.requeue, job)
            return
        self.cancel_hide(token, overlay_id)
        delta = sum(n["deltas"].values())
        if delta:
            self.check_lock(token)
            store = await self.store(token)
            value = increment(store.content(overlay_id).get(field_id), delta)
            clamped = self.clamp(store, overlay_id, field_id, value, limits)
            if clamped != value:
                await self.message("showAlert", n["owner"])  # limit reached: warn on the key
            self.remember(token, store, {overlay_id: [field_id]})
            await self.write_content(api, store, overlay_id, {field_id: clamped})
            if delta > 0 and point[0]:  # optional: a point shows a graphic for N seconds
                self.cancel_hide(token, point[0])
                await self.show(api, point[0])
                self.schedule_hide(n["owner"], api, point[0], point[1])
        self.schedule_hide(n["owner"], api, overlay_id, auto)
