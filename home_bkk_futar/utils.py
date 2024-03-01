"""Miscellaneous utilities for home-bkk-futar"""

import datetime as dt
import math
from colorsys import hls_to_rgb
from typing import Optional
from zoneinfo import ZoneInfo

# Color will make this many hue loops in a day. Hue is the primary color component in HLS.
# To make it predictable by the hour, set a multiple of 24, otherwise set some fractional number.
HUE_CYCLES_PER_DAY = 3.3333 * 24

# Color will make this many saturation loops in a day, plus the saturation bounds can be set here.
# Low saturation is grey-ish, high saturation is "strong" color.
SATURATION_CYCLES_PER_DAY = 0.5 * 24
SATURATION_MIN = 0.1
SATURATION_MAX = 0.9

# Color will be lightest at local noon and darkest at local midnight.
# Bounds and local time zone can be set here.
LIGHTNESS_MIN = 0.25
LIGHTNESS_MAX = 0.75
LOCAL_TZ = "Europe/Budapest"


def get_rgb_color(now: dt.datetime) -> tuple[int, int, int]:
    """
    Calculate a smoothly cycling RGB (0..255) color based on given datetime:
    - We set hue to a cycle with given frequency (think of it as cycling rainbow colors).
    - Saturation has its own cycle with given frequency (think of it as grey-ish vs strong color).
    - Lightness cycles according to local daylight cycle. It could be improved to use sun altitude.
    """
    now_timestamp = now.timestamp()
    local_now = now.astimezone(ZoneInfo(LOCAL_TZ))
    local_frac = (3600 * local_now.hour + 60 * local_now.minute + local_now.second) / 86400

    hue = now_timestamp / (86400 / HUE_CYCLES_PER_DAY) % 1

    saturation = SATURATION_MIN + (SATURATION_MAX - SATURATION_MIN) * 0.5 * (
        1 + math.sin(now_timestamp / (86400 / SATURATION_CYCLES_PER_DAY) * 2 * math.pi)
    )
    lightness = LIGHTNESS_MIN + (LIGHTNESS_MAX - LIGHTNESS_MIN) * 0.5 * (
        1 - math.cos(local_frac * 2 * math.pi)
    )
    # For some reason colorsys implements lightness the opposite way around
    return tuple(int(255 * value) for value in hls_to_rgb(hue, 1 - lightness, saturation))


def sign_by_stop_from_string(encoded: Optional[str], sep: str, pair_sep: str) -> dict[str, str]:
    """Deserialize the stop-id - stop-sign pairs from a string"""
    if not encoded:
        return {}
    sign_by_stop = {}
    for stop_and_sign in encoded.split(sep):
        pair = stop_and_sign.split(pair_sep)
        if len(pair) != 2:
            raise ValueError(
                f"The following item of stops and signs is wrongly encoded: {stop_and_sign}"
            )
        sign_by_stop[pair[0]] = pair[1]
    return sign_by_stop


def equal_divide(n: int, k: int) -> list[int]:
    """Divide n into k parts so that they are as equal as possible, e.g. (8, 3) -> [3, 3, 2]"""
    return [n // k + (1 if i < n % k else 0) for i in range(k)]
