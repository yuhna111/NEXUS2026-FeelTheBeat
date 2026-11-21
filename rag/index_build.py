"""Build Qdrant collections with BGE-M3 from data/parsed (Week 2, TV2).

Re-runnable from scratch: each run drops and rebuilds the collection.

    python -m rag.index_build --chunker fixed --collection vnadmin_fixed
    python -m rag.index_build --chunker legal --collection vnadmin_legal
    python -m rag.index_build --chunker legal --stats-only   # chunk counts, no embedding

Qdrant location comes from .env (QDRANT_PATH for embedded, else QDRANT_URL).
A JSON summary (chunks, lengths, timing, VRAM) is written to results/index/<collection>.json.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from collections import Counter
from pathlib import Path
from statistics import mean

from rag.chunkers import Chunk, fixed_chunks, legal_chunks

PARSED_DIR = Path("data/parsed")
RESULTS_DIR = Path("results/index")
CHUNKERS = {"fixed": fixed_chunks, "legal": legal_chunks}


def load_docs(parsed_dir: Path = PARSED_DIR) -> list[tuple[str, str]]:
    docs = []
    for p in sorted(parsed_dir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        docs.append((d["doc_id"], d["text"]))
    return docs


def build_chunks(chunker: str, parsed_dir: Path = PARSED_DIR) -> list[Chunk]:
    fn = CHUNKERS[chunker]
    return [c for doc_id, text in load_docs(parsed_dir) for c in fn(doc_id, text)]


def point_id(chunk: Chunk, seq: int) -> str:
    """Stable Qdrant id. `seq` keeps points distinct where data/parsed repeats a clause id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{chunk.chunk_id}|{seq}"))


def chunk_stats(chunks: list[Chunk]) -> dict:
    words = [len(c.text.split()) for c in chunks]
    counts = Counter(c.chunk_id for c in chunks)
    return {
        "chunks": len(chunks),
        "docs": len({c.doc_id for c in chunks}),
        "words_mean": round(mean(words), 1) if words else 0,
        "words_max": max(words, default=0),
        "duplicate_chunk_ids": sorted(i for i, n in counts.items() if n > 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunker", choices=list(CHUNKERS), required=True)
    ap.add_argument("--collection")
    ap.add_argument("--batch-size", type=int, default=None)
    ap.add_argument("--stats-only", action="store_true")
    args = ap.parse_args()

    chunks = build_chunks(args.chunker)
    stats = {"chunker": args.chunker, **chunk_stats(chunks)}
    print(json.dumps(stats, ensure_ascii=False))
    if args.stats_only:
        return
    if not args.collection:
        ap.error("--collection is required unless --stats-only")

    import torch
    from qdrant_client.models import Distance, PointStruct, VectorParams

    from rag.embedder import EMBEDDER, MAX_LEN, load_bge_m3
    from rag.vector_store import get_qdrant

    gpu = torch.cuda.is_available()
    t0 = time.time()
    model = load_bge_m3()
    stats["load_s"] = round(time.time() - t0, 1)

    texts = [c.text for c in chunks]
    n_tok = [len(x) for x in model.tokenizer(texts, add_special_tokens=True)["input_ids"]]
    stats["tokens_mean"] = round(mean(n_tok), 1)
    stats["truncated_over_max_len"] = sum(n > MAX_LEN for n in n_tok)
    batch = args.batch_size or (8 if args.chunker == "fixed" else 32)
    if gpu:
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    vecs = model.encode(texts, batch_size=batch, max_length=MAX_LEN)["dense_vecs"]
    stats["embed_s"] = round(time.time() - t0, 1)
    stats["chunks_per_s"] = round(len(chunks) / stats["embed_s"], 1)
    stats["vram_peak_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2) if gpu else None
    stats["device"] = torch.cuda.get_device_name(0) if gpu else "cpu"

    qd = get_qdrant()
    if qd.collection_exists(args.collection):
        qd.delete_collection(args.collection)
    qd.create_collection(args.collection,
                         vectors_config=VectorParams(size=vecs.shape[1], distance=Distance.COSINE))
    points = [PointStruct(id=point_id(c, i), vector=v.tolist(),
                          payload={"chunk_id": c.chunk_id, "doc_id": c.doc_id, "text": c.text,
                                   **c.metadata})
              for i, (c, v) in enumerate(zip(chunks, vecs))]
    for s in range(0, len(points), 256):
        qd.upsert(args.collection, points=points[s:s + 256])
    stats.update(collection=args.collection, points=qd.count(args.collection).count,
                 embedder=EMBEDDER, dim=int(vecs.shape[1]))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / f"{args.collection}.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
