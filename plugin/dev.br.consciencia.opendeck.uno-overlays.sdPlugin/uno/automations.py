"""Global automations: triggers and exclusive groups that belong to the plugin, not to a key.

OpenDeck 2.14 tells a plugin about a key only while it is on the selected profile of a connected
device (willAppear in events/inbound/devices.rs and events/frontend/profiles.rs). Rules kept in a
key's settings therefore stopped when that key was not visible. These rules live in the global
settings, which OpenDeck always sends at start (didReceiveGlobalSettings).

A trigger (vMix style: event → Function on an Input, Delay up to 30 000 ms):
    {"id", "on", "event", "scene", "sourceApp", "sourceOverlay", "function", "app", "overlay",
     "slotNumber", "serverSlotId", "autoClose", "delay"}
"app" is the control app id (start of the token's SHA-256); the token itself lives once, in the
registry of control apps ("controlApps"), so triggers and backups never repeat it.
A group (Singular logic layer): name → {"delay": seconds, -30 to 30, "members": [{"app", "overlay"}]}.
"""

import hashlib
import secrets

from uno.values import integer, seconds

__all__ = [
    "EVENTS",
    "LEGACY",
    "OBS_EVENTS",
    "SCENE_EVENTS",
    "UNO_EVENTS",
    "app_id",
    "clean_group",
    "clean_trigger",
    "group_delay",
    "key_triggers",
    "merge_triggers",
    "strip_legacy",
]

SCENE_EVENTS = ("obsIn", "obsOut")
OBS_EVENTS = (*SCENE_EVENTS, "obsStreamStart", "obsStreamStop", "obsRecordStart", "obsRecordStop")
UNO_EVENTS = ("unoIn", "unoOut")  # vMix OnOverlayIn / OnOverlayOut
EVENTS = OBS_EVENTS + UNO_EVENTS
# Overlay key settings of 1.0.0 that moved to the global settings (or went away: offAir, item 10).
LEGACY = ("obsScene", "groupDelay", "offAir", "offAirDelay") + tuple(
    event + part for event in EVENTS for part in ("Function", "Target", "Delay")
)
IDENTITY = (
    "event", "scene", "sourceApp", "sourceOverlay", "function", "app", "overlay",
    "slotNumber", "serverSlotId", "autoClose", "delay",
)


def app_id(token):
    """Short, non-secret name of a control app: the start of the token's SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()[:6]


def clean_trigger(raw):
    """A trigger with only known fields and valid values; None when it cannot run."""
    if not isinstance(raw, dict) or raw.get("event") not in EVENTS or raw.get("function") not in ("show", "hide"):
        return None
    text = {key: str(raw.get(key) or "").strip()[:200] for key in ("scene", "sourceApp", "sourceOverlay", "app")}
    showing = raw["function"] == "show"
    return {
        "id": str(raw.get("id") or secrets.token_hex(4))[:16],
        "on": raw.get("on") is not False,  # JSON false only: a missing flag keeps it on
        "event": raw["event"],
        "scene": text["scene"] if raw["event"] in SCENE_EVENTS else "",
        "sourceApp": text["sourceApp"] if raw["event"] in UNO_EVENTS else "",
        "sourceOverlay": text["sourceOverlay"] if raw["event"] in UNO_EVENTS else "",
        "function": raw["function"],
        "app": text["app"],
        "overlay": str(raw.get("overlay") or "").strip()[:200],
        "slotNumber": max(0, integer(raw.get("slotNumber"))) if showing else 0,
        "serverSlotId": str(raw.get("serverSlotId") or "").strip()[:200] if showing else "",
        "autoClose": seconds(raw.get("autoClose")) if showing else 0,
        "delay": max(0, min(30000, integer(raw.get("delay")))),
    }


def key_triggers(settings, app):
    """The triggers an Overlay key of 1.0.0 carried, as global triggers of control app `app`."""
    overlay, scene = str(settings.get("overlayId") or ""), str(settings.get("obsScene") or "").strip()
    found = []
    for event in EVENTS:
        target = settings.get(event + "Target") or overlay
        if settings.get(event + "Function") not in ("show", "hide") or not target:
            continue
        if (event in SCENE_EVENTS and not scene) or (event in UNO_EVENTS and not overlay):
            continue
        found.append(
            clean_trigger(
                {
                    "event": event,
                    "scene": scene,
                    "sourceApp": app,
                    "sourceOverlay": overlay,
                    "function": settings[event + "Function"],
                    "app": app,
                    "overlay": target,
                    "slotNumber": settings.get("slotNumber") if target == overlay else 0,
                    "serverSlotId": settings.get("serverSlotId") if target == overlay else "",
                    "autoClose": settings.get("autoClose") if target == overlay else 0,
                    "delay": settings.get(event + "Delay"),
                }
            )
        )
    return found


def merge_triggers(existing, new):
    """Existing triggers plus the new ones not already there (same event, target, slot, Auto Close and delay)."""
    merged = [t for t in (clean_trigger(raw) for raw in existing or []) if t]
    seen = {tuple(t[k] for k in IDENTITY) for t in merged}
    added = 0
    for trigger in new:
        identity = tuple(trigger[k] for k in IDENTITY)
        if identity not in seen:
            seen.add(identity)
            merged.append(trigger)
            added += 1
    return merged, added


def strip_legacy(settings):
    """Key settings without the fields that moved to the global settings or went away."""
    return {key: value for key, value in settings.items() if key not in LEGACY}


def group_delay(value):
    try:
        return max(-30.0, min(30.0, float(value or 0)))
    except (TypeError, ValueError):
        return 0.0


def clean_group(raw):
    raw = raw if isinstance(raw, dict) else {}
    members, seen = [], set()
    for member in raw.get("members") or []:
        if isinstance(member, dict) and member.get("app") and member.get("overlay"):
            pair = (str(member["app"])[:16], str(member["overlay"])[:200])
            if pair not in seen:
                seen.add(pair)
                members.append({"app": pair[0], "overlay": pair[1]})
    return {"delay": group_delay(raw.get("delay")), "members": members}
