"""Show control: Macro (Companion Sequential + Wait), Panic, Restore and Scene memory."""

import asyncio

from uno.api import UnoError
from uno.automations import app_id
from uno.i18n import tr
from uno.values import composite, integer, typed, visible

__all__ = ["ShowControlMixin"]


class ShowControlMixin:
    def _init_showcontrol(self):
        self.macros, self.panicked = {}, {}

    async def run_macro(self, ctx, s):
        token = self.api(s["token"]).token if s.get("token") else None
        self.macros[ctx] = asyncio.current_task()
        await self.repaint([ctx])
        try:
            for step in s.get("steps") or []:
                if step.get("type") == "wait":  # delays every step after it
                    await asyncio.sleep(max(0, integer(step.get("ms"))) / 1000)
                else:  # each step waits for the previous one to complete
                    await self.run_job(
                        lambda job, step=step: self.macro_step(ctx, s, step),
                        owners={ctx},
                        token=token,
                        overlay=step.get("overlayId") or None,
                    )
        finally:
            self.macros.pop(ctx, None)
            await self.repaint([ctx])

    async def macro_step(self, ctx, s, step):
        kind, overlay_id = step.get("type"), step.get("overlayId", "")
        if kind == "obsscene":
            return await self.run_obs_scene(ctx, {"sceneName": step.get("sceneName", "")})
        api = self.api(s.get("token"))
        if kind == "snapshot":
            return await self.run_snapshot(
                ctx, {"token": s.get("token"), "name": step.get("name"), "operation": "recall"}
            )
        if kind in ("showall", "hideall"):  # every control app of the step; one failure does not stop the rest
            tokens = self.tokens_of({"token": s.get("token"), "tokens": step.get("tokens")})
            return await self.each_app(tokens, lambda api: self.all_overlays(api, kind))
        if kind in ("nextslot", "prevslot"):
            return await self.step_slot(ctx, api, {"overlayId": overlay_id}, kind)
        if kind == "toggle":
            return await self.toggle(ctx, api, {"overlayId": overlay_id})
        if kind == "timer":
            return await self.run_timer(api, step)
        if kind == "setfield":
            overlay_id, field_id = composite(step.get("fieldComposite"))
            store = await self.store(api.token)
            value = typed(step.get("value", ""), store.content(overlay_id).get(field_id))
            return await self.write_content(api, store, overlay_id, {field_id: value})
        if kind not in ("show", "hide", "takeslot") or not overlay_id:
            raise UnoError(tr("A macro step is incomplete. Check it in the inspector."))
        self.cancel_hide(api.token, overlay_id)
        if kind == "hide":
            return await api.call("HideOverlay", id=overlay_id)
        if kind == "takeslot":
            self.check_edits(api.token)
            await api.call("TakeOverlaySlotNumber", id=overlay_id, value=max(1, integer(step.get("slot"), 1)))
        await self.show(api, overlay_id)

    def panic(self):
        self.flush_edits()  # typed text is saved, not lost: edits are not key runs
        for task in self.macros.values():
            task.cancel()
        for handle in self.triggers:
            handle.cancel()
        self.triggers.clear()
        for queue in self.queues:  # control runs only; inspector edits and reads still complete
            for job in [job for job in queue if job.owners or job.numeric]:
                job.dropped = True
                queue.remove(job)
                if job.future is not None and not job.future.done():
                    job.future.cancel()
        for job in self.accumulators.values():
            job.dropped = True
            if job.numeric.get("timer"):
                job.numeric["timer"].cancel()
        self.accumulators.clear()
        for entry in self.timers.values():
            entry[1].cancel()
        self.timers.clear()
        for d in self.dials.values():
            d.update(editing=False, pending=None, spin=0, spin_wait=None)
        for st in self.sources.values():  # Auto Next is a running action too
            if st["auto"]:
                st["auto"].cancel()
                st["auto"] = None

    def every_app(self):
        """Without a token, Panic and Restore act on every registered control app and every one open now."""
        return list(dict.fromkeys([*self.apps().values(), *self.stores]))

    async def run_panic(self, ctx, s):
        tokens = [self.api(s["token"]).token] if s.get("token") else self.every_app()
        await self.each_app(tokens, self.panic_app)
        await self.repaint()

    async def panic_app(self, api):
        on_air = [str(o.get("id")) for o in await api.call("GetOverlays") or [] if visible(o)]
        if on_air:  # a second Panic keeps the set Restore will bring back
            self.panicked[api.token] = on_air
        await api.call("HideAllOverlays")

    async def run_restore(self, ctx, s):
        # Documented limitation: the restore set lives in memory; a plugin restart forgets it.
        tokens = [self.api(s["token"]).token] if s.get("token") else list(self.panicked)
        await self.each_app(tokens, self.restore_app)

    async def restore_app(self, api):
        for overlay_id in self.panicked.pop(api.token, []):
            await api.call("ShowOverlay", id=overlay_id)

    async def each_app(self, tokens, run):
        """Run for every control app; one that fails does not stop the others, and is named (id only)."""
        failed = []
        for token in tokens:
            try:
                await run(self.api(token))
            except UnoError as exc:
                failed.append(tr("Control app {app}: {error}", app=app_id(token), error=exc))
        if failed:
            raise UnoError(" · ".join(failed))

    async def run_snapshot(self, ctx, s):
        name = str(s.get("name") or "").strip()
        if not name:
            raise UnoError(tr("Name the scene in the inspector."))
        api = self.api(s.get("token"))
        store = await self.store(api.token)
        overlays = {str(o.get("id")): o for o in await api.call("GetOverlays") or []}
        scenes = self.global_settings.setdefault("scenes", {})
        if s.get("operation") == "store":
            saved = {}
            for overlay_id, overlay in overlays.items():
                try:
                    saved[overlay_id] = {
                        "visible": visible(overlay),
                        "content": store.content(overlay_id),
                        "slot": store.slots(overlay_id).get("currentSlotId") or "",
                    }
                except UnoError:
                    continue  # not in this control app's datastore
            scenes[name] = {"token": api.token, "overlays": saved}
            await self.message("setGlobalSettings", self.plugin_uuid, self.global_settings)
            return
        scene = scenes.get(name)
        if not scene or scene.get("token") != api.token:
            raise UnoError(tr("Scene {name} was not stored for this token yet.", name=repr(name)))
        safe = set(s.get("safe") or [])
        for overlay_id, saved in scene["overlays"].items():
            overlay = overlays.get(overlay_id)
            if overlay is None or overlay_id in safe:
                continue
            if saved["slot"] and store.slots(overlay_id).get("currentSlotId") != saved["slot"]:
                index, _ = store.slot(overlay_id, 0, saved["slot"])
                await api.call("TakeOverlaySlotNumber", id=overlay_id, value=index + 1)
            current = store.content(overlay_id)
            changes = {key: value for key, value in saved["content"].items() if current.get(key) != value}
            if changes:
                mark = store.events
                await api.call("SetOverlayContent", id=overlay_id, content=changes)
                await store.sync_content(overlay_id, changes, mark)
            if saved["visible"] != visible(overlay):
                self.cancel_hide(api.token, overlay_id)
                await api.call("ShowOverlay" if saved["visible"] else "HideOverlay", id=overlay_id)
