"""Scoreboard tools: Lock, limits (model min/max), Undo history, Cycle, Swap Sides and Reset."""

from copy import deepcopy

from uno.api import UnoError
from uno.i18n import tr
from uno.values import composite, increment, scalar, typed

__all__ = ["ScoreboardMixin"]


class ScoreboardMixin:
    def _init_scoreboard(self):
        self.history, self.locked, self.holds = [], set(), {}

    def check_lock(self, token):
        if token in self.locked:
            raise UnoError(tr("The scoreboard is locked. Press Lock again to unlock it."))

    def clamp(self, store, overlay_id, field_id, value, limits):
        low, high, model = limits
        highs, lows = [high], [low]
        if model:
            spec = self.model_field(store, overlay_id, field_id)[0]
            highs.append(spec.get("max"))
            lows.append(spec.get("min"))
        try:
            number = float(scalar(value).replace(",", "."))
            target = number
            for limit in highs:  # the official client applies max, then min
                if limit not in (None, ""):
                    target = min(target, float(limit))
            for limit in lows:
                if limit not in (None, ""):
                    target = max(target, float(limit))
        except ValueError:
            return value
        return value if target == number else increment(value, target - number)  # keeps the field's type

    def remember(self, token, store, fields):
        """One undo entry: the previous value of each changed field."""
        entry = [
            (overlay_id, {f: deepcopy(store.content(overlay_id).get(f)) for f in names})
            for overlay_id, names in fields.items()
        ]
        self.history.append((token, entry))
        del self.history[:-50]  # ponytail: last 50 changes, in memory only

    async def commit(self, api, store, patches, empty):
        """Writes several fields as one undo entry."""
        if not patches:
            raise UnoError(empty)
        self.remember(api.token, store, {o: list(patch) for o, patch in patches.items()})
        for overlay_id, patch in patches.items():
            await self.write_content(api, store, overlay_id, patch)

    async def run_undo(self, ctx, s):
        api = self.api(s.get("token"))
        self.check_lock(api.token)
        only = s.get("fieldComposite")  # optional: undo only this field's last change
        for i in range(len(self.history) - 1, -1, -1):
            token, entry = self.history[i]
            if token == api.token and (not only or any(f"{o}::{f}" == only for o, previous in entry for f in previous)):
                del self.history[i]
                store = await self.store(token)
                for overlay_id, previous in entry:
                    await self.write_content(api, store, overlay_id, previous)
                return
        raise UnoError(tr("Nothing to undo."))

    async def run_cycle(self, ctx, s):
        api = self.api(s.get("token"))
        self.check_lock(api.token)
        overlay_id, field_id = composite(s.get("fieldComposite"))
        values = [v.strip() for v in str(s.get("values") or "").splitlines() if v.strip()]
        if not field_id or not values:
            raise UnoError(tr("Select a field and type the values, one per line."))
        store = await self.store(api.token)
        current = store.content(overlay_id).get(field_id)
        position = values.index(scalar(current)) + 1 if scalar(current) in values else 0
        self.remember(api.token, store, {overlay_id: [field_id]})
        await self.write_content(api, store, overlay_id, {field_id: typed(values[position % len(values)], current)})
        if s.get("resetClock"):  # e.g. a new period restarts the game clock
            self.clock_op(ctx, self.clock_config(api.token, s["resetClock"]), "stop")

    async def run_swap(self, ctx, s):
        api = self.api(s.get("token"))
        self.check_lock(api.token)
        store = await self.store(api.token)
        patches = {}
        for pair in s.get("pairs") or []:
            (a_overlay, a_field), (b_overlay, b_field) = composite(pair.get("a")), composite(pair.get("b"))
            if a_field and b_field:
                a_value, b_value = store.content(a_overlay).get(a_field), store.content(b_overlay).get(b_field)
                patches.setdefault(a_overlay, {})[a_field] = b_value
                patches.setdefault(b_overlay, {})[b_field] = a_value
        await self.commit(api, store, patches, "Choose the pairs of fields to swap.")

    async def run_reset(self, ctx, s):
        api = self.api(s.get("token"))
        self.check_lock(api.token)
        store = await self.store(api.token)
        patches = {}
        for item in s.get("fields") or []:
            overlay_id, field_id = composite(item)
            current = store.content(overlay_id).get(field_id)
            reset = self.model_field(store, overlay_id, field_id)[0].get("resetValue")
            if reset is not None:  # model resetValue, like the official "reset" command
                value = typed(reset, 0)
            elif isinstance(current, (int, float)) and not isinstance(current, bool):
                value = 0
            else:
                try:  # a number typed in a text field becomes "0"; other text is cleared
                    float(scalar(current).replace(",", "."))
                    value = "0"
                except ValueError:
                    value = ""
            patches.setdefault(overlay_id, {})[field_id] = value
            self.clocks.pop((api.token, overlay_id, field_id), None)
        await self.commit(api, store, patches, "Choose the fields to reset.")
