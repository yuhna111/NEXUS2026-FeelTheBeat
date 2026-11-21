"""Merge the two pilot question sets into one JSONL in qa_schema v1.0 (docs/qa_schema.md).

Inputs
- TV1 set (toan50): `pilot_80.jsonl` from branch feat/data, format pilot-0.1. Only its
  `P-T-*` records are used; its `P-V-*` records are an older copy of TV3's set.
- TV3 set (vinh30): `data/benchmark/pilot_30_vinh.jsonl`, already v1.0 (pilot-0.2).

The only change made to TV1 records is the upgrade to v1.0:
- `gold_clause_ids` is derived with the schema's own pilot-0.1 rule
  (`eval.qa_schema.recall_gold_ids`: evidence clauses with `in_corpus = true`), or
  `["TODO_VERIFY_CLAUSE"]` when there is none. The derived ids are flagged in
  `verification_note` because evidence may also list partly-supporting clauses,
  which v1.0 keeps out of `gold_clause_ids`; TV1 has to confirm them.
- `hops` is added as null, `version` becomes pilot-0.2.
Question text, answers and evidence are not touched.

    python scripts/merge_pilot_sets.py --toan pilot_80.jsonl \
        --vinh data/benchmark/pilot_30_vinh.jsonl --out data/benchmark/pilot_80_v0.2.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.qa_schema import (  # noqa: E402
    TODO_CLAUSE, load_clause_ids, read_jsonl, recall_gold_ids, validate_records,
)

VERSION = "pilot-0.2"
DERIVED_NOTE = ("gold_clause_ids suy tự động từ evidence in_corpus khi gộp sang v1.0; "
                "TV1 cần xác nhận khoản nào mang đáp án.")

# v1.0 field order (docs/qa_schema.md §4), so both sets read the same way.
FIELD_ORDER = [
    "id", "source_set", "source_id", "category", "subtype", "item_role", "question",
    "reference_date", "gold_answer", "obsolete_answer", "evidence", "gold_clause_ids",
    "source_url", "province_new", "province_is_control", "hops", "difficulty", "annotator",
    "verified", "verification_note", "duplicate_of", "version",
]


def upgrade_toan(rec: dict) -> dict:
    out = dict(rec)
    gold = recall_gold_ids(rec)
    out["gold_clause_ids"] = sorted(gold) if gold else [TODO_CLAUSE]
    if gold:
        note = out.get("verification_note") or ""
        out["verification_note"] = f"{note} {DERIVED_NOTE}".strip()
    out.setdefault("hops", None)
    out["version"] = VERSION
    return out


def ordered(rec: dict) -> dict:
    keys = [k for k in FIELD_ORDER if k in rec] + [k for k in rec if k not in FIELD_ORDER]
    return {k: rec[k] for k in keys}


def merge(toan: list[dict], vinh: list[dict]) -> list[dict]:
    toan_only = [upgrade_toan(r) for r in toan if r["id"].startswith("P-T-")]
    return [ordered(r) for r in toan_only + vinh]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toan", type=Path, required=True, help="pilot_80.jsonl (feat/data)")
    ap.add_argument("--vinh", type=Path, default=Path("data/benchmark/pilot_30_vinh.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("data/benchmark/pilot_80_v0.2.jsonl"))
    ap.add_argument("--parsed", type=Path, default=Path("data/parsed"))
    args = ap.parse_args()

    records = merge(read_jsonl(args.toan), read_jsonl(args.vinh))
    known = load_clause_ids(args.parsed) if args.parsed.is_dir() else set()
    bad = validate_records(records, known or None)
    for qid, errs in bad.items():
        print(f"{qid}: " + "; ".join(errs), file=sys.stderr)
    if bad:
        raise SystemExit(f"{len(bad)} invalid records, nothing written")
    if not known:
        print("warning: no data/parsed clauses found, gold_clause_ids not checked against corpus",
              file=sys.stderr)

    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ready = sum(recall_gold_ids(r) is not None for r in records)
    print(f"wrote {len(records)} records to {args.out} ({ready} Recall@k-ready)")


if __name__ == "__main__":
    main()
