"""Merge the two pilot sets into one JSONL following docs/qa_schema.md.

Inputs : data/pilot/pilot_50_toan.csv            (TV1, exported from Google Sheet)
         data/pilot/Pilot_30_cau_VN-Admin2025.xlsx (TV3)
Outputs: data/benchmark/pilot_80.jsonl
         data/benchmark/pilot_80_report.md       (evidence coverage, duplicates, open issues)

Usage:  python scripts/build_pilot_jsonl.py
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
from pathlib import Path

import openpyxl

PILOT = Path("data/pilot")
BENCH = Path("data/benchmark")
PARSED = Path("data/parsed")
REF_DATE = "2026-11-19"
VERSION = "pilot-0.1"

CAT_TOAN = {"A": "A_direct", "B": "A_direct", "C": "A_direct", "D": "E_procedure",
            "E": "B_obsolete_trap", "F": "F_rumor"}
SUB_TOAN = {"A": "province", "B": "commune", "C": "two_tier_structure", "D": "procedure",
            "E": "false_premise", "F": "debunked_rumor"}
CAT_VINH = {"A": "A_direct", "B": "B_obsolete_trap", "C": "C_multihop_spatial",
            "D": "D_before_after"}
DIFF = {"Dễ": "easy", "Trung bình": "medium", "Khó": "hard"}

# Clauses located in data/processed/commune_lineage.csv (TV1, 19/11) — overrides the
# coarser citation written in the source sheets. (doc number, [clauses], note)
LINEAGE_EVIDENCE = {
    "P-T-B02": ("1656", ["127"], ""),
    "P-T-B04": ("1656", ["1"], "Sheet ghi khoản 43 là sai: phường Hoàn Kiếm ở khoản 1. "
                                "NQ không nêu phường giáp ranh → phần 'giáp với' chưa có căn cứ."),
    "P-T-B05": ("1671", ["96", "97", "98"], "NQ không ghi tên huyện cũ; việc 3 xã này "
                                             "thuộc huyện Đắk R'lấp cũ cần nguồn khác."),
    "P-T-B06": ("1687", ["110"], ""),
    "P-T-B07": ("1663", ["77"], ""),
    "P-T-B08": ("1687", ["17"], ""),
    "P-T-C05": ("1667", ["65"], ""),
    "P-T-C06": ("1654", ["95"], ""),
    "P-T-C07": ("1685", ["163"], ""),
    "P-T-E01": ("1656", ["1"], ""),
    "P-T-E07": ("1671", ["119"], ""),
    "P-V-B04": ("1656", ["1"], ""),
    "P-V-B08": ("1685", ["163"], ""),
    "P-V-C07": ("1654", ["95"], ""),
}

NQ_RE = re.compile(r"NQ\s+(\d+)/(?:(\d{4})/)?(?:NQ-)?(QH15|UBTVQH15)"
                   r"(?:,\s*Điều\s+(\d+))?(?:,\s*khoản\s+(\d+))?")


def nfc(s) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip()


def clause_exists(clause_id: str) -> bool:
    doc_id = clause_id.split("#")[0]
    p = PARSED / f"{doc_id}.json"
    if not p.exists():
        return False
    doc = json.loads(p.read_text(encoding="utf-8"))
    return any(c["id"] == clause_id for a in doc["articles"] for c in a["clauses"])


def parse_citations(text: str) -> list[dict]:
    out = []
    for part in re.split(r";\s*", nfc(text)):
        if not part:
            continue
        m = NQ_RE.search(part)
        if m:
            num, year, body, art, cl = m.groups()
            year = year or "2025"
            doc_id = f"NQ-{num}-{year}-{body}"
            cid = f"{doc_id}#D{art}.K{cl}" if art and cl else None
            out.append({"doc_id": doc_id, "article": art, "clause": cl, "clause_id": cid,
                        "citation": part})
        else:
            out.append({"doc_id": None, "article": None, "clause": None, "clause_id": None,
                        "citation": part})
    return out


def lineage_evidence(qid: str) -> tuple[list[dict], str] | None:
    if qid not in LINEAGE_EVIDENCE:
        return None
    num, clauses, note = LINEAGE_EVIDENCE[qid]
    doc_id = f"NQ-{num}-2025-UBTVQH15"
    ev = [{"doc_id": doc_id, "article": "1", "clause": c, "clause_id": f"{doc_id}#D1.K{c}",
           "citation": f"NQ {num}/NQ-UBTVQH15, Điều 1, khoản {c}"} for c in clauses]
    return ev, note


def split_kw(s) -> list[str]:
    return [x.strip() for x in re.split(r";\s*", nfc(s)) if x.strip()]


def answer_type(gold: str, cat: str) -> str:
    if gold.startswith(("Phải chỉ ra", "Phải bác bỏ")) or cat == "F_rumor":
        return "premise_rejection"
    return "free_text"


def load_toan() -> list[dict]:
    recs = []
    with open(PILOT / "pilot_50_toan.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            grp = r["Nhóm"][0]
            qid = f"P-T-{r['ID']}"
            cat = CAT_TOAN[grp]
            gold = nfc(r["Đáp án chuẩn"])
            recs.append({
                "id": qid, "source_set": "toan50", "source_id": r["ID"],
                "category": cat, "subtype": SUB_TOAN[grp], "item_role": "trap",
                "question": nfc(r["Câu hỏi"]), "reference_date": REF_DATE,
                "gold_answer": {"text": gold, "aliases": [],
                                "answer_type": answer_type(gold, cat), "entities": []},
                "obsolete_answer": {"text": nfc(r["Dấu hiệu trả lời lỗi thời"]),
                                    "obsolete_entities": []},
                "evidence": parse_citations(r["Căn cứ pháp lý"]),
                "source_url": nfc(r["Nguồn tham khảo"]),
                "province_new": None, "province_is_control": None,
                "difficulty": DIFF.get(nfc(r["Độ khó"])), "annotator": [],
                "verified": False, "verification_note": "", "version": VERSION})
    return recs


def load_vinh() -> list[dict]:
    ws = openpyxl.load_workbook(PILOT / "Pilot_30_cau_VN-Admin2025.xlsx")["Bộ câu hỏi"]
    recs = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        code, grp = nfc(r[0]), nfc(r[1])
        cat = CAT_VINH[grp]
        prov = nfc(r[4]).replace("TP ", "")
        role = "control" if nfc(r[3]) == "Đối chứng" else "trap"
        gold = nfc(r[7])
        recs.append({
            "id": f"P-V-{code}", "source_set": "vinh30", "source_id": code,
            "category": cat, "subtype": None, "item_role": role,
            "question": nfc(r[6]), "reference_date": REF_DATE,
            "gold_answer": {"text": gold, "aliases": split_kw(r[8]),
                            "answer_type": answer_type(gold, cat), "entities": []},
            "obsolete_answer": {"text": "" if role == "control" else nfc(r[9]),
                                "obsolete_entities": [] if role == "control" else split_kw(r[10])},
            "evidence": parse_citations(r[12]),
            "source_url": "",
            "province_new": None if prov.startswith("(") else prov,
            "province_is_control": {"Có": True, "Không": False}.get(nfc(r[5])),
            "difficulty": None, "annotator": [],
            "verified": False, "verification_note": "", "version": VERSION})
    return recs


def main() -> None:
    recs = load_toan() + load_vinh()
    for r in recs:
        hit = lineage_evidence(r["id"])
        if hit:
            r["evidence"], r["verification_note"] = hit
        for e in r["evidence"]:
            e["in_corpus"] = bool(e["clause_id"]) and clause_exists(e["clause_id"])
    # near-duplicate questions across the two sets
    dups = []
    tq = [r for r in recs if r["source_set"] == "toan50"]
    vq = [r for r in recs if r["source_set"] == "vinh30"]
    for v in vq:
        best = max(tq, key=lambda t: difflib.SequenceMatcher(
            None, t["question"].lower(), v["question"].lower()).ratio())
        ratio = difflib.SequenceMatcher(None, best["question"].lower(),
                                        v["question"].lower()).ratio()
        if ratio >= 0.85:
            v["duplicate_of"] = best["id"]
            dups.append((v["id"], best["id"], round(ratio, 2)))
    BENCH.mkdir(parents=True, exist_ok=True)
    with open(BENCH / "pilot_80.jsonl", "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # report
    n = len(recs)
    by_cat: dict[str, int] = {}
    for r in recs:
        by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
    recall_ready = [r["id"] for r in recs if any(e["in_corpus"] for e in r["evidence"])]
    lines = [
        "# Báo cáo gộp bộ pilot (tự sinh bởi scripts/build_pilot_jsonl.py)", "",
        f"- Tổng: **{n} câu** (toan50: {len(tq)}, vinh30: {len(vq)})",
        "- Theo nhóm: " + ", ".join(f"{k} {v}" for k, v in sorted(by_cat.items())),
        f"- Câu `control`: {sum(r['item_role'] == 'control' for r in recs)}",
        f"- Câu có căn cứ là khoản **đã có trong kho** `data/parsed/` (dùng được cho Recall@k): "
        f"**{len(recall_ready)}** — {', '.join(recall_ready)}",
        "- Câu viện dẫn NQ 202/2025/QH15: có `clause_id` nhưng văn bản chưa vào kho "
        "(TV1 bổ sung tuần 2).",
        f"- Câu đã kiểm (`verified=true`): {sum(r['verified'] for r in recs)}", "",
        "## Câu gần như trùng chữ giữa hai bộ (độ giống ≥ 0,85)", "", "Câu trùng ý nhưng khác chữ (ví dụ cùng hỏi số tỉnh) cần người xem lại.", "",
        "| Câu TV3 | Gần giống câu TV1 | Độ giống |", "|---|---|---|",
        *[f"| {a} | {b} | {c} |" for a, b, c in dups], "",
        "## Ghi chú kiểm tra", "",
        *[f"- **{r['id']}**: {r['verification_note']}" for r in recs if r["verification_note"]],
        "", "## Còn thiếu", "",
        "- Bộ TV1 chưa có `aliases`, `obsolete_entities`, `province_new`.",
        "- Bộ TV1 chưa có câu `control`.",
        "- Toàn bộ 80 câu `verified=false`: cần 2 người đối chiếu văn bản gốc.",
    ]
    (BENCH / "pilot_80_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{n} questions → {BENCH/'pilot_80.jsonl'}; recall-ready {len(recall_ready)}; "
          f"duplicates {len(dups)}")


if __name__ == "__main__":
    main()
