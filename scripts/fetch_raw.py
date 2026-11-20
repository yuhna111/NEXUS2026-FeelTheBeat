"""Download the legal PDFs listed in data/raw/manifest.csv and convert them to Markdown.

PDFs are not committed (see .gitignore); this script rebuilds them from `source_url`
and checks each against the manifest's SHA-256, so every teammate works on identical files.

Scanned PDFs (no text layer) are OCR'd with EasyOCR. OCR output is a DRAFT: it contains
diacritic and punctuation errors and must be proofread before any gold answer relies on it.
The manifest `file` column says where each Markdown file is written.

    python scripts/fetch_raw.py            # download missing PDFs, convert missing Markdown
    python scripts/fetch_raw.py --force    # re-convert Markdown even if it exists

Requires the `rag` extra (pymupdf4llm) and, for scanned PDFs, the `ocr` extra (easyocr).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

import httpx

RAW = Path("data/raw")
PDF_DIR = RAW / "pdf"
MANIFEST = RAW / "manifest.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (research corpus fetcher)"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MIN_CHARS_PER_PAGE = 200  # below this the PDF is treated as a scan
_reader = None


def lines_from_boxes(boxes: list) -> str:
    """Rebuild text lines from EasyOCR boxes [(quad, text, conf), ...] by vertical position."""
    items = []
    for quad, text, _conf in boxes:
        ys, xs = [pt[1] for pt in quad], [pt[0] for pt in quad]
        items.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), text))
    if not items:
        return ""
    items.sort()
    heights = sorted(h for _, _, h, _ in items)
    tol = 0.6 * heights[len(heights) // 2]
    lines, current, anchor = [], [], None
    for y, x, _h, text in items:
        if anchor is not None and y - anchor > tol:
            lines.append(current)
            current = []
        current.append((x, text))
        anchor = y if len(current) == 1 else anchor
    lines.append(current)
    return "\n".join(" ".join(t for _, t in sorted(line)) for line in lines)


def ocr_pdf(pdf: Path) -> str:
    global _reader
    import easyocr
    import numpy as np
    import pymupdf

    if _reader is None:
        _reader = easyocr.Reader(["vi"], verbose=False)
    pages = []
    for page in pymupdf.open(pdf):
        pm = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
        img = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
        pages.append(lines_from_boxes(_reader.readtext(img)))
    return "\n\n".join(pages)


def pdf_to_text(pdf: Path) -> tuple[str, str]:
    """Return (text, method) where method is 'text-layer' or 'ocr'."""
    import pymupdf
    import pymupdf4llm

    n_pages = len(pymupdf.open(pdf))
    text = pymupdf4llm.to_markdown(str(pdf), show_progress=False)
    if len(text) >= MIN_CHARS_PER_PAGE * n_pages:
        return text, "text-layer"
    return ocr_pdf(pdf), "ocr"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-convert existing Markdown")
    args = ap.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    failures = 0
    for row in rows:
        doc_id, url = row["doc_id"], row["source_url"]
        if not url.lower().endswith(".pdf"):
            continue
        pdf = PDF_DIR / f"{doc_id}.pdf"
        if not pdf.exists():
            r = httpx.get(url, headers=HEADERS, timeout=120, follow_redirects=True)
            r.raise_for_status()
            pdf.write_bytes(r.content)
        digest = sha256(pdf)
        if row["sha256"] and digest != row["sha256"]:
            print(f"SHA-256 KHÔNG KHỚP {doc_id}: {digest} (manifest: {row['sha256']})", file=sys.stderr)
            failures += 1
            continue

        md = RAW / row["file"]
        method = "đã có"
        if args.force or not md.exists():
            text, method = pdf_to_text(pdf)
            md.parent.mkdir(parents=True, exist_ok=True)
            md.write_text(text, encoding="utf-8")
        print(f"{doc_id}: {md} ({len(md.read_text(encoding='utf-8')):,} ký tự, {method})", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
