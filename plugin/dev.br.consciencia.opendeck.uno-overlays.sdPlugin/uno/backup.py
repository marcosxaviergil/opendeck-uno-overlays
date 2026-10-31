"""Export and import of the plugin's shared settings. API tokens and the OBS password only when asked."""

import json
import os
from copy import deepcopy

from uno import PLUGIN_ID, VERSION
from uno.api import UnoError, token_value
from uno.files import check_path, read_file, write_private
from uno.i18n import tr

__all__ = ["DEFAULT", "export", "restore"]

DEFAULT = "~/uno-overlays-backup.json"
NAMED = ("scenes", "dataSources", "polls", "goals")
SHARED = NAMED + (
    "favorites", "obsEnabled", "obsHost", "obsPort", "multiplier", "lockAfter", "apiCap",
    "triggers", "groups", "language", "liveEditDelay", "clockConfigs", "revealConfigs",
)  # fmt: skip
SECRET = ("obsPassword", "controlApps")  # only when asked: the OBS password and the tokens of the control apps
LIVE = ("state", "reached", "started")  # a running goal belongs to the plugin, not to a backup


def export(settings, path, secrets):
    data = {"plugin": PLUGIN_ID, "version": VERSION}
    data.update({key: deepcopy(settings[key]) for key in SHARED if key in settings})
    for kind in NAMED:
        for item in (data.get(kind) or {}).values():
            if isinstance(item, dict):
                for key in LIVE + (() if secrets else ("token",)):
                    item.pop(key, None)
    if secrets:
        data.update({key: deepcopy(settings[key]) for key in SECRET if settings.get(key)})
    path = check_path(path, (".json",), DEFAULT)
    write_private(path, data)
    return path, sum(len(data.get(kind) or {}) for kind in NAMED)


def restore(settings, path, token=""):
    """Settings with the backup merged in: items with the same name are replaced."""
    path = check_path(path, (".json",), DEFAULT)
    try:
        data = json.loads(read_file(path, (".json",)))
    except ValueError:
        raise UnoError(tr("{name} is not a JSON backup.", name=os.path.basename(path))) from None
    if not isinstance(data, dict) or data.get("plugin") != PLUGIN_ID:
        raise UnoError(tr("This file is not a UNO Overlays backup."))
    result, count = deepcopy(settings), 0
    for key in SHARED + SECRET:
        if key not in data:
            continue
        if key == "controlApps" and isinstance(data[key], dict):  # merged: apps of this computer stay
            result[key] = {**(result.get(key) or {}), **data[key]}
            continue
        if key not in NAMED:
            result[key] = data[key]
            continue
        items = {
            name: item
            for name, item in (data[key] if isinstance(data[key], dict) else {}).items()
            if isinstance(item, dict)
        }
        for item in items.values():
            for live in LIVE:
                item.pop(live, None)
            if not item.get("token"):
                if not token:
                    raise UnoError(tr("The backup has no API tokens: type the API token to use for them."))
                item["token"] = token_value(token)
        result[key] = {**(result.get(key) or {}), **items}
        count += len(items)
    return result, count
