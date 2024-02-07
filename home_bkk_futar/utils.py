"""Miscellaneous utilities for home-bkk-futar"""

from typing import Optional


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
