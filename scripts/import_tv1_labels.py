"""Nhập nhãn TV1 đợt 2 (70 câu) từ file Excel đã gán, gộp với đợt 1 (20 câu).

File gán nhãn: TV1_gan_nhan_doc_lap_dot2_70cau.xlsx (sheet Gan_nhan, cột Mã, Nhãn, Ghi chú),
khoá mã -> câu/mô hình: outputs/pilot_manual/tv1_batch2_key.csv.
Đầu ra: outputs/pilot_manual/tv1_labels_90.jsonl, dùng với
  python scripts/kappa_tv1_tv3.py --tv1 outputs/pilot_manual/tv1_labels_90.jsonl

Usage: python scripts/import_tv1_labels.py <file.xlsx>
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

PILOT = Path("outputs/pilot_manual")
LABELS = {"CORRECT_CURRENT", "STALE", "BLENDED", "OTHER_ERROR", "ABSTAIN"}


def main() -> None:
    xlsx = Path(sys.argv[1])
    key = {r["code"]: r for r in csv.DictReader(open(PILOT / "tv1_batch2_key.csv", encoding="utf-8"))}
    ws = load_workbook(xlsx, data_only=True)["Gan_nhan"]
    head = [c.value for c in ws[1]]
    ci, li, ni = head.index("Mã"), head.index("Nhãn"), head.index("Ghi chú")
    new, missing = [], []
    for row in ws.iter_rows(min_row=2, values_only=True):
        code = row[ci]
        if not code:
            continue
        label = (row[li] or "").strip()
        if label not in LABELS:
            missing.append(code)
            continue
        k = key[code]
        new.append({"question_id": k["question_id"], "model_id": k["model_id"], "label": label,
                    "annotator": "TV1", "note": (row[ni] or None), "batch": 2})
    if missing:
        sys.exit(f"Chưa gán hoặc nhãn không hợp lệ ở {len(missing)} dòng: {', '.join(missing)}")
    if len(new) != len(key):
        sys.exit(f"Có {len(new)} nhãn, cần {len(key)}")
    old = [dict(json.loads(l), batch=1) for l in open(PILOT / "tv1_recheck20_labels.jsonl", encoding="utf-8")]
    seen = {(d["question_id"], d["model_id"]) for d in old}
    assert not seen & {(d["question_id"], d["model_id"]) for d in new}
    out = PILOT / "tv1_labels_90.jsonl"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for d in old + new:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"{len(old)} + {len(new)} = {len(old) + len(new)} nhãn -> {out}")


if __name__ == "__main__":
    main()
