#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
# The folder as OpenDeck named it (before symbolic links): its settings.json is two levels up (uno/i18n.py).
UNO_PLUGIN_DIR=$(pwd -L)
export UNO_PLUGIN_DIR
if ! command -v python3 >/dev/null 2>&1; then
    echo 'UNO Overlays requires Python 3.10 or newer. Debian: sudo apt install python3' >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo 'UNO Overlays requires Python 3.10 or newer.' >&2
    exit 1
}
exec python3 -B main.py "$@"
