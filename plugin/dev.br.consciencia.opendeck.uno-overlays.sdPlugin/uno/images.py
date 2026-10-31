"""Key images (144 px SVG): Material Symbols glyphs, iOS-style badge, captions and the Display number."""

import base64
import textwrap
from html import escape

from uno.glyphs import PATHS
from uno.values import scalar

__all__ = ["BADGE_RED", "RED", "WHITE", "WRAP_UP", "caption", "icon_image", "number_image", "step_image"]

WHITE, RED = "#FFFFFF", "#FF0000"
BADGE_RED = "#FF4245"  # Apple HIG system color Red, iOS default (dark): R255 G66 B69
WRAP_UP = ("#22C55D", "#F59E0C", "#EF4444")  # stagetimer progress bar: normal, yellow warning, red warning


def icon_image(key, color=WHITE, badge=None, caption=(), background="#000"):
    """Material Symbols glyph on a 144 px key; optional iOS-style badge and caption lines."""
    size, top = (60, 10) if caption else (100, 22)
    glyph = (
        f'<path transform="translate({(144 - size) / 2} {top + size}) scale({size / 960})" '
        f'fill="{color}" d="{PATHS[key]}"/>'
    )
    return key_image(glyph, color, badge, caption, background)


def step_image(text, color=WHITE, badge=None):
    """Numeric Fields: what one press adds ("+3", "−5") in place of the glyph, tally colors kept.

    Material Symbols has glyphs only for ±1 and ±2 (exposure_plus_1 … exposure_neg_2), so the step is
    text, drawn like number_image: bold sans-serif that shrinks with the number of characters."""
    font = max(24, min(84, int(260 / max(1, len(text)))))
    sign = (
        f'<text x="72" y="76" text-anchor="middle" dominant-baseline="middle" fill="{color}" '
        f'font-family="sans-serif" font-weight="bold" font-size="{font}">{escape(text)}</text>'
    )
    return key_image(sign, color, badge)


def key_image(drawing, color=WHITE, badge=None, caption=(), background="#000"):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" viewBox="0 0 144 144">',
        f'<rect width="144" height="144" fill="{background}"/>',
        drawing,
    ]
    big = len(caption) == 1 and len(caption[0]) <= 6  # a single value reads larger
    for i, line in enumerate(caption):
        parts.append(
            f'<text x="72" y="{112 if big else 96 + i * 30}" text-anchor="middle" fill="{color}" '
            f'font-family="sans-serif" font-weight="bold" font-size="{40 if big else 26}">{escape(line)}</text>'
        )
    if badge is not None:
        # A small filled oval containing a number, at the icon's top-right corner.
        text = str(badge)
        width = max(44, 18 + 17 * len(text))
        parts.append(
            f'<rect x="{140 - width}" y="4" width="{width}" height="44" rx="22" fill="{BADGE_RED}"/>'
            f'<text x="{140 - width / 2}" y="27" text-anchor="middle" dominant-baseline="middle" '
            f'fill="#FFFFFF" font-family="sans-serif" font-weight="bold" font-size="30">{escape(text)}</text>'
        )
    parts.append("</svg>")
    return "data:image/svg+xml;base64," + base64.b64encode("".join(parts).encode()).decode()


def caption(text, width=10):
    """Two short lines for a 144 px key."""
    lines = textwrap.wrap(" ".join(str(text).split()), width, break_long_words=False, break_on_hyphens=False)
    return [line[:width] for line in lines][:2] or [""]


def number_image(value):
    text = scalar(value) or "0"
    font = max(12, min(72, int(220 / max(1, len(text)))))
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" viewBox="0 0 144 144">'
        '<rect width="144" height="144" rx="12" fill="#0d1117"/>'
        f'<text x="72" y="76" text-anchor="middle" dominant-baseline="middle" '
        f'fill="white" font-family="sans-serif" font-weight="bold" font-size="{font}">'
        f"{escape(text)}</text></svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
