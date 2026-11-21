"""Convert TV3's 30 pilot questions to docs/qa_schema.md v1.0.

Input : data/pilot/Pilot_30_cau_VN-Admin2025.xlsx (sheet "Bộ câu hỏi")
Output: data/benchmark/pilot_30_vinh.jsonl

Clause ids below were located by text search in data/parsed/*.json (branch feat/data,
commit 55198ab). They are NOT verified by two annotators yet: every record keeps
verified=false.

Usage:  python scripts/build_pilot_30_vinh.py [--parsed data/parsed]
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import openpyxl

from eval.qa_schema import TODO_CLAUSE, load_clause_ids, recall_gold_ids, validate_records

XLSX = Path("data/pilot/Pilot_30_cau_VN-Admin2025.xlsx")
OUT = Path("data/benchmark/pilot_30_vinh.jsonl")
REF_DATE = "2026-11-19"
VERSION = "pilot-0.2"

CAT = {"A": "A_direct", "B": "B_obsolete_trap", "C": "C_multihop_spatial", "D": "D_before_after"}

NQ202 = "NQ-202-2025-QH15"
L72 = "LUAT-72-2025-QH15"
HN, HCM = "NQ-1656-2025-UBTVQH15", "NQ-1685-2025-UBTVQH15"


def cid(doc: str, art: int, cl: int) -> str:
    return f"{doc}#D{art}.K{cl}"


# code -> (answer-bearing clause ids, supporting-only clause ids, extra citations, note)
EVIDENCE: dict[str, tuple[list[str], list[str], list[tuple[str | None, str]], str]] = {
    "A01": ([cid(NQ202, 1, 24)], [], [], ""),
    "A02": ([cid(NQ202, 1, 14)], [], [], ""),
    "A03": ([cid(NQ202, 1, 12)], [], [], ""),
    "A04": ([cid(NQ202, 1, 16)], [], [], ""),
    "A05": ([cid(NQ202, 1, 16)], [], [], ""),
    "A06": ([cid(NQ202, 1, 24)], [], [], ""),
    "A07": ([cid(NQ202, 1, 24)], [], [
        (None, "NQ thành lập TP Huế trực thuộc trung ương (2024) [TODO_VERIFY số hiệu; sheet ghi NQ 1314/NQ-UBTVQH15]"),
    ], "K24 nêu 6 thành phố và Hà Nội, Huế; mốc Huế lên TP trực thuộc TW (01/01/2025) chưa có văn bản trong kho."),
    "A08": ([], [], [
        ("NQ-76-2025-UBTVQH15", "NQ 76/2025/UBTVQH15 (chưa có trong data/parsed)"),
        (None, "Các NQ sắp xếp cấp xã của từng tỉnh; thông cáo của Chính phủ [TODO_VERIFY]"),
    ], "Số 3.321 / 2.621 / 687 / 13 chưa tìm được khoản nào trong kho nêu trực tiếp."),
    "B01": ([cid(L72, 51, 3), cid(L72, 1, 1)], [], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], ""),
    "B02": ([cid(L72, 51, 3), cid(L72, 1, 1), cid(HCM, 1, 122)], [], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], "K122: thị trấn Cần Thạnh + xã Long Hòa → xã Cần Giờ. Các xã mới khác ở khu vực Cần Giờ cũ chưa liệt kê."),
    "B03": ([cid(L72, 51, 3), cid(L72, 1, 1)], [cid(HCM, 1, 68)], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], "D51.K3 định nghĩa cấp huyện gồm cả 'thành phố thuộc thành phố trực thuộc Trung ương'."),
    "B04": ([cid(HN, 1, 1), cid(L72, 51, 3), cid(L72, 1, 1)], [], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], "NQ-1656 K1 do TV1 định vị (pilot_80, P-V-B04)."),
    "B05": ([cid(NQ202, 1, 1), cid(L72, 51, 3), cid("NQ-1684-2025-UBTVQH15", 1, 51)], [], [], ""),
    "B06": ([cid(L72, 51, 3), cid(HN, 1, 50)], [], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], ""),
    "B07": ([], [cid(NQ202, 1, 24)], [],
            "K24 chỉ xác nhận Quảng Ninh không sắp xếp; đường biên giới với Trung Quốc không có trong kho."),
    "B08": ([cid(HCM, 1, 163), cid(NQ202, 1, 16)], [], [], "NQ-1685 K163 do TV1 định vị (pilot_80, P-V-B08)."),
    "C01": ([cid(NQ202, 1, 12)], [cid("NQ-1664-2025-UBTVQH15", 1, 102)], [],
            "Phần 'trung tâm hành chính tỉnh Gia Lai đặt ở Quy Nhơn cũ' chưa có căn cứ trong kho."),
    "C02": ([cid(NQ202, 1, 3)], [], [],
            "Bước 'Hồ Ba Bể thuộc Bắc Kạn cũ' là kiến thức nền, không có trong kho."),
    "C03": ([cid(NQ202, 1, 10)], [cid("NQ-1659-2025-UBTVQH15", 1, 21)], [], ""),
    "C04": ([cid(NQ202, 1, 14), cid("NQ-1671-2025-UBTVQH15", 1, 119)], [], [],
            "K14 nêu Lâm Đồng giáp Biển Đông; K119 thành lập đặc khu Phú Quý."),
    "C05": ([cid(NQ202, 1, 11)], [], [],
            "K11 nêu Quảng Ngãi giáp Lào và Campuchia (giải quyết mục 'cần dò biên giới Campuchia')."),
    "C06": ([], [cid(NQ202, 1, 24)], [],
            "K24 chỉ xác nhận Quảng Ninh không sắp xếp; vị trí Vịnh Hạ Long không có trong kho."),
    "C07": ([cid("NQ-1654-2025-UBTVQH15", 1, 95), cid(NQ202, 1, 23)], [], [],
            "NQ-1654 K95 do TV1 định vị (pilot_80, P-V-C07)."),
    "D01": ([cid(L72, 1, 1), cid(L72, 51, 3)], [], [
        ("NQ-203-2025-QH15", "NQ 203/2025/QH15 (Hiến pháp sửa đổi) — chưa định vị khoản"),
    ], ""),
    "D02": ([cid(NQ202, 1, 14)], [], [], ""),
    "D03": ([cid(NQ202, 1, 9)], [], [],
            "Phần 'trung tâm hành chính đặt tại Đồng Hới cũ' chưa có căn cứ trong kho."),
    "D04": ([], [cid(NQ202, 1, 2)], [],
            "Đáp án cốt lõi là trung tâm hành chính (Yên Bái cũ): không có trong kho; K2 chỉ nêu việc hợp nhất."),
    "D05": ([], [cid(NQ202, 1, 5)], [],
            "Đáp án cốt lõi là trung tâm hành chính (Bắc Giang cũ): không có trong kho; K5 chỉ nêu việc hợp nhất."),
    "D06": ([cid(NQ202, 1, 24)], [], [], "K24 liệt kê thành phố Huế trong 11 đơn vị không sắp xếp."),
    "D07": ([cid(NQ202, 1, 8)], [], [], ""),
}

ANSWER_TYPE = {
    "A01": "number", "A02": "entity_list", "A03": "entity_list", "A04": "entity_list",
    "A05": "yes_no", "A06": "yes_no", "A07": "entity_list", "A08": "number",
    "B01": "premise_rejection", "B02": "premise_rejection", "B03": "premise_rejection",
    "B04": "premise_rejection", "B05": "premise_rejection", "B06": "premise_rejection",
    "B07": "entity", "B08": "entity",
    "C01": "entity", "C02": "entity", "C03": "entity", "C04": "yes_no",
    "C05": "entity_list", "C06": "entity", "C07": "free_text",
    "D01": "free_text", "D02": "free_text", "D03": "free_text", "D04": "free_text",
    "D05": "free_text", "D06": "yes_no", "D07": "free_text",
}

ENTITIES = {
    "A02": ["Lâm Đồng", "Đắk Nông", "Bình Thuận"], "A03": ["Gia Lai", "Bình Định"],
    "A04": ["Hồ Chí Minh", "Bình Dương", "Bà Rịa – Vũng Tàu"],
    "A07": ["Hà Nội", "Huế", "Hải Phòng", "Đà Nẵng", "Hồ Chí Minh", "Cần Thơ"],
    "B01": ["Hà Nội"], "B02": ["Hồ Chí Minh"], "B03": ["Hồ Chí Minh"], "B04": ["Hà Nội"],
    "B05": ["Tuyên Quang"], "B06": ["Hà Nội"], "B07": ["Trung Quốc"], "B08": ["Hồ Chí Minh"],
    "C01": ["Gia Lai"], "C02": ["Thái Nguyên"], "C03": ["Đà Nẵng"], "C05": ["Lào", "Campuchia"],
    "C06": ["Quảng Ninh"], "C07": ["đặc khu Phú Quốc", "An Giang"],
}

DUPLICATE_OF = {"B08": "P-T-C07", "C07": "P-T-C06"}

_NON_LEXICAL = re.compile(r"^(chỉ nêu|nói như)\b", re.IGNORECASE)
_PAREN = re.compile(r"\s*\([^)]*\)")


def nfc(s: Any) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip()


def split_kw(s: Any) -> list[str]:
    out = []
    for part in re.split(r";\s*", nfc(s)):
        part = _PAREN.sub("", part).strip()
        if part and part != "—" and not _NON_LEXICAL.match(part):
            out.append(part)
    return out


def citation(clause_id: str) -> str:
    doc, rest = clause_id.split("#")
    art, cl = rest[1:].split(".K")
    kind, num, year, body = doc.split("-")
    if kind == "LUAT":
        ref = f"Luật {num}/{year}/{body}"
    elif body == "QH15":
        ref = f"NQ {num}/{year}/{body}"
    else:
        ref = f"NQ {num}/NQ-{body}"
    return f"{ref}, Điều {art}, khoản {cl}"


def evidence_item(clause_id: str, known: set[str] | None) -> dict[str, Any]:
    doc, rest = clause_id.split("#")
    art, cl = rest[1:].split(".K")
    return {"doc_id": doc, "article": art, "clause": cl, "clause_id": clause_id,
            "citation": citation(clause_id),
            "in_corpus": clause_id in known if known is not None else True}


def build(row: tuple, known: set[str] | None) -> dict[str, Any]:
    code = nfc(row[0])
    role = "control" if nfc(row[3]) == "Đối chứng" else "trap"
    prov = nfc(row[4]).replace("TP ", "")
    gold_ids, support_ids, extra, ev_note = EVIDENCE[code]
    evidence = [evidence_item(c, known) for c in gold_ids + support_ids]
    evidence += [{"doc_id": d, "article": None, "clause": None, "clause_id": None,
                  "citation": c, "in_corpus": False} for d, c in extra]
    if not evidence:
        evidence = [{"doc_id": None, "article": None, "clause": None, "clause_id": None,
                     "citation": nfc(row[12]) + " [TODO_VERIFY]", "in_corpus": False}]
    certainty = nfc(row[13])
    notes = [n for n in (f"Sheet: {certainty}." if certainty != "Chắc" else "", ev_note) if n]
    rec: dict[str, Any] = {
        "id": f"P-V-{code}", "source_set": "vinh30", "source_id": code,
        "category": CAT[nfc(row[1])], "subtype": None, "item_role": role,
        "question": nfc(row[6]), "reference_date": REF_DATE,
        "gold_answer": {"text": nfc(row[7]), "aliases": split_kw(row[8]),
                        "answer_type": ANSWER_TYPE[code], "entities": ENTITIES.get(code, [])},
        "obsolete_answer": {"text": "" if role == "control" else nfc(row[9]),
                            "obsolete_entities": [] if role == "control" else split_kw(row[10])},
        "evidence": evidence,
        "gold_clause_ids": gold_ids or [TODO_CLAUSE],
        "source_url": "",
        "province_new": None if prov.startswith("(") else prov,
        "province_is_control": {"Có": True, "Không": False}.get(nfc(row[5])),
        "hops": 2 if code.startswith("C") else None,
        "difficulty": None, "annotator": ["TV3"],
        "verified": False, "verification_note": " ".join(notes), "version": VERSION,
    }
    if code in DUPLICATE_OF:
        rec["duplicate_of"] = DUPLICATE_OF[code]
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=XLSX)
    ap.add_argument("--parsed", type=Path, default=Path("data/parsed"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    known = load_clause_ids(args.parsed) if args.parsed.is_dir() else set()
    known_or_none = known or None
    if known_or_none is None:
        print(f"WARNING: {args.parsed} empty — clause ids not checked against the corpus")

    ws = openpyxl.load_workbook(args.xlsx, read_only=True)["Bộ câu hỏi"]
    recs = [build(r, known_or_none) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
    bad = validate_records(recs, known_or_none)
    if bad:
        raise SystemExit("\n".join(f"{k}: {'; '.join(v)}" for k, v in bad.items()))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="\n") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    todo = [r["id"] for r in recs if recall_gold_ids(r) is None]
    print(f"{len(recs)} records → {args.out}; Recall@k-ready {len(recs) - len(todo)}; "
          f"{TODO_CLAUSE}: {', '.join(todo) or '-'}")


if __name__ == "__main__":
    main()
