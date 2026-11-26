"""Recall@5 of BM25 / dense / hybrid / hybrid+rerank × fixed / legal chunking (Weeks 2–3, TV2).

    python -m rag.eval_retrieval                       # needs vnadmin_fixed / vnadmin_legal
    python -m rag.eval_retrieval --skip-dense          # BM25 only, no GPU / Qdrant
    python -m rag.eval_retrieval --rerank              # + C3: RRF top-20 → bge-reranker-v2-m3

Question sets (gold = eval.qa_schema.recall_gold_ids; TODO_VERIFY_CLAUSE questions excluded)
- `pilot_v0.3` (main table): data/benchmark/pilot_80_v0.3.jsonl
- `pilot_v0.2` (comparison with Week 2): data/benchmark/pilot_80_v0.2.jsonl

Hit rule (one correct chunk in the top k is enough), metrics_spec v0.3 §5
- legal chunks: chunk_id is a gold clause id (ids match data/parsed directly).
- fixed chunks: eval.metrics.fixed_hit_rank (same doc, covers ≥ 50% of a gold clause).

Outputs
- results/retrieval_w2/recall.md + recall.json   (tables)
- outputs/retrieval_w2/<method>_<chunker>.jsonl  (per question: top-20 context_ids, hit rank)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from eval.metrics import fixed_hit_rank
from eval.qa_schema import read_jsonl, recall_gold_ids
from rag.index_build import build_chunks
from rag.retriever import BM25Retriever, Hit, HybridRetriever, VnTokenizer, place_names

PARSED = Path("data/parsed")
QSETS = {
    "pilot_v0.3": Path("data/benchmark/pilot_80_v0.3.jsonl"),
    "pilot_v0.2": Path("data/benchmark/pilot_80_v0.2.jsonl"),
}
COLLECTIONS = {"fixed": "vnadmin_fixed", "legal": "vnadmin_legal"}
CANDIDATES = 20


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split()).lower()


def clause_texts(parsed_dir: Path = PARSED) -> dict[str, list[str]]:
    """clause id -> texts (a list: a few ids repeat in data/parsed)."""
    out: dict[str, list[str]] = defaultdict(list)
    for p in sorted(parsed_dir.glob("*.json")):
        for a in json.loads(p.read_text(encoding="utf-8"))["articles"]:
            for c in a.get("clauses") or []:
                out[c["id"]].append(c["text"])
    return out


def load_questions(qset: str) -> list[tuple[str, str, set[str]]]:
    out = []
    for r in read_jsonl(QSETS[qset]):
        gold = recall_gold_ids(r)
        if gold:
            out.append((r["id"], r["question"], set(gold)))
    return out


def hit_rank(hits: Sequence[Hit], gold: set[str], chunker: str, clauses: dict[str, list[str]],
             k: int) -> int | None:
    """1-based rank of the first correct chunk within the top k, else None."""
    if chunker == "fixed":
        return fixed_hit_rank([h.chunk_id for h in hits], {h.chunk_id: h.text for h in hits},
                              {g: clauses.get(g, []) for g in gold}, k=k)
    for rank, h in enumerate(hits[:k], start=1):
        if h.chunk_id in gold:
            return rank
    return None


def score(ranks: Sequence[int | None]) -> dict:
    n = len(ranks)
    ok = sum(r is not None for r in ranks)
    return {"n": n, "hits": ok, "recall": round(ok / n, 4) if n else None,
            "mrr": round(sum(1 / r for r in ranks if r) / n, 4) if n else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--skip-dense", action="store_true")
    ap.add_argument("--rerank", action="store_true", help="add hybrid_rerank (C3)")
    ap.add_argument("--out", type=Path, default=Path("results/retrieval_w2"))
    ap.add_argument("--log-dir", type=Path, default=Path("outputs/retrieval_w2"))
    args = ap.parse_args()

    clauses = clause_texts()
    qsets = {name: load_questions(name) for name in QSETS}
    all_q = {qid: q for qs in qsets.values() for qid, q, _ in qs}
    print({name: len(qs) for name, qs in qsets.items()}, file=sys.stderr)

    t0 = time.time()
    tokenizer = VnTokenizer(place_names())
    chunks = {c: build_chunks(c) for c in COLLECTIONS}
    bm25 = {c: BM25Retriever(chunks[c], tokenizer) for c in COLLECTIONS}
    timing = {"bm25_build_s": round(time.time() - t0, 1)}

    # Retrieve once per (method, chunker) for every question id, then score each set.
    results: dict[tuple[str, str], dict[str, list[Hit]]] = {}
    qids = list(all_q)
    for c in COLLECTIONS:
        results[("bm25", c)] = {q: bm25[c].search(all_q[q], CANDIDATES) for q in qids}
    if not args.skip_dense:
        from rag.embedder import load_bge_m3
        from rag.retriever import DenseRetriever
        from rag.vector_store import get_qdrant

        model, client = load_bge_m3(), get_qdrant()
        reranker = None
        for c, coll in COLLECTIONS.items():
            dense = DenseRetriever(coll, model=model, client=client)
            hits = dense.search_many([all_q[q] for q in qids], CANDIDATES)
            results[("dense", c)] = dict(zip(qids, hits))
            hyb = HybridRetriever(bm25[c], dense, candidates=CANDIDATES)
            results[("hybrid", c)] = {q: hyb.fuse(results[("bm25", c)][q], results[("dense", c)][q],
                                                  CANDIDATES) for q in qids}
            if args.rerank:
                from rag.retriever import Reranker

                reranker = reranker or Reranker()
                results[("hybrid_rerank", c)] = {
                    q: reranker.rerank(all_q[q], results[("hybrid", c)][q], CANDIDATES) for q in qids}
    timing["retrieval_s"] = round(time.time() - t0, 1)

    table: dict[str, dict[str, dict]] = {}
    args.log_dir.mkdir(parents=True, exist_ok=True)
    for (method, c), by_q in results.items():
        with (args.log_dir / f"{method}_{c}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for qid in qids:
                hits = by_q[qid]
                f.write(json.dumps({"question_id": qid, "method": method, "chunker": c,
                                    "context_ids": [h.chunk_id for h in hits],
                                    "scores": [round(h.score, 4) for h in hits]},
                                   ensure_ascii=False) + "\n")
        for name, qs in qsets.items():
            ranks = [hit_rank(by_q[qid], gold, c, clauses, args.k) for qid, _, gold in qs]
            table.setdefault(name, {})[f"{method}/{c}"] = score(ranks)

    args.out.mkdir(parents=True, exist_ok=True)
    meta = {"k": args.k, "candidates": CANDIDATES, "rrf_k": 60, "fixed_rule": "fixed_hit_rank ≥ 0.5",
            "question_sets": {n: str(p) for n, p in QSETS.items()}, **timing}
    (args.out / "recall.json").write_text(
        json.dumps({"meta": meta, "results": table}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (args.out / "recall.md").write_text(render_md(table, args.k, meta), encoding="utf-8")
    print(render_md(table, args.k, meta))


def render_md(table: dict, k: int, meta: dict) -> str:
    lines = [f"# Recall@{k} trên bộ pilot (TV2)", ""]
    for name, cells in table.items():
        n = next(iter(cells.values()))["n"]
        lines += [f"## Bộ `{name}` ({n} câu)", "",
                  "| Truy xuất | Chia cố định | Chia theo Điều–Khoản |", "|---|---|---|"]
        for method in ("bm25", "dense", "hybrid", "hybrid_rerank"):
            row = [cells.get(f"{method}/{c}") for c in ("fixed", "legal")]
            if not any(row):
                continue
            fmt = [f"{x['recall']:.3f} ({x['hits']}/{x['n']}) · MRR {x['mrr']:.3f}" if x else "—"
                   for x in row]
            lines.append(f"| {method} | {fmt[0]} | {fmt[1]} |")
        lines.append("")
    lines += ["Tham số: " + ", ".join(f"{a}={b}" for a, b in meta.items() if a != "question_sets"), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
