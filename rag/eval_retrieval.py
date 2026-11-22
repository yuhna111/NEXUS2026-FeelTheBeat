"""Recall@5 of BM25 / dense / hybrid × fixed / legal chunking on the pilot set (Week 2, TV2).

    python -m rag.eval_retrieval                       # needs vnadmin_fixed / vnadmin_legal
    python -m rag.eval_retrieval --skip-dense          # BM25 only, no GPU / Qdrant

Question sets
- `v1.0` (main table): data/benchmark/pilot_80_v0.2.jsonl, gold = eval.qa_schema.recall_gold_ids
  (`gold_clause_ids`; questions marked TODO_VERIFY_CLAUSE are excluded).
- `tv1-33` (comparison with TV1's note of 20/11): data/benchmark/pilot_80.jsonl, gold =
  evidence clause ids with in_corpus = true.

Hit rule (one correct chunk in the top k is enough)
- legal chunks: chunk_id is a gold clause id (ids match data/parsed directly).
- fixed chunks: chunk text contains the first 80 characters of a gold clause
  (whitespace-collapsed, lowercased) — TV1's rule; to be confirmed by TV3 (qa_schema §5 (3)).

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

from eval.qa_schema import read_jsonl, recall_gold_ids
from rag.index_build import build_chunks
from rag.retriever import BM25Retriever, Hit, HybridRetriever, VnTokenizer, place_names

PARSED = Path("data/parsed")
QSETS = {
    "v1.0": Path("data/benchmark/pilot_80_v0.2.jsonl"),
    "tv1-33": Path("data/benchmark/pilot_80.jsonl"),
}
COLLECTIONS = {"fixed": "vnadmin_fixed", "legal": "vnadmin_legal"}
PREFIX_CHARS = 80
CANDIDATES = 20


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split()).lower()


def clause_texts(parsed_dir: Path = PARSED) -> dict[str, list[str]]:
    """clause id -> normalized texts (a list: a few ids repeat in data/parsed)."""
    out: dict[str, list[str]] = defaultdict(list)
    for p in sorted(parsed_dir.glob("*.json")):
        for a in json.loads(p.read_text(encoding="utf-8"))["articles"]:
            for c in a.get("clauses") or []:
                out[c["id"]].append(norm(c["text"]))
    return out


def load_questions(qset: str) -> list[tuple[str, str, set[str]]]:
    recs = read_jsonl(QSETS[qset])
    out = []
    for r in recs:
        if qset == "v1.0":
            gold = recall_gold_ids(r)
        else:
            gold = {e["clause_id"] for e in r["evidence"] if e.get("in_corpus") and e.get("clause_id")}
        if gold:
            out.append((r["id"], r["question"], set(gold)))
    return out


def hit_rank(hits: Sequence[Hit], gold: set[str], chunker: str, clauses: dict[str, list[str]],
             k: int) -> int | None:
    """1-based rank of the first correct chunk within the top k, else None."""
    prefixes = [t[:PREFIX_CHARS] for g in gold for t in clauses.get(g, [])]
    for rank, h in enumerate(hits[:k], start=1):
        if chunker == "legal":
            if h.chunk_id in gold:
                return rank
        elif any(p and p in norm(h.text) for p in prefixes):
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
        for c, coll in COLLECTIONS.items():
            dense = DenseRetriever(coll, model=model, client=client)
            hits = dense.search_many([all_q[q] for q in qids], CANDIDATES)
            results[("dense", c)] = dict(zip(qids, hits))
            hyb = HybridRetriever(bm25[c], dense, candidates=CANDIDATES)
            results[("hybrid", c)] = {q: hyb.fuse(results[("bm25", c)][q], results[("dense", c)][q],
                                                  CANDIDATES) for q in qids}
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
    meta = {"k": args.k, "candidates": CANDIDATES, "rrf_k": 60, "prefix_chars": PREFIX_CHARS,
            "question_sets": {n: str(p) for n, p in QSETS.items()}, **timing}
    (args.out / "recall.json").write_text(
        json.dumps({"meta": meta, "results": table}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (args.out / "recall.md").write_text(render_md(table, args.k, meta), encoding="utf-8")
    print(render_md(table, args.k, meta))


def render_md(table: dict, k: int, meta: dict) -> str:
    lines = [f"# Recall@{k} trên bộ pilot (tuần 2, TV2)", ""]
    for name, cells in table.items():
        n = next(iter(cells.values()))["n"]
        lines += [f"## Bộ `{name}` ({n} câu)", "",
                  "| Truy xuất | Chia cố định | Chia theo Điều–Khoản |", "|---|---|---|"]
        for method in ("bm25", "dense", "hybrid"):
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
