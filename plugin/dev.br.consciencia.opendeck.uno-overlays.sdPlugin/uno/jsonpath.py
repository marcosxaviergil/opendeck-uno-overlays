"""JSON paths as the official singular-datastore client applies them (updateJsonObject, non-strict JavaScript).

Pure data functions, ported from singular-datastore 1.0.1 index.js; see docs/SOURCES.md.
"""

import math
from copy import deepcopy

__all__ = ["Skip", "ancestors", "get_path", "js_order", "set_path", "truthy"]

SPARSE_LIMIT = 100_000  # memory guard for JavaScript sparse-array writes


def set_path(data, path, value):
    """Python port of updateJsonObject() in the official singular-datastore client."""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if not truthy(js_get(current, key)):
            js_set(current, key, {})
        current = js_get(current, key)
        if current is None:
            raise Skip("path crosses an undefined value")
    js_set(current, keys[-1], deepcopy(value))


def get_path(data, path):
    for part in path.split("."):
        if isinstance(data, list) and part.isdigit():
            data = data[int(part)] if int(part) < len(data) else None
        elif isinstance(data, dict):
            data = data.get(part)
        else:
            return None
    return data


def js_order(keys):
    """Object.entries() order: array-index keys ascending, then insertion order."""
    keys = list(keys)
    indexes = sorted((k for k in keys if array_index(k) is not None), key=int)
    return indexes + [k for k in keys if array_index(k) is None]


def ancestors(path):
    parts = path.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


class Skip(Exception):
    """A path JSON cannot hold; the official (non-strict) client stores nothing visible."""


def truthy(value):
    """JavaScript truthiness of a JSON value; updateJsonObject() tests !current[key]."""
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0 and not math.isnan(value)
    if isinstance(value, str):
        return value != ""
    return True  # objects and arrays, even empty ones, are truthy in JavaScript


def array_index(key):
    # JavaScript array element keys: canonical integers 0 .. 2**32 - 2.
    if key.isascii() and key.isdigit() and str(int(key)) == key and int(key) < 2**32 - 1:
        return int(key)
    return None


def js_get(container, key):
    if isinstance(container, dict):
        return container.get(key)
    if isinstance(container, list):
        index = array_index(key)
        if index is None:
            raise Skip("non-index property of an array")
        return container[index] if index < len(container) else None
    if isinstance(container, str):
        index = array_index(key)
        return container[index] if index is not None and index < len(container) else None
    return None  # properties of numbers and booleans are undefined


def js_set(container, key, value):
    """Assignment in non-strict JavaScript; the vendor file has no "use strict"."""
    if isinstance(container, dict):
        container[key] = value
    elif isinstance(container, list):
        index = array_index(key)
        if index is None:
            raise Skip("non-index property of an array")
        if index - len(container) > SPARSE_LIMIT:
            raise Skip("sparse array index")
        if index >= len(container):
            container.extend([None] * (index + 1 - len(container)))  # holes serialize as null
        container[index] = value
    else:
        raise Skip("assignment to a primitive value")  # silently ignored by JavaScript
