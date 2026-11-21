"""Chunkers (Week 2, TV2).

- fixed_chunks: 512 tokens, overlap 64 (config C1)
- legal_chunks: one chunk per Khoản, with parent Điều title as metadata (C2–C4)

chunk_id of a legal chunk is the clause id used in data/parsed and the benchmark
(`<doc_id>#D<điều>.K<khoản>`; an Điều without Khoản is `<doc_id>#D<điều>`), so
Recall@k compares ids directly. Fixed chunks are `<doc_id>#fixed<i>`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def fixed_chunks(doc_id: str, text: str, size: int = 512, overlap: int = 64) -> list[Chunk]:
    """Whitespace-token sliding window. Swap in the embedder's tokenizer if needed."""
    tokens = text.split()
    step = size - overlap
    out: list[Chunk] = []
    for i, start in enumerate(range(0, max(len(tokens), 1), step)):
        piece = tokens[start : start + size]
        if not piece:
            break
        out.append(Chunk(f"{doc_id}#fixed{i}", doc_id, " ".join(piece), {"start_token": start}))
        if start + size >= len(tokens):
            break
    return out


_DIEU = re.compile(r"^\s*Điều\s+(\d+[a-z]?)\.?\s*(.*)$", re.MULTILINE)
_KHOAN = re.compile(r"^\s*(\d+)\.\s+", re.MULTILINE)


def legal_chunks(doc_id: str, text: str) -> list[Chunk]:
    """Split by Điều, then by Khoản. Each chunk is prefixed with its Điều heading."""
    out: list[Chunk] = []
    dieu_matches = list(_DIEU.finditer(text))
    for di, m in enumerate(dieu_matches):
        article, title = m.group(1), m.group(2).strip()
        end = dieu_matches[di + 1].start() if di + 1 < len(dieu_matches) else len(text)
        body = text[m.end() : end]
        khoans = list(_KHOAN.finditer(body))
        header = f"Điều {article}. {title}".strip()
        if not khoans:
            out.append(Chunk(f"{doc_id}#D{article}", doc_id, f"{header}\n{body.strip()}",
                             {"article": article, "clause": None, "article_title": title}))
            continue
        for ki, k in enumerate(khoans):
            kend = khoans[ki + 1].start() if ki + 1 < len(khoans) else len(body)
            clause = k.group(1)
            out.append(Chunk(f"{doc_id}#D{article}.K{clause}", doc_id,
                             f"{header}\n{body[k.start():kend].strip()}",
                             {"article": article, "clause": clause, "article_title": title}))
    return out
