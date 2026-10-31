"""Data sources as in vMix: rows from a list, .txt or .csv, mapped to fields, Auto Next and Loop."""

import asyncio
import logging

from uno.api import UnoError
from uno.i18n import tr
from uno.images import RED, WHITE, caption, icon_image
from uno.sources import column_of, stamp, table
from uno.values import composite, integer, number, render, typed

__all__ = ["DataSourceMixin", "row_after"]

log = logging.getLogger(__name__)


class DataSourceMixin:
    def _init_datasources(self):
        self.sources, self.source_task = {}, None

    async def run_source(self, ctx, s):
        name = str(s.get("source") or "")
        d, st = self.definition("dataSources", name), self.source_state(name)
        if (s.get("operation") or "next") == "autonext":  # Auto Next on/off; red while it runs
            if st["auto"]:
                st["auto"].cancel()
                st["auto"] = None
            else:
                if number(d.get("seconds")) <= 0:
                    raise UnoError(tr("Type the Auto Next seconds of the data source."))
                if st["row"] is None:
                    await self.write_row(name, d, 0)
                st["auto"] = self.spawn(self.auto_next(name))
            await self.repaint()
            return
        _, rows = table(d)
        await self.write_row(
            name, d, row_after(st["row"], s.get("operation") or "next", s.get("row"), len(rows), d.get("loop"))
        )

    async def write_row(self, name, d, index, only_changed=False):
        """Selecting a row updates every mapped field (vMix mapping: Column, Row, Format)."""
        if not d.get("map"):
            raise UnoError(tr("Map at least one field in the data source."))
        version = stamp(d)  # read before the rows, so a change during the read is seen next time
        names, rows = table(d)
        if not rows:
            raise UnoError(tr("The data source has no rows."))
        api = self.api(d.get("token"))
        store = await self.store(api.token)
        st = self.source_state(name)
        index = min(index, len(rows) - 1)
        patches, written = {}, {}
        for m in d.get("map") or []:
            overlay_id, field_id = composite(m.get("field"))
            if not field_id:
                continue
            fixed = integer(m.get("row"))  # Row: "Selected" (empty) or a fixed row number
            row = rows[index] if fixed <= 0 else rows[fixed - 1] if fixed <= len(rows) else [""] * len(names)
            spec, position = self.model_field(store, overlay_id, field_id)
            column = column_of(names, m.get("column") or "", [field_id, str(spec.get("title") or "")], position)
            value = row[column] if column is not None else ""
            text = render(
                m.get("format") or "{0}",
                lambda key, value=value, row=row: (
                    value if key == "0" else row[names.index(key)] if key in names else None
                ),
            )
            if only_changed and st["written"].get((overlay_id, field_id)) == text:
                continue
            written[(overlay_id, field_id)] = text
            patches.setdefault(overlay_id, {})[field_id] = typed(text, store.content(overlay_id).get(field_id))
        for overlay_id, patch in patches.items():
            await self.write_content(api, store, overlay_id, patch)
        st.update(row=index, stamp=version)
        st["written"].update(written)
        self.watch_sources()
        await self.repaint()

    def definition(self, kind, name):
        """Data sources, polls and goals live in the global settings, shared by every key."""
        d = (self.global_settings.get(kind) or {}).get(str(name or ""))
        if not isinstance(d, dict):
            choose = {"dataSources": tr("Choose a data source."), "polls": tr("Choose a poll.")}
            raise UnoError(choose.get(kind) or tr("Choose a goal."))
        return d

    def source_state(self, name):
        return self.sources.setdefault(name, {"row": None, "auto": None, "written": {}, "stamp": None})

    async def auto_next(self, name):
        # vMix: "the number of seconds between each row"; Loop jumps to the start after the last row.
        st = self.source_state(name)
        try:
            while True:
                await asyncio.sleep(float(number(self.definition("dataSources", name).get("seconds"))) or 1)
                d = self.definition("dataSources", name)
                _, rows = table(d)
                if st["row"] is not None and st["row"] >= len(rows) - 1 and not d.get("loop"):
                    return
                index = row_after(st["row"], "next", None, len(rows), d.get("loop"))
                await self.run_job(
                    lambda job, d=d, index=index: self.write_row(name, d, index),
                    token=str(d.get("token") or "").strip(),
                )
        except UnoError as exc:
            log.warning("UNO data source: %s", exc)
        finally:
            if st["auto"] is asyncio.current_task():
                st["auto"] = None
                self.spawn(self.repaint())

    @staticmethod
    def model_field(store, overlay_id, field_id):
        """(model field, index in the overlay model): vMix Auto maps by name, else by field index.
        controlNode.model.fields, as singular-datastore processPayloadCommand() reads it."""
        fields = (store.node(overlay_id)[1].get("model") or {}).get("fields") or {}
        fields = [f for f in (fields.values() if isinstance(fields, dict) else fields) if isinstance(f, dict)]
        return next(((f, i) for i, f in enumerate(fields) if f.get("id") == field_id), ({}, -1))

    def watch_sources(self):
        if self.source_task is None or self.source_task.done():
            self.source_task = self.spawn(self.source_watch())

    async def source_watch(self):
        # vMix: "all Data Sources automatically update". A changed file or list rewrites the changed fields.
        while any(st["row"] is not None for st in self.sources.values()):
            await asyncio.sleep(1)
            for name, st in list(self.sources.items()):
                d = (self.global_settings.get("dataSources") or {}).get(name)
                if st["row"] is None or not isinstance(d, dict) or stamp(d) == st["stamp"]:
                    continue
                st["stamp"] = stamp(d)
                self.submit(
                    lambda job, name=name, d=d, row=st["row"]: self.logged(self.write_row(name, d, row, True)),
                    token=str(d.get("token") or "").strip(),
                )

    async def logged(self, coro):
        try:
            await coro
        except UnoError as exc:
            log.warning("UNO: %s", exc)

    def cue_row(self, ctx, s, ticks):
        """Knob: turning moves through the rows (shown on the Visor), pressing selects one."""
        name = str(s.get("source") or "")
        _, rows = table(self.definition("dataSources", name))
        if not rows:
            raise UnoError(tr("The data source has no rows."))
        d = self.dials.setdefault(ctx, {})
        d["row"] = (d.get("row", self.source_state(name)["row"] or 0) + ticks) % len(rows)
        self.spawn(self.repaint())

    def take_row(self, ctx, s):
        name = str(s.get("source") or "")
        d = self.definition("dataSources", name)
        index = self.dials.setdefault(ctx, {}).get("row", self.source_state(name)["row"] or 0)
        self.submit(lambda job: self.write_row(name, d, index), owners={ctx})

    def source_image(self, ctx, s):
        try:
            names, rows = table(self.definition("dataSources", s.get("source")))
        except UnoError:
            return icon_image("datasource")
        if not rows:
            return icon_image("datasource", WHITE, None, [tr("No rows")])
        st = self.source_state(str(s.get("source") or ""))
        index = self.dials.get(ctx, {}).get("row", st["row"] or 0) % len(rows)
        return icon_image(
            "datasource", RED if index == st["row"] else WHITE, None, caption(f"{index + 1} {rows[index][0]}")
        )


def row_after(current, operation, row, count, loop):
    """DataSourceNextRow / PreviousRow / SelectRow. Loop: after the last row, jump to the start."""
    if not count:
        raise UnoError(tr("The data source has no rows."))
    if operation == "select":
        index = integer(row, 1) - 1
        if not 0 <= index < count:
            raise UnoError(
                tr("Row {row} does not exist; the data source has {count} rows.", row=index + 1, count=count)
            )
        return index
    if current is None:
        return 0
    index = min(current, count - 1) + (1 if operation == "next" else -1)
    return 0 if index >= count and loop else max(0, min(index, count - 1))
