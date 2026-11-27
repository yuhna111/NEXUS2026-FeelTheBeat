"""LLM-as-a-Judge runner & pilot calibration against human labels (TV3).

Rule (Week 3 assignment & eval/metrics_spec.md):
  - The judge model MUST NOT be the same model family as the evaluated model
    (e.g., when evaluating `gemini-flash` and `qwen-7b`, pick `claude-haiku`,
    `gpt-mini`, or a distinct open model such as `meta-llama/Llama-3.1-8B-Instruct`
    served via vLLM).
  - Prompt template lives in `eval/judge_prompt_v1.txt` (includes Group D examples
    and boundary rules from `eval/metrics_spec.md` v0.3.1).

Usage:
    # Dry-run prompt rendering (no API calls):
    python -m eval.judge outputs/pilot_manual/deepseek.jsonl \
        --bench data/benchmark/pilot_30_vinh.jsonl --dry-run

    # Judge predictions & calibrate against human labels (e.g. 90 pilot items):
    python -m eval.judge outputs/pilot_manual/chatgpt.jsonl outputs/pilot_manual/deepseek.jsonl \
        outputs/pilot_manual/gemini-flash.jsonl \
        --bench data/benchmark/pilot_30_vinh.jsonl \
        --provider anthropic --model claude-3-5-haiku-20241022 \
        --human-labels outputs/pilot_manual/chatgpt_labels.jsonl \
                       outputs/pilot_manual/deepseek_labels.jsonl \
                       outputs/pilot_manual/gemini-flash_labels.jsonl \
        --out results/judge_pilot90.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from eval.metrics import (
    DEFAULT_ENTITY_MAPS,
    LABELS,
    NEEDS_JUDGE,
    auto_label,
    cohen_kappa,
    load_predictions,
    load_vocab,
    read_jsonl,
)

DEFAULT_PROMPT = Path(__file__).with_name("judge_prompt_v1.txt")
RECOMMENDED_JUDGES = {
    # Evaluated models -> recommended non-overlapping judges
    "gemini-flash": ("anthropic/claude-haiku", "openai/gpt-mini", "vllm/Llama-3.1-8B-Instruct"),
    "qwen-7b": ("anthropic/claude-haiku", "openai/gpt-mini", "vllm/Llama-3.1-8B-Instruct"),
}

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def load_prompt_template(path: Path = DEFAULT_PROMPT) -> str:
    return path.read_text(encoding="utf-8")


def render_prompt(q: Mapping[str, Any], prediction: str, template: str) -> str:
    gold = q.get("gold_answer") if isinstance(q.get("gold_answer"), Mapping) else {}
    obs = q.get("obsolete_answer") if isinstance(q.get("obsolete_answer"), Mapping) else {}
    obs_ents = obs.get("obsolete_entities") or []
    return template.format(
        reference_date=q.get("reference_date") or "2026-11-27",
        question=q.get("question") or "",
        gold_answer=gold.get("text") or "",
        obsolete_entities=", ".join(obs_ents) if obs_ents else "(không có)",
        prediction=prediction or "",
    )


def parse_judge_response(text: str) -> tuple[str | None, str]:
    """Extract (label, rationale) from a judge model output string."""
    raw = (text or "").strip()
    candidates = []
    m_fence = _FENCE_RE.search(raw)
    if m_fence:
        candidates.append(m_fence.group(1))
    candidates.append(raw)
    for m_obj in _OBJ_RE.finditer(raw):
        candidates.append(m_obj.group(0))

    for cand in candidates:
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            lab = str(obj.get("label") or "").strip().upper()
            rat = str(obj.get("rationale") or "").strip()
            if lab in LABELS:
                return lab, rat
            return None, rat
    # Fallback: look for an exact label token if JSON failed
    for lab in LABELS:
        if re.search(rf"\b{lab}\b", raw):
            return lab, raw[:200]
    return None, raw[:200]


def same_model_family(judge_provider: str, judge_model: str, evaluated_model_id: str) -> bool:
    """Detect whether judge and evaluated model belong to the same family (forbidden)."""
    jm = f"{judge_provider} {judge_model}".lower()
    em = (evaluated_model_id or "").lower()
    families = (
        ("gemini", "google"),
        ("qwen",),
        ("gpt", "openai", "chatgpt"),
        ("claude", "anthropic"),
        ("deepseek",),
        ("llama",),
    )
    for fam in families:
        if any(tok in jm for tok in fam) and any(tok in em for tok in fam):
            return True
    return False


def judge_predictions(
    preds: Sequence[Mapping[str, Any]],
    bench: Mapping[str, Mapping[str, Any]],
    client: Any,
    *,
    template: str,
    only_pending: bool = False,
    vocab: set[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for p in preds:
        qid = p["question_id"]
        if qid not in bench:
            continue
        q = bench[qid]
        if only_pending:
            auto = auto_label(p["output"], q, vocab or set())
            if auto != NEEDS_JUDGE:
                results.append({
                    "question_id": qid,
                    "model_id": p.get("model_id", ""),
                    "label": auto,
                    "rationale": "auto_label",
                    "source": "auto",
                })
                continue
        prompt = render_prompt(q, p["output"], template)
        rec = client.generate(prompt)
        label, rationale = parse_judge_response(rec.get("output", ""))
        results.append({
            "question_id": qid,
            "model_id": p.get("model_id", ""),
            "label": label or NEEDS_JUDGE,
            "rationale": rationale,
            "source": "llm_judge",
            "judge_model": rec.get("model", getattr(client, "model", "")),
            "cache_key": rec.get("key", ""),
        })
    return results


def compare_with_human(
    judge_rows: Sequence[Mapping[str, Any]],
    human_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    def key_of(r: Mapping[str, Any]) -> tuple[str, str]:
        return str(r.get("question_id") or r.get("id") or "").strip(), str(r.get("model_id") or "").strip().lower()

    j_map = {key_of(r): str(r.get("label") or "").upper() for r in judge_rows if r.get("label") in LABELS}
    h_map = {key_of(r): str(r.get("label") or "").upper() for r in human_rows if r.get("label") in LABELS}
    shared = sorted(set(j_map) & set(h_map))
    ja = [j_map[k] for k in shared]
    hb = [h_map[k] for k in shared]
    n = len(shared)
    acc = sum(x == y for x, y in zip(ja, hb)) / n if n else None
    kappa = cohen_kappa(ja, hb)
    stale_kappa = cohen_kappa([x == "STALE" for x in ja], [y == "STALE" for y in hb]) if n else None
    stale_plus_kappa = cohen_kappa(
        [x in ("STALE", "BLENDED") for x in ja],
        [y in ("STALE", "BLENDED") for y in hb],
    ) if n else None
    cm = Counter(zip(hb, ja))
    return {
        "n": n,
        "agreement": acc,
        "kappa": kappa,
        "stale_kappa": stale_kappa,
        "stale_plus_kappa": stale_plus_kappa,
        "confusion": {f"{h}->{j}": c for (h, j), c in cm.most_common()},
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run LLM-as-a-Judge using eval/judge_prompt_v1.txt")
    ap.add_argument("predictions", type=Path, nargs="+")
    ap.add_argument("--bench", type=Path, required=True)
    ap.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    ap.add_argument("--provider", choices=["openai", "gemini", "anthropic", "vllm"])
    ap.add_argument("--model", type=str)
    ap.add_argument("--only-pending", action="store_true", help="Only call judge for auto_label == NEEDS_JUDGE")
    ap.add_argument("--allow-same-family", action="store_true", help="Override non-overlapping judge guard")
    ap.add_argument("--human-labels", type=Path, nargs="*", default=[])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    bench = {q["id"]: q for q in read_jsonl(args.bench) if q.get("id")}
    template = load_prompt_template(args.prompt)
    all_preds: list[dict[str, Any]] = []
    for p in args.predictions:
        all_preds.extend(load_predictions(p))

    if args.dry_run:
        sample = [p for p in all_preds if p["question_id"] in bench][:2]
        print(f"Loaded {len(all_preds)} predictions across {len(args.predictions)} file(s); bench={len(bench)}")
        for s in sample:
            print("=" * 60)
            print(render_prompt(bench[s["question_id"]], s["output"], template))
        return 0

    if not args.provider or not args.model:
        print("error: --provider and --model are required unless --dry-run is set", file=sys.stderr)
        return 2

    if not args.allow_same_family:
        models_eval = sorted({str(p.get("model_id") or "") for p in all_preds})
        bad = [m for m in models_eval if same_model_family(args.provider, args.model, m)]
        if bad:
            print(
                f"error: judge {args.provider}/{args.model} overlaps evaluated model(s) {bad}; "
                "choose a distinct model family or pass --allow-same-family explicitly.",
                file=sys.stderr,
            )
            return 2

    from rag.llm_client import LLMClient

    client = LLMClient(provider=args.provider, model=args.model, temperature=0.0, max_tokens=256)
    vocab = load_vocab(DEFAULT_ENTITY_MAPS, bench.values())
    rows = judge_predictions(all_preds, bench, client, template=template, only_pending=args.only_pending, vocab=vocab)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Wrote {len(rows)} judge labels -> {args.out}")

    if args.human_labels:
        human_rows: list[dict[str, Any]] = []
        for hp in args.human_labels:
            human_rows.extend(read_jsonl(hp))
        stats = compare_with_human(rows, human_rows)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
