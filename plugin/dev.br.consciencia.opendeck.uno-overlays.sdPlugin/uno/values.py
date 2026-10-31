"""Field values: numbers, text templates and clock text, keeping each UNO field's JSON type.

Content semantics retained from the supplied 5.0.1-fixed6 runtime (scalar, merge, increment).
"""

import re
from copy import deepcopy
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

__all__ = [
    "composite",
    "format_clock",
    "increment",
    "integer",
    "merge",
    "number",
    "parse_hms",
    "percent",
    "render",
    "scalar",
    "seconds",
    "typed",
    "visible",
]

TOKEN = re.compile(r"\{([^{}]+)\}")


def scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, Decimal)):
        return format(Decimal(str(value)).normalize(), "f")
    return str(value)


def number(raw):
    """Field value as Decimal; text that is not a number counts as 0."""
    try:
        value = Decimal(scalar(raw).strip().replace(",", ".") or "0")
        return value if value.is_finite() else Decimal(0)
    except InvalidOperation:
        return Decimal(0)


def increment(raw, delta):
    result = number(raw) + Decimal(str(delta))
    if isinstance(raw, str):
        return format(result.normalize(), "f")
    return int(result) if result == result.to_integral() else float(result)


def percent(part, whole):
    """Whole percent, half up; 0 when there is no total."""
    return int((number(part) * 100 / number(whole)).quantize(Decimal(1), ROUND_HALF_UP)) if number(whole) else 0


def merge(base, patch):
    if not isinstance(patch, dict):
        return deepcopy(patch)
    result = deepcopy(base) if isinstance(base, dict) else {}
    for key, value in patch.items():
        result[key] = merge(result.get(key), value)
    return result


def typed(value, current):
    """Macro values are typed text; keep the field's current JSON type."""
    if isinstance(current, bool):
        return str(value).strip().lower() in ("true", "1", "yes")
    if isinstance(current, (int, float)):
        try:
            parsed = float(value)
            return int(parsed) if parsed.is_integer() else parsed
        except ValueError:
            pass
    return value


def integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def seconds(value):
    return max(0, min(120, integer(value)))


def visible(overlay):
    return str(overlay.get("visible", False)).lower() in ("true", "1")


def composite(value):
    parts = str(value or "").split("::", 1)
    return parts if len(parts) == 2 else ("", "")


def render(template, lookup):
    """vMix Format: {0} is the value ('Name: {0}'). Other {names} come from lookup; unknown ones stay as typed."""

    def fill(match):
        value = lookup(match.group(1))
        return match.group(0) if value is None else scalar(value)

    return TOKEN.sub(fill, str(template))


def parse_hms(text):
    """hh:mm:ss, mm:ss or ss (vMix SetCountdown value) in seconds; bad text is 0."""
    try:
        seconds = 0.0
        for part in str(text or "0").strip().split(":"):
            seconds = seconds * 60 + float(part)
        return seconds
    except ValueError:
        return 0.0


def format_clock(seconds, fmt="mm:ss", prefix="-"):
    """stagetimer formats: 230:59 (mmm:ss), 41:30:59 (hhh:mm:ss), 92 (seconds only); overtime -0:01 / +0:01."""
    sign, s = (prefix, int(-seconds)) if seconds < 0 else ("", int(seconds))
    minutes, s = divmod(s, 60)
    if fmt == "hh:mm:ss":
        return f"{sign}{minutes // 60}:{minutes % 60:02d}:{s:02d}"
    return f"{sign}{minutes * 60 + s}" if fmt == "sss" else f"{sign}{minutes}:{s:02d}"
