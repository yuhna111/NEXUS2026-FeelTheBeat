"""Cohen's κ giữa TV1 và TV3 trên các câu trả lời pilot mà cả hai đã gán độc lập.

TV1 gán độc lập 20 câu (chọn ngẫu nhiên trong 90 câu = 30 câu × 3 mô hình, ẩn tên mô hình,
xáo thứ tự) → outputs/pilot_manual/tv1_recheck20_labels.jsonl.
TV3: outputs/pilot_manual/<model>_labels.jsonl.

Usage:  python scripts/kappa_tv1_tv3.py [--bootstrap 5000]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.metrics import cohen_kappa  # noqa: E402

PILOT = Path("outputs/pilot_manual")
MODELS = ["chatgpt", "deepseek", "gemini-flash"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tv1", default=str(PILOT / "tv1_recheck20_labels.jsonl"))
    ap.add_argument("--bootstrap", type=int, default=5000)
    args = ap.parse_args()
    tv3 = {}
    for m in MODELS:
        for line in open(PILOT / f"{m}_labels.jsonl", encoding="utf-8"):
            d = json.loads(line)
            tv3[(d["question_id"], m)] = d["label"]
    pairs, diffs = [], []
    for line in open(args.tv1, encoding="utf-8"):
        d = json.loads(line)
        b = tv3[(d["question_id"], d["model_id"])]
        pairs.append((d["label"], b))
        if d["label"] != b:
            diffs.append((d["question_id"], d["model_id"], d["label"], b))
    a, b = [p[0] for p in pairs], [p[1] for p in pairs]
    kappa = cohen_kappa(a, b)
    agree = sum(x == y for x, y in pairs)
    rng = random.Random(0)
    ks = []
    for _ in range(args.bootstrap):
        s = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        k = cohen_kappa([x for x, _ in s], [y for _, y in s])
        if k is not None:
            ks.append(k)
    ks.sort()
    lo, hi = ks[int(0.025 * len(ks))], ks[int(0.975 * len(ks))]
    print(f"n = {len(pairs)}, khớp {agree}/{len(pairs)}, Cohen's κ = {kappa:.3f} "
          f"(bootstrap 95%: {lo:.2f}–{hi:.2f})")
    for q, m, x, y in diffs:
        print(f"  bất đồng: {q} [{m}] TV1={x} · TV3={y}")


if __name__ == "__main__":
    main()
