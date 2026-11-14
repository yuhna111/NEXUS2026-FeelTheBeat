"""Batch inference over the benchmark (Week 4, TV2).

Writes outputs/<config>/<model_id>.jsonl, one line per question with:
model_id, config, question_id, prompt, context_ids, output, timestamp.

Usage:
    python -m rag.run_inference --config C0 [--models qwen-7b,gpt-mini] [--limit 30]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from rag.llm_client import LLMClient

BENCH = Path("data/benchmark/vn_admin2025_qa_v1.0.jsonl")
PROMPTS = Path("configs/prompts")


def load_questions(path: Path, limit: int | None) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        qs = [json.loads(line) for line in f if line.strip()]
    return qs[:limit] if limit else qs


def build_prompt(cfg: dict, q: dict, context: str = "") -> str:
    tpl = (PROMPTS / f"{cfg['prompt']}.txt").read_text(encoding="utf-8")
    return tpl.format(question=q["question"], context=context,
                      reference_date=q.get("reference_date", ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", default="")
    ap.add_argument("--bench", default=str(BENCH))
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path("configs/retrieval.yaml").read_text(encoding="utf-8"))[args.config]
    models = yaml.safe_load(Path("configs/models.yaml").read_text(encoding="utf-8"))["models"]
    if args.models:
        wanted = set(args.models.split(","))
        models = [m for m in models if m["id"] in wanted]

    questions = load_questions(Path(args.bench), args.limit)
    out_dir = Path("outputs") / args.config
    out_dir.mkdir(parents=True, exist_ok=True)

    for m in models:
        client = LLMClient(provider=m["provider"], model=m["snapshot"] or m["id"])
        out_path = out_dir / f"{m['id']}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for q in questions:
                context, context_ids = "", []  # TODO(TV2): retrieval for C1–C6
                rec = client.generate(build_prompt(cfg, q, context))
                f.write(json.dumps({
                    "model_id": m["id"], "config": args.config, "question_id": q["id"],
                    "prompt": rec["prompt"], "context_ids": context_ids,
                    "output": rec["output"], "timestamp": rec["timestamp"],
                }, ensure_ascii=False) + "\n")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
