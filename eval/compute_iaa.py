"""Inter-annotator agreement (Cohen's kappa) between two independent pilot annotations.

Accepted inputs (each annotator: one file):
  .xlsx  copy of data/pilot/Pilot_30_cau_VN-Admin2025.xlsx with sheet "Kết quả chạy" filled in
  .jsonl one object per line: {"question_id" | "id", "model_id"?, "label", "note"?, "question"?, "output"?}
  .csv   same columns as JSONL

An item is (question id, model id); the pilot has 30 questions × 3 models = 90 items.

Usage:
    python -m eval.compute_iaa vinh.xlsx toan.xlsx
    python -m eval.compute_iaa vinh_labels.jsonl toan_labels.jsonl \
        --bench data/benchmark/pilot_30_vinh.jsonl --predictions outputs/pilot_manual/*.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eval.metrics import LABELS, cohen_kappa

DEFAULT_OUT = Path("eval/pilot_disagreements.csv")
EXPECTED_ITEMS = 90
KAPPA_TARGET = 0.75
QUESTION_SHEET = "Bộ câu hỏi"
RESULT_SHEET = "Kết quả chạy"
QUESTION_PREFIX = "P-V-"
CRITERIA: dict[str, frozenset[str]] = {
    "stale (STALE vs rest)": frozenset({"STALE"}),
    "stale+ (STALE|BLENDED vs rest)": frozenset({"STALE", "BLENDED"}),
    "correct (CORRECT_CURRENT vs rest)": frozenset({"CORRECT_CURRENT"}),
}


def _nfc(x: Any) -> str:
    return unicodedata.normalize("NFC", "" if x is None else str(x)).strip()


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _nfc(name).lower()).strip("-")


def _qid(raw: str) -> str:
    q = _nfc(raw)
    return f"{QUESTION_PREFIX}{q}" if re.fullmatch(r"[A-Z]\d{2}", q) else q


def item_key(question_id: str, model_id: str = "") -> str:
    return f"{_qid(question_id)}::{slug(model_id)}" if model_id else _qid(question_id)


@dataclass
class Item:
    question_id: str
    model_id: str
    label: str
    note: str = ""
    question: str = ""
    output: str = ""

    @property
    def key(self) -> str:
        return item_key(self.question_id, self.model_id)


@dataclass
class Annotation:
    path: Path
    items: dict[str, Item] = field(default_factory=dict)
    unlabeled: list[str] = field(default_factory=list)
    invalid: dict[str, str] = field(default_factory=dict)
    duplicates: list[str] = field(default_factory=list)

    def add(self, item: Item) -> None:
        label = _nfc(item.label).upper()
        if not label:
            self.unlabeled.append(item.key)
            return
        if label not in LABELS:
            self.invalid[item.key] = label
        if item.key in self.items:
            self.duplicates.append(item.key)
        item.label = label
        self.items[item.key] = item


def _read_xlsx(path: Path, ann: Annotation) -> None:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if RESULT_SHEET not in wb.sheetnames or QUESTION_SHEET not in wb.sheetnames:
        raise ValueError(f"{path}: needs sheets '{QUESTION_SHEET}' and '{RESULT_SHEET}'")
    questions = [(_nfc(r[0]), _nfc(r[6]) if len(r) > 6 else "")
                 for r in wb[QUESTION_SHEET].iter_rows(min_row=2, values_only=True) if r and r[0]]
    rows = list(wb[RESULT_SHEET].iter_rows(values_only=True))
    if len(rows) < 3:
        return
    models, header = rows[0], rows[1]
    label_cols = [i for i, h in enumerate(header) if _nfc(h).lower() == "nhãn" and i > 0]
    for (code, question), row in zip(questions, rows[2:2 + len(questions)]):
        for col in label_cols:
            model = _nfc(models[col - 1]) if col - 1 < len(models) else ""
            ann.add(Item(code, model or f"col{col}", _nfc(row[col]) if col < len(row) else "",
                         note=_nfc(row[col + 1]) if col + 1 < len(row) else "",
                         question=question, output=_nfc(row[col - 1])))


def _rows_from_tabular(path: Path) -> Iterable[Mapping[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            yield from csv.DictReader(f)
        return
    with path.open(encoding="utf-8-sig") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"warning: {path}:{n}: invalid JSON ({e.msg})", file=sys.stderr)
                continue
            if isinstance(rec, dict):
                yield rec


def _read_tabular(path: Path, ann: Annotation) -> None:
    default_model = slug(re.sub(r"_labels?$", "", path.stem)) if path.stem.endswith(("_labels", "_label")) else ""
    for r in _rows_from_tabular(path):
        qid = _nfc(r.get("question_id") or r.get("id"))
        if not qid:
            continue
        ann.add(Item(qid, _nfc(r.get("model_id")) or default_model, _nfc(r.get("label")),
                     note=_nfc(r.get("note") or r.get("notes")), question=_nfc(r.get("question")),
                     output=_nfc(r.get("output") or r.get("model_answer"))))


def load_annotation(path: Path) -> Annotation:
    ann = Annotation(path)
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        _read_xlsx(path, ann)
    elif path.suffix.lower() in (".jsonl", ".json", ".csv"):
        _read_tabular(path, ann)
    else:
        raise ValueError(f"{path}: unsupported format (use .xlsx, .jsonl or .csv)")
    return ann


def load_context(bench: Path | None, predictions: Sequence[Path]) -> tuple[dict[str, str], dict[str, str]]:
    questions: dict[str, str] = {}
    outputs: dict[str, str] = {}
    if bench and bench.exists():
        for r in _rows_from_tabular(bench):
            if r.get("id"):
                questions[_qid(str(r["id"]))] = _nfc(r.get("question"))
    for p in predictions:
        if not p.exists():
            continue
        for r in _rows_from_tabular(p):
            if r.get("question_id"):
                outputs[item_key(str(r["question_id"]), _nfc(r.get("model_id")))] = _nfc(r.get("output"))
    return questions, outputs


def binary_kappa(a: Sequence[str], b: Sequence[str], positive: frozenset[str]) -> float | None:
    return cohen_kappa([x in positive for x in a], [y in positive for y in b])


def confusion_matrix(a: Sequence[str], b: Sequence[str]) -> tuple[list[str], dict[tuple[str, str], int]]:
    extra = sorted((set(a) | set(b)) - set(LABELS))
    labels = [lab for lab in LABELS if lab in set(a) | set(b)] + extra
    return labels, Counter(zip(a, b))


def confusion_pairs(a: Sequence[str], b: Sequence[str]) -> list[tuple[tuple[str, str], int]]:
    return Counter(tuple(sorted((x, y))) for x, y in zip(a, b) if x != y).most_common()


def compute(ann_a: Annotation, ann_b: Annotation) -> dict[str, Any]:
    shared = sorted(set(ann_a.items) & set(ann_b.items))
    a = [ann_a.items[k].label for k in shared]
    b = [ann_b.items[k].label for k in shared]
    n = len(shared)
    by_model: dict[str, dict[str, Any]] = {}
    for model in sorted({ann_a.items[k].model_id for k in shared}):
        idx = [i for i, k in enumerate(shared) if ann_a.items[k].model_id == model]
        ma, mb = [a[i] for i in idx], [b[i] for i in idx]
        by_model[model or "-"] = {"n": len(idx), "agreement": sum(x == y for x, y in zip(ma, mb)) / len(idx),
                                  "kappa": cohen_kappa(ma, mb)}
    return {
        "n": n, "keys": shared, "a": a, "b": b,
        "only_a": sorted(set(ann_a.items) - set(ann_b.items)),
        "only_b": sorted(set(ann_b.items) - set(ann_a.items)),
        "agreement": sum(x == y for x, y in zip(a, b)) / n if n else None,
        "kappa": cohen_kappa(a, b),
        "per_label": {lab: binary_kappa(a, b, frozenset({lab})) for lab in LABELS if lab in set(a) | set(b)},
        "criteria": {name: binary_kappa(a, b, pos) for name, pos in CRITERIA.items()},
        "by_model": by_model,
        "pairs": confusion_pairs(a, b),
    }


def export_disagreements(res: Mapping[str, Any], ann_a: Annotation, ann_b: Annotation, out: Path,
                         name_a: str, name_b: str, questions: Mapping[str, str],
                         outputs: Mapping[str, str]) -> int:
    rows = []
    for key, la, lb in zip(res["keys"], res["a"], res["b"]):
        if la == lb:
            continue
        ia, ib = ann_a.items[key], ann_b.items[key]
        qid = _qid(ia.question_id)
        notes = "; ".join(f"{who}: {it.note}" for who, it in ((name_a, ia), (name_b, ib)) if it.note)
        rows.append({
            "id": qid, "model_id": slug(ia.model_id),
            "question": ia.question or ib.question or questions.get(qid, ""),
            "model_answer": ia.output or ib.output or outputs.get(key, ""),
            f"{name_a}_label": la, f"{name_b}_label": lb, "notes": notes,
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "model_id", "question", "model_answer", f"{name_a}_label", f"{name_b}_label", "notes"]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _k(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def report(res: Mapping[str, Any], ann_a: Annotation, ann_b: Annotation, name_a: str, name_b: str,
           expected: int) -> str:
    lines = [f"{name_a}: {ann_a.path}  ({len(ann_a.items)} labelled)",
             f"{name_b}: {ann_b.path}  ({len(ann_b.items)} labelled)",
             f"n (inner join) = {res['n']}" + (f"  [expected {expected}]" if res["n"] != expected else "")]
    for who, ann in ((name_a, ann_a), (name_b, ann_b)):
        if ann.unlabeled:
            lines.append(f"  {who} unlabelled ({len(ann.unlabeled)}): {', '.join(ann.unlabeled)}")
        if ann.invalid:
            lines.append(f"  {who} non-standard labels: " + ", ".join(f"{k}={v}" for k, v in ann.invalid.items()))
        if ann.duplicates:
            lines.append(f"  {who} duplicate ids (last kept): {', '.join(sorted(set(ann.duplicates)))}")
    for who, missing in ((name_b, res["only_a"]), (name_a, res["only_b"])):
        if missing:
            lines.append(f"  missing in {who} ({len(missing)}): {', '.join(missing)}")
    if not res["n"]:
        return "\n".join(lines + ["no overlapping items"])
    kappa = res["kappa"]
    verdict = "" if kappa is None else ("  ✓ ≥ target" if kappa >= KAPPA_TARGET else f"  ✗ < target {KAPPA_TARGET}")
    lines += ["", f"raw agreement   {res['agreement']:.1%}  ({sum(x == y for x, y in zip(res['a'], res['b']))}/{res['n']})",
              f"Cohen's kappa   {_k(kappa)}{verdict}", "", "per-label kappa (one-vs-rest):"]
    lines += [f"  {lab:<16} {_k(v)}" for lab, v in res["per_label"].items()]
    lines += ["criterion kappa:"] + [f"  {name:<36} {_k(v)}" for name, v in res["criteria"].items()]
    if len(res["by_model"]) > 1:
        lines += ["by model:"] + [f"  {m:<16} n={v['n']:<3} agree {v['agreement']:.1%}  kappa {_k(v['kappa'])}"
                                  for m, v in res["by_model"].items()]
    labels, cm = confusion_matrix(res["a"], res["b"])
    short = {lab: lab[:9] for lab in labels}
    lines += ["", f"confusion matrix (rows = {name_a}, cols = {name_b}):",
              " " * 17 + "".join(f"{short[c]:>10}" for c in labels)]
    lines += [f"  {r:<15}" + "".join(f"{cm.get((r, c), 0):>10}" for c in labels) for r in labels]
    if res["pairs"]:
        lines += ["", "most frequent confusion pairs:"]
        lines += [f"  {x} ↔ {y}: {c}" for (x, y), c in res["pairs"]]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cohen's kappa between two pilot annotation files")
    ap.add_argument("annotator_a", type=Path)
    ap.add_argument("annotator_b", type=Path)
    ap.add_argument("--name-a", default="vinh")
    ap.add_argument("--name-b", default="toan")
    ap.add_argument("--bench", type=Path, default=Path("data/benchmark/pilot_30_vinh.jsonl"))
    ap.add_argument("--predictions", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--expected", type=int, default=EXPECTED_ITEMS)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    for p in (args.annotator_a, args.annotator_b):
        if not p.exists() or p.stat().st_size == 0:
            print(f"error: annotation file {p} is missing or empty", file=sys.stderr)
            return 2
    try:
        ann_a, ann_b = load_annotation(args.annotator_a), load_annotation(args.annotator_b)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not ann_a.items or not ann_b.items:
        empty = args.annotator_a if not ann_a.items else args.annotator_b
        print(f"error: {empty} has no labelled items", file=sys.stderr)
        return 2

    res = compute(ann_a, ann_b)
    print(report(res, ann_a, ann_b, args.name_a, args.name_b, args.expected))
    if not res["n"]:
        return 1
    questions, outputs = load_context(args.bench, args.predictions)
    n_dis = export_disagreements(res, ann_a, ann_b, args.out, args.name_a, args.name_b, questions, outputs)
    print(f"\n{n_dis} disagreements → {args.out}")
    if args.json:
        payload = {k: v for k, v in res.items() if k not in ("keys", "a", "b")}
        payload["pairs"] = [{"pair": list(p), "count": c} for p, c in res["pairs"]]
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
