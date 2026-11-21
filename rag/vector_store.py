"""Qdrant connection shared by index_build, retriever and notebooks.

Two modes, chosen by environment:
- QDRANT_PATH set  → embedded Qdrant stored in that folder (no Docker needed).
- otherwise        → Qdrant server at QDRANT_URL (docker compose up -d qdrant).

Collections built in one mode are not visible in the other.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()


def get_qdrant() -> QdrantClient:
    path = os.getenv("QDRANT_PATH")
    if path:
        return QdrantClient(path=path)
    return QdrantClient(url=os.getenv("QDRANT_URL", "http://localhost:6333"))
