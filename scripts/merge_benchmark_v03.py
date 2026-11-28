"""Đặt `verified = true` cho `tv1_v0.3.jsonl` (sau khi TV3 kiểm lại 15 câu sửa) và gộp `benchmark_v0.3.jsonl` (308 câu).

Quy tắc (phân công Tuần 3):
  - Chỉ đặt `verified = true` khi người thứ hai đã kiểm đối chiếu với văn bản gốc.
  - `tv1_v0.3.jsonl` (168 câu): TV1 soạn, TV3 kiểm chéo (`docs/tv3_review_tv1_v03.md`),
    TV1 sửa 15 câu (`docs/tv1_response_review_v03.md`), TV3 kiểm lại 28/11/2026 → đặt `verified = true`.
  - `tv3_v0.3.jsonl` (60 câu): giữ `verified = false` cho tới khi TV1 xác nhận kiểm chéo xong.
  - `pilot_80_v0.3.jsonl` (80 câu): giữ nguyên cờ `verified` hiện có (`false`).

Chạy:
  python scripts/merge_benchmark_v03.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.qa_schema import load_clause_ids, read_jsonl, recall_gold_ids, validate_records

PILOT_PATH = ROOT / "data/benchmark/pilot_80_v0.3.jsonl"
TV1_PATH = ROOT / "data/benchmark/tv1_v0.3.jsonl"
TV3_PATH = ROOT / "data/benchmark/tv3_v0.3.jsonl"
OUT_PATH = ROOT / "data/benchmark/benchmark_v0.3.jsonl"


def write_jsonl(path: Path, recs: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    known = load_clause_ids(ROOT / "data/parsed")

    # 1. Mark tv1_v0.3.jsonl as verified=True after TV3 re-checked all 15 fixes on 28/11/2026
    tv1_recs = read_jsonl(TV1_PATH)
    note_tag = "TV3 đã kiểm chéo toàn bộ 168 câu (27/11) và xác nhận 15 câu sửa (28/11/2026)."
    for r in tv1_recs:
        r["verified"] = True
        ann = list(r.get("annotator") or [])
        if "TV3" not in ann:
            ann.append("TV3")
        r["annotator"] = ann
        note = (r.get("verification_note") or "").strip()
        if note_tag not in note:
            r["verification_note"] = f"{note} {note_tag}".strip()
    write_jsonl(TV1_PATH, tv1_recs)

    # 2. Merge pilot_80_v0.3 (80) + tv1_v0.3 (168) + tv3_v0.3 (60) -> benchmark_v0.3.jsonl (308)
    pilot_recs = read_jsonl(PILOT_PATH)
    tv3_recs = read_jsonl(TV3_PATH)
    merged = pilot_recs + tv1_recs + tv3_recs

    bad = validate_records(merged, known)
    if bad:
        for qid, errs in bad.items():
            print(f"INVALID {qid}: {'; '.join(errs)}")
        return 1

    write_jsonl(OUT_PATH, merged)

    cats = collections.Counter(r["category"] for r in merged)
    roles = collections.Counter(r["item_role"] for r in merged)
    n_ver = sum(r["verified"] for r in merged)
    n_rec = sum(recall_gold_ids(r) is not None for r in merged)
    print(f"Wrote {len(merged)} records -> {OUT_PATH} (verified={n_ver}/{len(merged)}, Recall@k-ready={n_rec}/{len(merged)})")
    print("  by category:", dict(sorted(cats.items())))
    print("  by item_role:", dict(sorted(roles.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
