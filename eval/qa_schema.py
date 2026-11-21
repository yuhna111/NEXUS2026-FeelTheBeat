"""Validator and Recall@k helpers for docs/qa_schema.md (TV3)."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
TODO_CLAUSE = "TODO_VERIFY_CLAUSE"

CATEGORIES = frozenset({
    "A_direct", "B_obsolete_trap", "C_multihop_spatial", "D_before_after",
    "E_procedure", "F_rumor",
})
ITEM_ROLES = frozenset({"trap", "control"})
ANSWER_TYPES = frozenset({
    "entity", "entity_list", "number", "date", "yes_no", "premise_rejection", "free_text",
})
DIFFICULTIES = frozenset({"easy", "medium", "hard"})
REQUIRED = (
    "id", "category", "item_role", "question", "reference_date", "gold_answer",
    "obsolete_answer", "evidence", "gold_clause_ids", "verified", "version",
)
EVIDENCE_KEYS = ("doc_id", "article", "clause", "clause_id", "citation", "in_corpus")

CLAUSE_ID_RE = re.compile(
    r"^(?P<doc>[A-Z]+(?:-\d+)+-[A-Z0-9]+)#D(?P<art>\d+[a-z]?)\.K(?P<cl>\d+[a-z]?)$"
)
CHUNK_ID_RE = re.compile(r"^(?P<doc>[^#]+)#Art(?P<art>\d+[a-z]?)\.(?P<cl>\d+[a-z]?)$")


def _is_str_list(x: Any) -> bool:
    return isinstance(x, list) and all(isinstance(i, str) for i in x)


def _is_iso_date(x: Any) -> bool:
    if not isinstance(x, str):
        return False
    try:
        date.fromisoformat(x)
    except ValueError:
        return False
    return True


def load_clause_ids(parsed_dir: Path) -> set[str]:
    ids: set[str] = set()
    for p in sorted(parsed_dir.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        for art in doc.get("articles", []):
            ids.update(c["id"] for c in art.get("clauses") or [] if c.get("id"))
    return ids


def clause_id_to_chunk_id(clause_id: str) -> str:
    """`<doc>#D1.K14` (data/parsed) → `<doc>#Art1.14` (rag/chunkers.legal_chunks)."""
    m = CLAUSE_ID_RE.match(clause_id)
    if not m:
        raise ValueError(f"not a clause id: {clause_id!r}")
    return f"{m['doc']}#Art{m['art']}.{m['cl']}"


def chunk_id_to_clause_id(chunk_id: str) -> str | None:
    m = CHUNK_ID_RE.match(chunk_id)
    return f"{m['doc']}#D{m['art']}.K{m['cl']}" if m else None


def recall_gold_ids(rec: Mapping[str, Any]) -> set[str] | None:
    """Gold clause ids for Recall@k, or None when the record must be excluded.

    Records without `gold_clause_ids` (pilot-0.1, e.g. pilot_80.jsonl) fall back to
    evidence clause ids flagged `in_corpus`.
    """
    if "gold_clause_ids" in rec:
        ids = [i for i in rec.get("gold_clause_ids") or [] if isinstance(i, str)]
        if not ids or TODO_CLAUSE in ids:
            return None
        return set(ids)
    ids = {e["clause_id"] for e in rec.get("evidence") or []
           if e.get("clause_id") and e.get("in_corpus")}
    return ids or None


def _validate_evidence(evidence: Any, errors: list[str]) -> set[str]:
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence: must be a non-empty list")
        return set()
    cids: set[str] = set()
    for i, e in enumerate(evidence):
        if not isinstance(e, dict):
            errors.append(f"evidence[{i}]: must be an object")
            continue
        missing = [k for k in EVIDENCE_KEYS if k not in e]
        if missing:
            errors.append(f"evidence[{i}]: missing {missing}")
        if not isinstance(e.get("citation"), str) or not e.get("citation", "").strip():
            errors.append(f"evidence[{i}].citation: non-empty str required")
        if not isinstance(e.get("in_corpus"), bool):
            errors.append(f"evidence[{i}].in_corpus: bool required")
        cid = e.get("clause_id")
        if cid is None:
            if e.get("in_corpus"):
                errors.append(f"evidence[{i}]: in_corpus=true requires clause_id")
            continue
        m = CLAUSE_ID_RE.match(cid) if isinstance(cid, str) else None
        if not m:
            errors.append(f"evidence[{i}].clause_id: bad format {cid!r}")
            continue
        if e.get("doc_id") != m["doc"]:
            errors.append(f"evidence[{i}]: doc_id does not match clause_id")
        if e.get("article") != m["art"] or e.get("clause") != m["cl"]:
            errors.append(f"evidence[{i}]: article/clause do not match clause_id")
        cids.add(cid)
    return cids


def validate_record(rec: Mapping[str, Any], known_clause_ids: set[str] | None = None) -> list[str]:
    errors: list[str] = [f"missing field: {k}" for k in REQUIRED if k not in rec]
    if errors:
        return errors

    if not isinstance(rec["id"], str) or not rec["id"].strip():
        errors.append("id: non-empty str required")
    if rec["category"] not in CATEGORIES:
        errors.append(f"category: {rec['category']!r} not in enum")
    if rec["item_role"] not in ITEM_ROLES:
        errors.append(f"item_role: {rec['item_role']!r} not in enum")
    if not isinstance(rec["question"], str) or not rec["question"].strip():
        errors.append("question: non-empty str required")
    if not _is_iso_date(rec["reference_date"]):
        errors.append("reference_date: ISO date YYYY-MM-DD required")
    if not isinstance(rec["verified"], bool):
        errors.append("verified: bool required")
    if not isinstance(rec["version"], str) or not rec["version"].strip():
        errors.append("version: non-empty str required")

    gold = rec["gold_answer"]
    if not isinstance(gold, dict):
        errors.append("gold_answer: object required")
    else:
        if not isinstance(gold.get("text"), str) or not gold.get("text", "").strip():
            errors.append("gold_answer.text: non-empty str required")
        if not _is_str_list(gold.get("aliases")):
            errors.append("gold_answer.aliases: list[str] required")
        if gold.get("answer_type") not in ANSWER_TYPES:
            errors.append(f"gold_answer.answer_type: {gold.get('answer_type')!r} not in enum")
        if "entities" in gold and not _is_str_list(gold["entities"]):
            errors.append("gold_answer.entities: list[str] required")

    obs = rec["obsolete_answer"]
    if not isinstance(obs, dict) or not isinstance(obs.get("text"), str) \
            or not _is_str_list(obs.get("obsolete_entities")):
        errors.append("obsolete_answer: {text: str, obsolete_entities: list[str]} required")
    elif rec["item_role"] == "control" and (obs["text"] or obs["obsolete_entities"]):
        errors.append("obsolete_answer: must be empty for item_role=control")

    evidence_cids = _validate_evidence(rec["evidence"], errors)

    gids = rec["gold_clause_ids"]
    if not _is_str_list(gids) or not gids:
        errors.append("gold_clause_ids: non-empty list[str] required")
    elif TODO_CLAUSE in gids:
        if gids != [TODO_CLAUSE]:
            errors.append(f"gold_clause_ids: {TODO_CLAUSE} must be the only element")
    else:
        if len(set(gids)) != len(gids):
            errors.append("gold_clause_ids: duplicates")
        for g in gids:
            if not CLAUSE_ID_RE.match(g):
                errors.append(f"gold_clause_ids: bad format {g!r}")
            elif g not in evidence_cids:
                errors.append(f"gold_clause_ids: {g} not listed in evidence")
            elif known_clause_ids is not None and g not in known_clause_ids:
                errors.append(f"gold_clause_ids: {g} not found in data/parsed")

    if rec.get("province_is_control") not in (True, False, None):
        errors.append("province_is_control: bool | null required")
    hops = rec.get("hops")
    if hops is not None and (not isinstance(hops, int) or isinstance(hops, bool) or hops < 1):
        errors.append("hops: int >= 1 | null required")
    if rec.get("difficulty") not in DIFFICULTIES | {None}:
        errors.append(f"difficulty: {rec.get('difficulty')!r} not in enum")
    if "annotator" in rec and not _is_str_list(rec["annotator"]):
        errors.append("annotator: list[str] required")
    return errors


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate_records(records: list[Mapping[str, Any]],
                     known_clause_ids: set[str] | None = None) -> dict[str, list[str]]:
    report: dict[str, list[str]] = {}
    seen: set[str] = set()
    for n, rec in enumerate(records, start=1):
        key = str(rec.get("id") or f"<line {n}>")
        errs = validate_record(rec, known_clause_ids)
        if key in seen:
            errs.append("id: duplicate")
        seen.add(key)
        if errs:
            report[key] = errs
    return report


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Validate a benchmark JSONL against docs/qa_schema.md")
    ap.add_argument("jsonl", type=Path)
    ap.add_argument("--parsed", type=Path, default=Path("data/parsed"))
    args = ap.parse_args()
    known = load_clause_ids(args.parsed) if args.parsed.is_dir() else set()
    recs = read_jsonl(args.jsonl)
    bad = validate_records(recs, known or None)
    for qid, errs in bad.items():
        print(f"{qid}: " + "; ".join(errs))
    todo = [r["id"] for r in recs if recall_gold_ids(r) is None]
    print(f"{len(recs)} records, {len(bad)} invalid, {len(recs) - len(todo)} Recall@k-ready")
    raise SystemExit(1 if bad else 0)
