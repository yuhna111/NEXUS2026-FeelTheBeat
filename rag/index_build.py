"""Build Qdrant collections with BGE-M3 (Week 2, TV2).

Usage:
    python -m rag.index_build --chunker fixed --collection vnadmin_fixed
    python -m rag.index_build --chunker legal --collection vnadmin_legal
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag.chunkers import fixed_chunks, legal_chunks

PARSED_DIR = Path("data/parsed")


def load_docs() -> list[tuple[str, str]]:
    docs = []
    for p in sorted(PARSED_DIR.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        docs.append((d["doc_id"], d["text"]))
    return docs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunker", choices=["fixed", "legal"], required=True)
    ap.add_argument("--collection", required=True)
    args = ap.parse_args()

    chunk_fn = fixed_chunks if args.chunker == "fixed" else legal_chunks
    chunks = [c for doc_id, text in load_docs() for c in chunk_fn(doc_id, text)]
    print(f"{len(chunks)} chunks")

    # TODO(TV2): embed with FlagEmbedding BGEM3FlagModel and upsert into Qdrant.
    raise NotImplementedError("Embedding + Qdrant upsert — Week 2")


if __name__ == "__main__":
    main()
