"""Local files named in the inspector: data source rows (.txt, .csv) and backups (.json).

Inspector requests reach the plugin through OpenDeck, whose WebSocket server also accepts
connections from the network (docs/SECURITY.md). A path is therefore never trusted: it must be
absolute, have the expected extension and point to a regular file of limited size, and a
backup never overwrites a file that is not a backup.
"""

import json
import os
import stat

from uno import PLUGIN_ID
from uno.api import UnoError
from uno.i18n import tr

__all__ = ["MAX_BYTES", "check_path", "read_file", "write_private"]

MAX_BYTES = 10_000_000


def check_path(path, suffixes, default=""):
    """The absolute path the user typed, or UnoError with the fix."""
    path = os.path.expanduser(str(path or "").strip() or default)
    if not path:
        raise UnoError(tr("Type the file path."))
    if not os.path.isabs(path):
        raise UnoError(tr("Type the full path of the file, starting with / or ~/."))
    if os.path.splitext(path)[1].lower() not in suffixes:
        raise UnoError(tr("Use a {suffixes} file here.", suffixes=" / ".join(suffixes)))
    return path


def read_file(path, suffixes, limit=MAX_BYTES):
    """Text of a regular UTF-8 file (a BOM is ignored)."""
    path = check_path(path, suffixes)
    name = os.path.basename(path)
    try:
        info = os.stat(path)
        if not stat.S_ISREG(info.st_mode):
            raise UnoError(tr("{name} is not a regular file.", name=name))
        if info.st_size > limit:
            raise UnoError(tr("{name} is larger than {size} MB.", name=name, size=limit // 1_000_000))
        with open(path, encoding="utf-8-sig", newline="") as f:
            return f.read(limit + 1)[:limit]
    except OSError as exc:
        raise UnoError(tr("Cannot read {name}: {reason}.", name=name, reason=exc.strerror)) from None
    except UnicodeDecodeError:
        raise UnoError(tr("{name} is not UTF-8; save it as UTF-8.", name=name)) from None


def write_private(path, data):
    """Write JSON readable by the owner only; replace only an earlier backup of this plugin."""
    name = os.path.basename(path)
    if os.path.lexists(path):
        try:
            earlier = json.loads(read_file(path, (".json",)))
        except (UnoError, ValueError):
            earlier = None
        if os.path.islink(path) or not isinstance(earlier, dict) or earlier.get("plugin") != PLUGIN_ID:
            raise UnoError(tr("{name} exists and is not a UNO Overlays backup; choose another name.", name=name))
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)  # the file may hold tokens and names: owner only
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise UnoError(tr("Cannot write {name}: {reason}.", name=name, reason=exc.strerror)) from None
