"""Split every legal text in data/raw/*.md (34 commune-level resolutions + framework
documents) into
Điều → Khoản JSON (data/parsed/<doc_id>.json).

Each clause gets a stable id  <doc_id>#D<article>.K<clause>  that the benchmark
cites in `evidence` and the RAG pipeline uses as chunk id.

Usage:  python scripts/parse_resolutions.py
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

RAW = Path("data/raw")
OUT = Path("data/parsed")

_NEXT = r"(?=(?:xã|phường|thị trấn|đặc khu|các|toàn|một|phần|huyện|quận|của|\d|[A-ZĐ]))"
_GLUED = re.compile(r"(xếp|của|là|số|gồm|và|thành)" + _NEXT)
ARTICLE_RE = re.compile(r"^Điều\s+(\d+)(?:\.\s*(.*)|\s*)$")
CHAPTER_RE = re.compile(r"^(Chương\s+[IVXLC]+|Mục\s+\d+)\b")
CLAUSE_RE = re.compile(r"^(\d+)\.\s*(.*)$")


def clean(line: str) -> str:
    """NFC, collapse spaces, re-insert spaces the web source dropped."""
    s = unicodedata.normalize("NFC", line).replace(" ", " ")
    s = _GLUED.sub(r"\1 ", s)
    s = re.sub(r",(?=[^\s\d])", ", ", s)
    s = re.sub(r"(xã|phường|các|thị trấn|đặc khu)(?=[A-ZĐÂĂÊÔƠƯÁÀẢÃẠÉÈÍÌÓÒÚÙÝ]|xã|phường)", r"\1 ", s)
    s = re.sub(r"(?<=\S)thành (?=(?:xã|phường|đặc khu) )", " thành ", s)
    s = re.sub(r"tự nhiên(?:,| và)? quy mô", "tự nhiên, quy mô", s)
    s = re.sub(r"\bcủa(?: của)+\b", "của", s)
    s = re.sub(r"(?<=[^\s(])\(", " (", s)
    s = re.sub(r"\)(?=[^\s.,;:)])", ") ", s)
    s = re.sub(r"(lại|tại)(?=của|khoản|các)", r"\1 ", s)
    s = re.sub(r"(?<=[^\s])và (?=(?:các|xã|phường|thị trấn) )", " và ", s)
    # typos in the published text
    s = s.replace("quy mô dân của", "quy mô dân số của")
    s = s.replace("Sắp xếp bộ diện tích", "Sắp xếp toàn bộ diện tích")
    s = re.sub(r"quy mô dân số (?=(?:xã|phường|thị trấn|các|huyện|Phường) )", "quy mô dân số của ", s)
    s = s.replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def parse_file(path: Path, meta: dict) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    source = ""
    if lines and lines[0].startswith("<!-- source:"):
        source = lines[0].split("source:")[1].split("|")[0].strip()
    articles: list[dict] = []
    cur_art = None
    cur_clause = None
    chapter = ""
    seen: set[str] = set()
    for raw in lines[1:]:
        line = clean(raw)
        if not line:
            continue
        if CHAPTER_RE.match(line):
            chapter, cur_art, cur_clause = line, None, None
            continue
        m = ARTICLE_RE.match(line)
        if m and m.group(1) in seen and cur_clause is not None:
            cur_clause["text"] += " " + line
            continue
        if m:
            seen.add(m.group(1))
            cur_art = {"article": m.group(1), "title": m.group(2) or "", "intro": "",
                       "chapter": chapter, "clauses": []}
            articles.append(cur_art)
            cur_clause = None
            continue
        if cur_art is None:
            continue
        # body ends at the signature / distribution list
        if line.startswith(("Nghị quyết này được", "Nơi nhận", "TM.", "Tham khảo")):
            cur_art = None
            continue
        m = CLAUSE_RE.match(line)
        if m:
            cur_clause = {"clause": m.group(1), "text": m.group(2)}
            cur_art["clauses"].append(cur_clause)
        elif cur_clause is None:
            cur_art["intro"] = (cur_art["intro"] + " " + line).strip()
        else:
            cur_clause["text"] += " " + line
    doc_id = path.stem
    for a in articles:
        for c in a["clauses"]:
            c["id"] = f"{doc_id}#D{a['article']}.K{c['clause']}"
    return {
        "doc_id": doc_id,
        "doc_number": meta.get("doc_number", ""),
        "title": meta.get("title", ""),
        "issuer": meta.get("issuer", ""),
        "issued_date": meta.get("issued_date", ""),
        "effective_date": meta.get("effective_date", ""),
        "province": meta.get("province", ""),
        "source_url": source or meta.get("source_url", ""),
        "articles": articles,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with open(RAW / "manifest.csv", encoding="utf-8") as f:
        manifest = {r["doc_id"]: r for r in csv.DictReader(f)}
    n_files = n_clauses = 0
    for path in sorted(RAW.glob("*.md")):
        doc = parse_file(path, manifest.get(path.stem, {}))
        (OUT / f"{path.stem}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        n_files += 1
        n_clauses += sum(len(a["clauses"]) for a in doc["articles"])
    print(f"parsed {n_files} files, {n_clauses} clauses → {OUT}/")


if __name__ == "__main__":
    main()
