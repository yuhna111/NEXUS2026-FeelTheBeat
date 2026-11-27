"""Batch inference over a benchmark file (Week 3, TV2).

Writes outputs/<bench stem>/<config>/<model_id>.jsonl (run 1) and
<model_id>.run<N>.jsonl (runs 2..N), one line per question, in the format read by
eval/metrics.py (load_predictions):
model_id, config, question_id, prompt, context_ids, output, timestamp
+ run, seed, temperature, model_version, usage.

One file per run because eval/metrics.py scores one answer per question id.

RAG configs (C1–C4) read contexts precomputed by rag.retrieve_contexts, so this
script needs no index or GPU (e.g. Qwen on Colab only generates). C0 has no context.

Re-running resumes: questions already in an output file are skipped (delete the
file to start over). A model with `subset: <name>` in configs/models.yaml only
runs the ids listed in data/benchmark/subsets/<name>.txt.

Usage:
    python -m rag.run_inference --config C0 --bench data/benchmark/pilot_80_v0.3.jsonl \
        --models gemini-flash [--runs 3] [--temperature 0.7] [--limit 30]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from rag.llm_client import LLMClient

BENCH = Path("data/benchmark/vn_admin2025_qa_v1.0.jsonl")
PROMPTS = Path("configs/prompts")
SUBSETS = Path("data/benchmark/subsets")
OUTPUTS = Path("outputs")


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


def resolve_config(name: str, path: Path = Path("configs/retrieval.yaml")) -> dict:
    all_cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg = dict(all_cfg[name])
    if "inherit" in cfg:
        cfg = {**resolve_config(cfg["inherit"], path), **cfg}
    return cfg


def context_config(name: str, path: Path = Path("configs/retrieval.yaml")) -> str:
    """Config whose retrieved contexts `name` uses: C4 inherits C3 and only changes the
    prompt, so it reads C3's contexts instead of retrieving again."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))[name]
    own_retrieval = {"retrieval", "collection", "top_k", "candidates", "reranker", "rrf_k",
                     "distractors", "oracle_file"} & set(raw)
    if "inherit" in raw and not own_retrieval:
        return context_config(raw["inherit"], path)
    return name


def build_prompt(cfg: dict, q: dict, context: str = "") -> str:
    tpl = (PROMPTS / f"{cfg['prompt']}.txt").read_text(encoding="utf-8")
    return tpl.format(question=q["question"], context=context,
                      reference_date=q.get("reference_date", ""))


def output_path(bench: Path, config: str, model_id: str, run: int) -> Path:
    name = f"{model_id}.jsonl" if run == 1 else f"{model_id}.run{run}.jsonl"
    return OUTPUTS / bench.stem / config / name


def run_seed(run: int) -> int | None:
    """Run 1 has no seed; later runs use seed = run so each is a distinct cached call."""
    return None if run == 1 else run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", default="")
    ap.add_argument("--bench", type=Path, default=BENCH)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--first-run", type=int, default=1, help="e.g. 2 to add runs 2..N only")
    ap.add_argument("--temperature", type=float)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    cfg = resolve_config(args.config)
    model_cfg = yaml.safe_load(Path("configs/models.yaml").read_text(encoding="utf-8"))
    models = select_models(model_cfg["models"], args.models)
    defaults = model_cfg.get("defaults", {})
    temperature = args.temperature if args.temperature is not None else defaults.get("temperature", 0)

    questions = load_questions(args.bench)
    contexts: dict[str, dict] = {}
    if cfg.get("retrieval", "none") != "none":
        from rag.retrieve_contexts import load_contexts

        contexts = load_contexts(args.bench, context_config(args.config))

    for m in models:
        qs = questions
        if m.get("subset") and (SUBSETS / f"{m['subset']}.txt").exists():
            keep = load_subset_ids(m["subset"])
            qs = [q for q in qs if q["id"] in keep]
        if args.limit:
            qs = qs[: args.limit]

        client = LLMClient(provider=m["provider"], model=m["snapshot"], temperature=temperature,
                           max_tokens=defaults.get("max_tokens", 512))
        for run in range(args.first_run, args.runs + 1):
            out_path = output_path(args.bench, args.config, m["id"], run)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            done = done_ids(out_path)
            todo = [q for q in qs if q["id"] not in done]
            with out_path.open("a", encoding="utf-8", newline="\n") as f:
                for i, q in enumerate(todo, 1):
                    ctx = contexts.get(q["id"], {})
                    rec = client.generate(build_prompt(cfg, q, ctx.get("context", "")),
                                          seed=run_seed(run))
                    usage = rec.get("usage") or {}
                    f.write(json.dumps({
                        "model_id": m["id"], "config": args.config, "question_id": q["id"],
                        "prompt": rec["prompt"], "context_ids": ctx.get("context_ids", []),
                        "output": rec["output"], "timestamp": rec["timestamp"],
                        "run": run, "seed": run_seed(run), "temperature": temperature,
                        "model_version": usage.get("model_version") or m["snapshot"],
                        "usage": usage,
                    }, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"\r{m['id']} {args.config} run{run}: {i}/{len(todo)}", end="",
                          file=sys.stderr, flush=True)
            print(f"\n{out_path}: +{len(todo)} mới, {len(qs) - len(todo)} đã có sẵn", file=sys.stderr)


if __name__ == "__main__":
    main()
