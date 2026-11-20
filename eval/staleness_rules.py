"""Rule-based staleness detector (Week 3, TV3).

Runs before the LLM judge; the judge only handles cases the rules cannot decide.
"""
from __future__ import annotations

import re
import unicodedata

from eval.normalize import normalize

# Phrases showing the answer is DESCRIBING the change rather than asserting the old
# unit as current. When one is present the rules cannot decide → LLM judge.
# "cũ" is NOT listed here: on its own it is too common ("trụ sở cũ", "đường cũ").
# It only counts right after an obsolete entity ("huyện Gia Lâm cũ", "Gia Lâm (cũ)"),
# see _old_suffix().
CHANGE_MARKERS = [
    "không còn", "trước đây", "trước kia", "trước ngày", "trước khi", "trước 01/07",
    "từng là", "từng thuộc", "đã sáp nhập", "đã hợp nhất", "đã được sáp nhập",
    "đã được hợp nhất", "đã được sắp xếp", "đã sắp xếp", "đã bãi bỏ", "đã bị bãi bỏ",
    "đã bỏ", "đã giải thể", "nay thuộc", "nay là", "hiện thuộc", "hiện nay thuộc",
]
_MARKER_RE = re.compile(
    r"(?<!\w)(?:" + "|".join(re.escape(m) for m in CHANGE_MARKERS) + r")(?!\w)"
)


def has_change_marker(answer: str) -> bool:
    return bool(_MARKER_RE.search(unicodedata.normalize("NFC", answer).lower()))


def _old_suffix(answer: str, hits: list[str]) -> bool:
    """True when an obsolete entity is directly followed by "cũ", e.g. "Gia Lâm (cũ)"."""
    a = normalize(answer)  # strips punctuation, so "(cũ)" becomes " cũ "
    return any(
        re.search(r"(?<!\w)" + re.escape(normalize(e)) + r" cũ(?!\w)", a) for e in hits
    )


def mentions_obsolete(answer: str, obsolete_entities: list[str]) -> list[str]:
    """Return obsolete entities that appear in the answer (normalized substring match)."""
    a = normalize(answer)
    return [e for e in obsolete_entities if normalize(e) and normalize(e) in a]


def rule_verdict(answer: str, obsolete_entities: list[str]) -> str | None:
    """Return 'STALE' / 'NOT_STALE', or None when undecidable → send to LLM judge.

    - no obsolete entity mentioned                       → NOT_STALE
    - obsolete entity mentioned, no change marker        → STALE
    - obsolete entity mentioned alongside a change marker, or written as
      "<entity> cũ"                                       → None (judge decides
      between describing the change, BLENDED and STALE)
    """
    hits = mentions_obsolete(answer, obsolete_entities)
    if not hits:
        return "NOT_STALE"
    if has_change_marker(answer) or _old_suffix(answer, hits):
        return None
    return "STALE"
