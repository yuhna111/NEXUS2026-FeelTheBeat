"""Retrievers: BM25, dense, hybrid (RRF) (Week 2, TV2). Reranker comes in Week 3 (C3).

All retrievers return ranked `Hit(chunk_id, doc_id, text, score)` lists, so the
evaluation code does not care which one produced them.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rag.chunkers import Chunk

PROCESSED = Path("data/processed")
_UNIT_PREFIX = re.compile(
    r"^(?:thành phố|thị trấn|thị xã|đặc khu|phường|huyện|quận|tỉnh|xã|tp\.?)\s+", re.IGNORECASE
)


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    text: str
    score: float


def rrf_fuse(rankings: list[list[str]], k: int = 60, top_n: int = 20) -> list[str]:
    """Reciprocal Rank Fusion over several ranked lists of chunk ids."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return [cid for cid, _ in sorted(scores.items(), key=lambda x: -x[1])[:top_n]]


# --------------------------------------------------------------------------- BM25

def place_names(processed_dir: Path = PROCESSED) -> list[str]:
    """Multi-syllable place names from TV1's lineage table and entity map.

    Passed to underthesea as `fixed_words` so "Hoàn Kiếm" or "Bà Rịa - Vũng Tàu"
    stay one token instead of being split.
    """
    names: set[str] = set()
    sources = [
        (processed_dir / "commune_lineage.csv", ("new_commune", "old_commune", "old_district",
                                                 "new_province", "old_province")),
        (processed_dir / "entity_map_63_34_v1.csv", ("old_province", "new_province")),
    ]
    for path, cols in sources:
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                for col in cols:
                    name = _UNIT_PREFIX.sub("", (row.get(col) or "").strip())
                    name = unicodedata.normalize("NFC", name)
                    if " " in name:
                        names.add(name)
    return sorted(names, key=len, reverse=True)


class VnTokenizer:
    """underthesea word segmentation + lowercase; punctuation-only tokens dropped."""

    def __init__(self, fixed_words: Sequence[str] | None = None) -> None:
        from underthesea import word_tokenize

        self._tok = word_tokenize
        self._fixed = list(fixed_words) if fixed_words else None

    def __call__(self, text: str) -> list[str]:
        text = unicodedata.normalize("NFC", text)
        toks = self._tok(text, fixed_words=self._fixed)
        return [t.lower().replace(" ", "_") for t in toks if any(ch.isalnum() for ch in t)]


class BM25Retriever:
    def __init__(self, chunks: Sequence[Chunk], tokenizer: Callable[[str], list[str]]) -> None:
        from rank_bm25 import BM25Okapi

        self.chunks = list(chunks)
        self.tokenize = tokenizer
        self.bm25 = BM25Okapi([tokenizer(c.text) for c in self.chunks])

    def search(self, query: str, k: int = 20) -> list[Hit]:
        scores = self.bm25.get_scores(self.tokenize(query))
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        return [Hit(self.chunks[i].chunk_id, self.chunks[i].doc_id, self.chunks[i].text,
                    float(scores[i])) for i in top]


# --------------------------------------------------------------------------- dense

class DenseRetriever:
    """BGE-M3 query embedding + Qdrant search over a collection built by rag.index_build."""

    def __init__(self, collection: str, model=None, client=None) -> None:
        from rag.embedder import load_bge_m3
        from rag.vector_store import get_qdrant

        self.collection = collection
        self.model = model or load_bge_m3()
        self.client = client or get_qdrant()

    def search(self, query: str, k: int = 20) -> list[Hit]:
        return self.search_many([query], k)[0]

    def search_many(self, queries: Sequence[str], k: int = 20) -> list[list[Hit]]:
        vecs = self.model.encode(list(queries), batch_size=16, max_length=256)["dense_vecs"]
        out = []
        for v in vecs:
            pts = self.client.query_points(self.collection, query=v.tolist(), limit=k).points
            out.append([Hit(p.payload["chunk_id"], p.payload["doc_id"], p.payload["text"],
                            float(p.score)) for p in pts])
        return out


# --------------------------------------------------------------------------- hybrid

def hybrid_fuse(rankings: Iterable[Sequence[Hit]], k: int = 60, top_n: int = 20) -> list[Hit]:
    """RRF over hit lists. Hits are keyed by (chunk_id, text) because a few chunk ids
    repeat in data/parsed (NQ 203, Luật 72 Điều 30); the fused score replaces `score`."""
    by_key: dict[tuple[str, str], Hit] = {}
    keyed: list[list[str]] = []
    for hits in rankings:
        ranking = []
        for h in hits:
            key = f"{h.chunk_id}\x00{h.text}"
            by_key.setdefault((h.chunk_id, h.text), h)
            ranking.append(key)
        keyed.append(ranking)
    fused = rrf_fuse(keyed, k=k, top_n=top_n)
    scores = {key: sum(1.0 / (k + r.index(key) + 1) for r in keyed if key in r) for key in fused}
    out = []
    for key in fused:
        cid, text = key.split("\x00", 1)
        h = by_key[(cid, text)]
        out.append(Hit(h.chunk_id, h.doc_id, h.text, scores[key]))
    return out


class Reranker:
    """Cross-encoder reranker (bge-reranker-v2-m3 for C3/C4)."""

    def __init__(self, name: str = "BAAI/bge-reranker-v2-m3", model=None) -> None:
        if model is None:
            import torch
            from FlagEmbedding import FlagReranker

            model = FlagReranker(name, use_fp16=torch.cuda.is_available())
        self.model = model

    def rerank(self, query: str, hits: Sequence[Hit], k: int) -> list[Hit]:
        if not hits:
            return []
        scores = self.model.compute_score([[query, h.text] for h in hits], normalize=True)
        scores = [scores] if isinstance(scores, float) else list(scores)
        order = sorted(range(len(hits)), key=lambda i: -scores[i])[:k]
        return [Hit(hits[i].chunk_id, hits[i].doc_id, hits[i].text, float(scores[i])) for i in order]


class HybridRetriever:
    """BM25 + dense, each top-`candidates`, fused with RRF; optional reranker on the fused
    candidates (C3: rrf top-20 → bge-reranker-v2-m3 → top-k)."""

    def __init__(self, bm25: BM25Retriever, dense: DenseRetriever, rrf_k: int = 60,
                 candidates: int = 20, reranker: Reranker | str | None = None) -> None:
        self.bm25, self.dense, self.rrf_k, self.candidates = bm25, dense, rrf_k, candidates
        self.reranker = Reranker(reranker) if isinstance(reranker, str) else reranker

    def search(self, query: str, k: int = 20) -> list[Hit]:
        fused = self.fuse(self.bm25.search(query, self.candidates),
                          self.dense.search(query, self.candidates),
                          self.candidates if self.reranker else k)
        return self.reranker.rerank(query, fused, k) if self.reranker else fused

    def fuse(self, bm25_hits: Sequence[Hit], dense_hits: Sequence[Hit], k: int = 20) -> list[Hit]:
        return hybrid_fuse([bm25_hits, dense_hits], k=self.rrf_k, top_n=k)
