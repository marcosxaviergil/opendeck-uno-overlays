"""Data sources as the vMix manual documents them: rows from a typed list, a text file or a CSV file."""

import csv
import io
import os

from uno.api import UnoError
from uno.files import check_path, read_file

__all__ = ["SUFFIXES", "column_of", "stamp", "table"]

DELIMITERS = {"": ",", ";": ";", "tab": "\t"}


SUFFIXES = {"text": (".txt",), "csv": (".csv", ".tsv", ".txt")}


def stamp(d):
    """Changes when the file changes (vMix: "all Data Sources automatically update")."""
    kind = d.get("kind") or "list"
    if kind == "list":
        return str(d.get("text") or "")
    try:
        info = os.stat(check_path(d.get("path"), SUFFIXES.get(kind, ())))
        return info.st_mtime_ns, info.st_size
    except (OSError, UnoError):
        return None


def table(d):
    """(column names, rows). A text or list row is one line; CSV may use its first row as column names."""
    kind = d.get("kind") or "list"
    text = str(d.get("text") or "") if kind == "list" else read_file(d.get("path"), SUFFIXES.get(kind, ()))
    if kind == "csv":
        data = [
            row
            for row in csv.reader(io.StringIO(text), delimiter=DELIMITERS.get(d.get("delimiter") or "", ","))
            if any(cell.strip() for cell in row)
        ]
        header = data.pop(0) if d.get("header") and data else []
    else:
        data, header = [[line.strip()] for line in text.splitlines() if line.strip()], []
    width = max([len(header)] + [len(row) for row in data])
    names = [(header[i].strip() if i < len(header) else "") or str(i + 1) for i in range(width)]
    return names, [row + [""] * (width - len(row)) for row in data]


def column_of(names, column, field_names, position):
    """vMix mapping: the chosen column; Auto = the column named like the field, else the field's index."""
    if column:
        return names.index(column) if column in names else None
    match = next((name for name in field_names if name in names), None)
    if match is not None:
        return names.index(match)
    return position if 0 <= position < len(names) else None
