"""Precompute retrieval contexts for a RAG config (Week 3, TV2).

Retrieval runs once, on a machine with the Qdrant indexes and BGE-M3; generation
(rag.run_inference) then only reads the file, so Colab/vLLM never needs the index.

    python -m rag.retrieve_contexts --config C2 --bench data/benchmark/pilot_80_v0.3.jsonl

Writes outputs/contexts/<bench stem>/<config>.jsonl, one line per question:
{question_id, config, context_ids, scores, context}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from rag.retriever import Hit

PARSED = Path("data/parsed")
CONTEXT_DIR = Path("outputs/contexts")


def doc_labels(parsed_dir: Path = PARSED) -> dict[str, str]:
    """doc_id -> human label such as 'Nghị quyết 202/2025/QH15'."""
    out = {}
    for p in sorted(parsed_dir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        kind = "Luật" if d["doc_id"].startswith("LUAT") else "Nghị quyết"
        out[d["doc_id"]] = f"{kind} {d.get('doc_number') or d['doc_id']}"
    return out


def format_context(hits: list[Hit], labels: dict[str, str]) -> str:
    return "\n\n".join(f"[{i}] {labels.get(h.doc_id, h.doc_id)}\n{h.text}"
                       for i, h in enumerate(hits, start=1))


def context_path(bench: Path, config: str) -> Path:
    return CONTEXT_DIR / bench.stem / f"{config}.jsonl"


def load_contexts(bench: Path, config: str) -> dict[str, dict]:
    path = context_path(bench, config)
    if not path.exists():
        raise SystemExit(f"Thiếu ngữ cảnh {path}. Chạy trước: python -m rag.retrieve_contexts "
                         f"--config {config} --bench {bench}")
    with path.open(encoding="utf-8") as f:
        return {r["question_id"]: r for r in map(json.loads, f) if r}


def build_retriever(cfg: dict):
    """dense → DenseRetriever; hybrid → BM25 + dense (RRF), with reranker if cfg has one."""
    from rag.retriever import DenseRetriever

    dense = DenseRetriever(cfg["collection"])
    if cfg["retrieval"] == "dense":
        return dense
    if cfg["retrieval"] == "hybrid":
        from rag.index_build import build_chunks
        from rag.retriever import BM25Retriever, HybridRetriever, VnTokenizer, place_names

        chunker = "legal" if cfg["collection"].endswith("legal") else "fixed"
        bm25 = BM25Retriever(build_chunks(chunker), VnTokenizer(place_names()))
        return HybridRetriever(bm25, dense, rrf_k=cfg.get("rrf_k", 60),
                               candidates=cfg.get("candidates", 20),
                               reranker=cfg.get("reranker"))
    raise SystemExit(f"retrieval={cfg['retrieval']!r} không cần ngữ cảnh truy xuất")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--bench", type=Path, required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path("configs/retrieval.yaml").read_text(encoding="utf-8"))[args.config]
    if "inherit" in cfg:
        base = yaml.safe_load(Path("configs/retrieval.yaml").read_text(encoding="utf-8"))[cfg["inherit"]]
        cfg = {**base, **cfg}
    with args.bench.open(encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]
    retriever = build_retriever(cfg)
    labels = doc_labels()
    k = cfg.get("top_k", 5)

    out = context_path(args.bench, args.config)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        for q in questions:
            hits = retriever.search(q["question"], k)[:k]
            f.write(json.dumps({"question_id": q["id"], "config": args.config,
                                "context_ids": [h.chunk_id for h in hits],
                                "scores": [round(h.score, 4) for h in hits],
                                "context": format_context(hits, labels)},
                               ensure_ascii=False) + "\n")
    print(f"{out}: {len(questions)} câu, top-{k}")


if __name__ == "__main__":
    main()
