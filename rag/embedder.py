"""BGE-M3 loader shared by index_build and DenseRetriever (Week 2, TV2)."""
from __future__ import annotations

EMBEDDER = "BAAI/bge-m3"
MAX_LEN = 1024  # BGE-M3 tokens; longer chunks are truncated (index_build reports how many)


def load_bge_m3(name: str = EMBEDDER):
    import torch
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel(name, use_fp16=torch.cuda.is_available())
