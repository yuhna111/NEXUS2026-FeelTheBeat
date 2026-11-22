"""Vietnamese administrative-name normalizer (Week 2, TV3).

lowercase → Unicode NFC → strip unit prefixes → alias map.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

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


ALIASES_CSV = Path(__file__).with_name("aliases.csv")


def _base(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _DASH_RE.sub(" – ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    prev = None
    while prev != s:  # strip stacked prefixes, e.g. "tp thành phố ..."
        prev = s
        s = _PREFIX_RE.sub("", s).strip()
    return s


def load_aliases(path: Path = ALIASES_CSV) -> dict[str, str]:
    """`alias,canonical` rows (eval/aliases.csv, TV1 + TV3) keyed by their normalized form."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            alias, canon = (row.get("alias") or "").strip(), (row.get("canonical") or "").strip()
            if alias and canon:
                out[_base(alias)] = _base(canon)
    return out


ALIASES.update({k: v for k, v in load_aliases().items() if k not in ALIASES})


def normalize(s: str) -> str:
    s = _base(s)
    return ALIASES.get(s, s)
