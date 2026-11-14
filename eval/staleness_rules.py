"""Rule-based staleness detector (Week 3, TV3).

Runs before the LLM judge; the judge only handles cases the rules cannot decide.
"""
from __future__ import annotations

from eval.normalize import normalize


def mentions_obsolete(answer: str, obsolete_entities: list[str]) -> list[str]:
    """Return obsolete entities that appear in the answer (normalized substring match)."""
    a = normalize(answer)
    return [e for e in obsolete_entities if normalize(e) and normalize(e) in a]


def rule_verdict(answer: str, obsolete_entities: list[str]) -> str | None:
    """Return 'STALE' / 'NOT_STALE', or None when undecidable → send to LLM judge.

    TODO(TV3): handle negation ("đã không còn", "trước đây là", "đã sáp nhập")
    so that mentioning an old unit while describing the change is not STALE.
    """
    hits = mentions_obsolete(answer, obsolete_entities)
    if not hits:
        return "NOT_STALE"
    return None
