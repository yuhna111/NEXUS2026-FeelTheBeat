"""Export the manual pilot runs (sheet "Kết quả chạy") to TV2's prediction format.

Input : data/pilot/Pilot_30_cau_VN-Admin2025.xlsx
Output: outputs/pilot_manual/<model_id>.jsonl         (model_id, config, question_id, prompt,
                                                      context_ids, output, timestamp)
        outputs/pilot_manual/<model_id>_labels.jsonl  (question_id, label) — human labels

Usage:  python scripts/export_pilot_runs.py
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import openpyxl

XLSX = Path("data/pilot/Pilot_30_cau_VN-Admin2025.xlsx")
OUT = Path("outputs/pilot_manual")
RUN_DATE = "2026-11-14"
LABELS = {"CORRECT_CURRENT", "STALE", "BLENDED", "OTHER_ERROR", "ABSTAIN"}
MODEL_COLUMNS = (5, 8, 11)


def nfc(x: object) -> str:
    return unicodedata.normalize("NFC", str(x or "")).strip()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", nfc(name).lower()).strip("-")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=XLSX)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    wb = openpyxl.load_workbook(args.xlsx, read_only=True)
    codes = [nfc(r[0]) for r in wb["Bộ câu hỏi"].iter_rows(min_row=2, values_only=True) if r[0]]
    rows = list(wb["Kết quả chạy"].iter_rows(values_only=True))
    header, data = rows[0], rows[2:2 + len(codes)]

    args.out.mkdir(parents=True, exist_ok=True)
    for col in MODEL_COLUMNS:
        model_id = slug(header[col])
        preds, labels = [], []
        for code, row in zip(codes, data, strict=True):
            qid, output, label = f"P-V-{code}", nfc(row[col]), nfc(row[col + 1]).upper()
            if output:
                preds.append({"model_id": model_id, "config": "C0", "question_id": qid, "prompt": "",
                              "context_ids": [], "output": output, "timestamp": RUN_DATE})
            if label in LABELS:
                labels.append({"question_id": qid, "label": label})
        for path, recs in ((args.out / f"{model_id}.jsonl", preds),
                           (args.out / f"{model_id}_labels.jsonl", labels)):
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
        print(f"{model_id}: {len(preds)} predictions, {len(labels)} labels → {args.out}")


if __name__ == "__main__":
    main()
