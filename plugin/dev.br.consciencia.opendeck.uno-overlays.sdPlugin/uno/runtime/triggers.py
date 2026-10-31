"""OBS Studio (obs-websocket 5): the connection, OBS keys and the vMix-style actions of Clock and Goal.

The global triggers that react to OBS and UNO events are in uno.runtime.automation.
"""

import logging

from uno.api import UnoError
from uno.i18n import tr
from uno.obs import Obs, check_address
from uno.values import integer, seconds

__all__ = ["TriggerMixin", "browser_sources"]

log = logging.getLogger(__name__)

BROWSER = "browser_source"  # inputKind of OBS browser sources (GetInputList, GetSceneItemList)


class TriggerMixin:
    def _init_triggers(self):
        self.obs, self.obs_config, self.triggers, self.air = None, None, set(), {}

    async def configure_obs(self):
        g = self.global_settings
        config = (
            (g.get("obsHost") or "127.0.0.1", integer(g.get("obsPort"), 4455), g.get("obsPassword") or "")
            if g.get("obsEnabled")
            else None
        )
        if config:
            try:
                check_address(*config[:2])
            except UnoError as exc:
                log.warning("UNO: %s", exc)
                config = None
        if config == self.obs_config:
            return
        if self.obs:
            await self.obs.close()
        self.obs_config, self.obs = config, Obs(*config, self.obs_event) if config else None
        await self.repaint()

    def fire(self, owner, s, trigger):
        """A key's or a definition's own action (Clock "When it completes", Goal "When reached")."""
        function, target = s.get(trigger + "Function"), s.get(trigger + "Target") or s.get("overlayId")
        if function not in ("show", "hide") or not target:
            return
        label = f"{trigger} of {self.actions.get(owner, 'goal').rsplit('.', 1)[-1]}"
        log.info("%s fired: %s overlay %s.", label, function, target)
        self.run_later(self.api(s.get("token")), function, target, integer(s.get(trigger + "Delay")), label)

    async def run_obs_refresh(self, ctx, settings):
        """ "Refresh cache of current page" (refreshnocache) on each browser source; one failure does not stop
        the others. Scene mode: every browser source in the scene, its groups and nested scenes."""
        self.check_obs()
        if settings.get("refreshMode") == "scene":
            names = await browser_sources(self.obs, str(settings.get("refreshScene") or ""))
        else:
            names = [settings.get("inputName"), *(settings.get("inputNames") or [])]
        names = list(dict.fromkeys(str(n).strip() for n in names if str(n or "").strip()))
        if not names:
            raise UnoError(tr("Choose at least one browser source, or a scene."))
        failed = []
        for name in names:
            try:
                await self.obs.request(
                    "PressInputPropertiesButton", {"inputName": name, "propertyName": "refreshnocache"}
                )
                log.info("OBS Refresh Browser: %r refreshed.", name)
            except UnoError as exc:
                log.warning("OBS Refresh Browser: %r failed: %s", name, exc)
                failed.append(name)
        self.note(tr("Refreshed {done} of {total} browser sources.", done=len(names) - len(failed), total=len(names)))
        if failed:
            raise UnoError(tr("Not refreshed: {names}. Check them in OBS.", names=", ".join(failed)))

    async def run_obs_scene(self, ctx, settings):
        """Program scene, then optionally show an overlay with Auto Close."""
        self.check_obs()
        await self.obs.request("SetCurrentProgramScene", {"sceneName": settings.get("sceneName", "")})
        if settings.get("overlayId") and settings.get("token"):
            overlay_id = settings["overlayId"]
            api = self.api(settings["token"])
            self.cancel_hide(api.token, overlay_id)
            slot = max(0, integer(settings.get("slotNumber")))
            slot_id = settings.get("serverSlotId") or ""
            if slot or slot_id:
                store = await self.store(api.token)
                index, _ = store.slot(overlay_id, slot, slot_id)
                await api.call("TakeOverlaySlotNumber", id=overlay_id, value=index + 1)
            await self.show(api, overlay_id)
            self.schedule_hide(ctx, api, overlay_id, seconds(settings.get("autoClose")))

    def check_obs(self):
        if not (self.obs and self.obs.connected):
            raise UnoError(tr("OBS is not connected. Set it up in OpenDeck: Plugins → UNO Overlays → Settings (gear)."))

    async def obs_lists(self):
        self.check_obs()
        scenes = (await self.obs.request("GetSceneList")).get("scenes") or []
        inputs = (await self.obs.request("GetInputList", {"inputKind": BROWSER})).get("inputs") or []
        return {
            "scenes": [scene.get("sceneName") for scene in scenes],
            "browsers": [item.get("inputName") for item in inputs],
        }


async def browser_sources(obs, scene):
    """Browser sources shown by a scene, in order: its items, its groups and its nested scenes.

    obs-websocket 5 (utils/Obs_ArrayHelper.cpp, the same since 5.0.0): each scene item has sourceName,
    inputKind (null when it is not an input) and isGroup (null unless it is a scene; true for a group).
    Groups are read with GetGroupSceneItemList; nested scenes with GetSceneItemList, each scene once.
    """
    if not scene:
        raise UnoError(tr("Choose the OBS scene whose browser sources are refreshed."))
    found, seen, pending = [], set(), [(scene, False)]
    while pending:
        name, group = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        request = "GetGroupSceneItemList" if group else "GetSceneItemList"
        for item in (await obs.request(request, {"sceneName": name})).get("sceneItems") or []:
            source = str(item.get("sourceName") or "")
            if item.get("inputKind") == BROWSER and source not in found:
                found.append(source)
            elif item.get("isGroup") is not None and source:
                pending.append((source, bool(item.get("isGroup"))))
    return found