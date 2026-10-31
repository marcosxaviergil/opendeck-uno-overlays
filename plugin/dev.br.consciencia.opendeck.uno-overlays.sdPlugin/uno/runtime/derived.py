"""Text templates, polls and goals: fields computed from other fields."""

import logging
import time

from uno.api import UnoError
from uno.i18n import tr
from uno.values import composite, integer, number, percent, render, scalar, typed

__all__ = ["DerivedMixin", "value_of"]

log = logging.getLogger(__name__)


class DerivedMixin:
    def _init_derived(self):
        self.deriving = set()

    async def run_template(self, ctx, s):
        api = self.api(s.get("token"))
        overlay_id, field_id = composite(s.get("fieldComposite"))
        if not field_id:
            raise UnoError(tr("Select the field that receives the text."))
        store = await self.store(api.token)
        await self.write_content(
            api, store, overlay_id, {field_id: render(s.get("text") or "", lambda key: value_of(store, key))}
        )

    def derive(self, store):
        for kind, patches in (("polls", self.poll_patches), ("goals", self.goal_patches)):
            for name, d in list((self.global_settings.get(kind) or {}).items()):
                if (
                    not isinstance(d, dict)
                    or str(d.get("token") or "").strip() != store.token
                    or (kind, name) in self.deriving
                ):
                    continue
                try:
                    pending = patches(store, name, d)
                except UnoError:
                    continue  # a field of a removed overlay: nothing to derive
                if pending:
                    self.deriving.add((kind, name))
                    self.submit(
                        lambda job, kind=kind, name=name, patches=patches: self.write_derived(kind, name, patches),
                        token=store.token,
                    )

    async def write_derived(self, kind, name, patches):
        try:
            d = self.definition(kind, name)
            api = self.api(d.get("token"))
            store = await self.store(api.token)
            for overlay_id, patch in patches(store, name, d).items():
                await self.write_content(api, store, overlay_id, patch)
        except UnoError as exc:
            log.warning("UNO %s: %s", kind[:-1], exc)
        finally:
            self.deriving.discard((kind, name))

    @staticmethod
    def changed(store, patches, field, value, fmt=""):
        overlay_id, field_id = composite(field)
        if not field_id:
            return
        current = store.content(overlay_id).get(field_id)
        value = typed(render(fmt or "{0}", lambda key: value if key == "0" else None), current)
        if scalar(value) != scalar(current):
            patches.setdefault(overlay_id, {})[field_id] = value

    def poll_patches(self, store, name, d):
        """Total and whole percent of each option (half up), written only when they differ."""
        options = [o for o in d.get("options") or [] if isinstance(o, dict)]
        votes = [number(value_of(store, o.get("votes"))) for o in options]
        patches = {}
        self.changed(store, patches, d.get("total"), sum(votes))
        for option, count in zip(options, votes, strict=True):
            self.changed(store, patches, option.get("percent"), percent(count, sum(votes)), d.get("format"))
        return patches

    def goal_patches(self, store, name, d):
        current = number(value_of(store, d.get("current")))
        patches = {}
        self.changed(store, patches, d.get("percent"), percent(current, d.get("goal")), d.get("percentFormat"))
        if (
            d.get("state") == "active"
            and not d.get("reached")
            and number(d.get("goal"))
            and current >= number(d.get("goal"))
        ):
            self.save_goal(name, reached=True)  # first time the goal is reached: optional trigger
            self.fire(
                name,
                {
                    "token": d.get("token"),
                    **{k: d.get(k) for k in ("reachedFunction", "reachedTarget", "reachedDelay")},
                },
                "reached",
            )
        return patches

    async def run_goal(self, ctx, s, operation):
        """Streamlabs goal: Title, Goal Amount, Starting Amount, End After; a started goal is not edited."""
        name = str(s.get("goal") or "")
        d = self.definition("goals", name)
        if operation == "end":
            self.save_goal(name, state="ended")
            await self.repaint()
            return
        api = self.api(d.get("token"))
        store = await self.store(api.token)
        if number(d.get("goal")) <= 0 or not composite(d.get("current"))[1]:
            raise UnoError(tr("Type the goal amount and choose the field of the current amount."))
        patches = {}
        for field, value, fmt in (
            (d.get("titleField"), d.get("title") or "", ""),
            (d.get("goalField"), number(d.get("goal")), d.get("goalFormat")),
            (d.get("current"), number(d.get("start")), ""),
        ):
            self.changed(store, patches, field, value, fmt)
        self.save_goal(name, state="active", reached=False, started=time.strftime("%Y-%m-%dT%H:%M"))
        for overlay_id, patch in patches.items():
            await self.write_content(api, store, overlay_id, patch)
        await self.repaint()

    def vote(self, ctx, s, delta):
        """Poll Vote: add to the option's votes field (Undo and Lock apply, like the score)."""
        poll = self.definition("polls", s.get("poll"))
        options = poll.get("options") or []
        index = integer(s.get("option"), 1) - 1
        if not 0 <= index < len(options):
            raise UnoError(tr("Choose the option this key votes for."))
        overlay_id, field_id = composite(options[index].get("votes"))
        self.queue_numeric(
            ctx,
            self.api(poll.get("token")),
            {"token": poll.get("token"), "overlayId": overlay_id, "fieldId": field_id},
            delta,
        )

    def goal_add(self, ctx, s, steps):
        d = self.definition("goals", s.get("goal"))
        if d.get("state") != "active":
            raise UnoError(tr("Start the goal first."))
        end = str(d.get("end") or "")
        if end and time.strftime("%Y-%m-%dT%H:%M") >= end[:16]:
            raise UnoError(tr("The goal ended at {end}.", end=end.replace("T", " ")))
        overlay_id, field_id = composite(d.get("current"))
        amount = number(s.get("amount")) or 1
        self.queue_numeric(
            ctx,
            self.api(d.get("token")),
            {"token": d.get("token"), "overlayId": overlay_id, "fieldId": field_id},
            amount * steps,
        )

    def save_goal(self, name, **changes):
        goals = self.global_settings.setdefault("goals", {})
        goals[name] = {**goals.get(name, {}), **changes}
        self.spawn(self.message("setGlobalSettings", self.plugin_uuid, self.global_settings))


def value_of(store, field):
    """Current value of an "overlay::field" composite; None when it names no field."""
    overlay_id, field_id = composite(field)
    return store.content(overlay_id).get(field_id) if field_id else None
