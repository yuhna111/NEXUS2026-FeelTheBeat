"""Batch inference over the benchmark (Week 4, TV2).

Writes outputs/<config>/<model_id>.jsonl, one line per question with:
model_id, config, question_id, prompt, context_ids, output, timestamp.

Re-running resumes: questions already in the output file are skipped (delete the
file to start over). A model with `subset: <name>` in configs/models.yaml only
runs the ids listed in data/benchmark/subsets/<name>.txt.

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
SUBSETS = Path("data/benchmark/subsets")


def load_questions(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_subset_ids(name: str, subsets_dir: Path = SUBSETS) -> set[str]:
    """Question ids of a named subset: <subsets_dir>/<name>.txt, one id per line."""
    path = subsets_dir / f"{name}.txt"
    if not path.exists():
        raise SystemExit(f"Thiếu file tập con {path} (mỗi dòng một question id).")
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def done_ids(out_path: Path) -> set[str]:
    """Question ids already written to an output file, so a re-run resumes instead of overwriting."""
    if not out_path.exists():
        return set()
    with out_path.open(encoding="utf-8") as f:
        return {json.loads(line)["question_id"] for line in f if line.strip()}


def select_models(models: list[dict], wanted: str) -> list[dict]:
    """Filter by comma-separated ids and require a pinned snapshot for each selected model."""
    if wanted:
        ids = [w.strip() for w in wanted.split(",") if w.strip()]
        unknown = sorted(set(ids) - {m["id"] for m in models})
        if unknown:
            raise SystemExit(f"Không có trong configs/models.yaml: {', '.join(unknown)}")
        models = [m for m in models if m["id"] in ids]
    unpinned = [m["id"] for m in models if not m.get("snapshot")]
    if unpinned:
        raise SystemExit(
            "configs/models.yaml chưa điền `snapshot` cho: " + ", ".join(unpinned)
            + ". Điền mã snapshot chính xác hoặc chọn mô hình khác bằng --models."
        )
    return models


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
    models = select_models(
        yaml.safe_load(Path("configs/models.yaml").read_text(encoding="utf-8"))["models"],
        args.models,
    )

    questions = load_questions(Path(args.bench))
    out_dir = Path("outputs") / args.config
    out_dir.mkdir(parents=True, exist_ok=True)

    for m in models:
        qs = questions
        if m.get("subset"):
            keep = load_subset_ids(m["subset"])
            qs = [q for q in qs if q["id"] in keep]
        if args.limit:
            qs = qs[: args.limit]

        client = LLMClient(provider=m["provider"], model=m["snapshot"])
        out_path = out_dir / f"{m['id']}.jsonl"
        done = done_ids(out_path)
        todo = [q for q in qs if q["id"] not in done]
        with out_path.open("a", encoding="utf-8") as f:
            for q in todo:
                context, context_ids = "", []  # TODO(TV2): retrieval for C1–C6
                rec = client.generate(build_prompt(cfg, q, context))
                f.write(json.dumps({
                    "model_id": m["id"], "config": args.config, "question_id": q["id"],
                    "prompt": rec["prompt"], "context_ids": context_ids,
                    "output": rec["output"], "timestamp": rec["timestamp"],
                }, ensure_ascii=False) + "\n")
        print(f"{out_path}: +{len(todo)} mới, {len(qs) - len(todo)} đã có sẵn")


if __name__ == "__main__":
    main()
