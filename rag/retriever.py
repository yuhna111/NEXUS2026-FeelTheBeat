"""Retrievers: BM25, dense, hybrid (RRF) + reranker (Week 3, TV2)."""
from __future__ import annotations


def rrf_fuse(rankings: list[list[str]], k: int = 60, top_n: int = 20) -> list[str]:
    """Reciprocal Rank Fusion over several ranked lists of chunk ids."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return [cid for cid, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_n]]


class BM25Retriever:
    """TODO(TV2): rank_bm25 + underthesea word_tokenize, place-name dictionary."""


class DenseRetriever:
    """TODO(TV2): BGE-M3 query embedding + Qdrant search."""


class HybridRetriever:
    """TODO(TV2): BM25 + dense → rrf_fuse(top-20) → bge-reranker-v2-m3 → top-5."""
