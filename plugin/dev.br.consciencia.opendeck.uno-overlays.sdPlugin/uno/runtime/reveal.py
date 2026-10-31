"""Reveal Answer: toggle a field of the live content between "hidden" and "revealed" (quiz).

Generic on purpose: the uno quiz overlays were not inspected (their field names are not public), so
the key names the field, the two values and an optional field copied when revealing (for example the
correct option into a highlight field). Writes go to the live content, which is the slot on air.
On a new slot the answer goes back to hidden, also when no Reveal key is visible: the key's settings
are remembered by field in the global settings (uno.runtime.automation).
"""

import logging

from uno.api import UnoError
from uno.automations import app_id
from uno.i18n import tr
from uno.runtime.automation import AUTOMATION
from uno.values import composite, scalar, typed

__all__ = ["RevealMixin"]

log = logging.getLogger(__name__)


class RevealMixin:
    def _init_reveal(self):
        self.slot_seen = {}  # (token, overlay) -> current slot id last seen

    async def run_reveal(self, ctx, s):
        api = self.api(s.get("token"))
        store = await self.store(api.token)
        overlay_id, field_id = composite(s.get("fieldComposite"))
        if not field_id:
            raise UnoError(tr("Select the field that shows the answer."))
        reveal = not self.revealed(store, s)
        await self.write_reveal(api, store, s, reveal)
        log.info("Reveal Answer: %s %s.", "revealed" if reveal else "hidden", f"{overlay_id}::{field_id}")
        self.note(tr("Answer revealed.") if reveal else tr("Answer hidden."))

    @staticmethod
    def revealed(store, s):
        overlay_id, field_id = composite(s.get("fieldComposite"))
        try:
            current = store.content(overlay_id).get(field_id)
        except UnoError:
            return False
        return scalar(current) == scalar(typed(setting(s, "shownValue", "true"), current))

    async def write_reveal(self, api, store, s, reveal):
        overlay_id, field_id = composite(s.get("fieldComposite"))
        content = store.content(overlay_id)
        state = setting(s, "shownValue", "true") if reveal else setting(s, "hiddenValue", "false")
        patch = {field_id: typed(state, content.get(field_id))}
        source, target = composite(s.get("copyFrom")), composite(s.get("copyTo"))
        patches = {overlay_id: patch}
        if target[1]:  # optional highlight: the correct answer goes into another field while revealed
            value = store.content(source[0]).get(source[1], "") if reveal and source[1] else ""
            patches.setdefault(target[0], {})[target[1]] = typed(value, store.content(target[0]).get(target[1]))
        for overlay, changes in patches.items():
            await self.write_content(api, store, overlay, changes)

    def slots_changed(self, store):
        """A new slot on air hides the answer of every Reveal setting of this control app."""
        app = app_id(store.token)
        for key, config in (self.global_settings.get("revealConfigs") or {}).items():
            if not isinstance(config, dict) or not key.startswith(app + "::"):
                continue
            overlay_id = composite(config.get("fieldComposite"))[0]
            try:
                slot = store.slots(overlay_id).get("currentSlotId")
            except UnoError:
                continue
            before, self.slot_seen[(store.token, overlay_id)] = self.slot_seen.get((store.token, overlay_id)), slot
            s = {**config, "token": store.token}
            if before is not None and before != slot and self.revealed(store, s):
                log.info("Reveal Answer: new slot on %s, answer hidden again.", overlay_id)
                api = self.api(store.token)
                self.submit(
                    lambda job, s=s, api=api: self.write_reveal(api, store, s, False),
                    owners={AUTOMATION},
                    token=store.token,
                    overlay=overlay_id,
                )


def setting(s, key, default):
    """A typed value of the key, else the default ("true" shown, "false" hidden)."""
    return default if s.get(key) in (None, "") else str(s[key])
