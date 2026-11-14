"""Vietnamese administrative-name normalizer (Week 2, TV3).

lowercase → Unicode NFC → strip unit prefixes → alias map.
"""
from __future__ import annotations

import re
import unicodedata

# Longest first so "thành phố" wins over shorter overlaps.
PREFIXES = sorted(
    ["thành phố", "tp", "tỉnh", "phường", "xã", "đặc khu", "thị trấn", "thị xã", "quận", "huyện"],
    key=len, reverse=True,
)
_PREFIX_RE = re.compile(r"^(?:" + "|".join(re.escape(p) for p in PREFIXES) + r")\s+")
_DASH_RE = re.compile(r"\s*[-–—]\s*")
_PUNCT_RE = re.compile(r"[\"'“”‘’.,;:!?()\[\]]")
_SPACE_RE = re.compile(r"\s+")

# Extend from data/processed/entity_map_63_34.csv
ALIASES: dict[str, str] = {
    "hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "sài gòn": "hồ chí minh",
    "brvt": "bà rịa – vũng tàu",
}


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _DASH_RE.sub(" – ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    prev = None
    while prev != s:  # strip stacked prefixes, e.g. "tp thành phố ..."
        prev = s
        s = _PREFIX_RE.sub("", s).strip()
    return ALIASES.get(s, s)
