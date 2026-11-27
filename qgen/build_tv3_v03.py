"""Soạn 60 câu hỏi nhóm C, D, F của TV3 cho bộ câu hỏi v0.3 (tuần 3).

Đầu vào:
  data/parsed/*.json (để kiểm tra mọi `gold_clause_ids` và trích dẫn chính xác)
  data/processed/entity_map_63_34_v1.csv (để chuẩn hóa tên tỉnh mới và cờ control)

Đầu ra:
  data/benchmark/tv3_v0.3.jsonl (60 câu: 26 C_multihop_spatial, 22 D_before_after, 12 F_rumor),
  tuân thủ docs/qa_schema.md v1.0.

Tất cả câu đều đặt `verified = false` để chờ TV1 kiểm chéo với văn bản gốc.

Chạy:
  python qgen/build_tv3_v03.py
"""
from __future__ import annotations

import collections
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REF_DATE = "2026-11-27"
VERSION = "v0.3"
TODO_CLAUSE = "TODO_VERIFY_CLAUSE"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


class Corpus:
    def __init__(self, parsed: Path):
        self.text: dict[str, str] = {}
        for f in sorted(parsed.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            for a in d["articles"]:
                for c in a["clauses"]:
                    cid = c.get("clause_id") or c.get("id")
                    self.text.setdefault(cid, c["text"])

    def ev(self, clause_id: str) -> dict[str, Any]:
        if clause_id not in self.text:
            raise KeyError(f"Clause ID not found in data/parsed: {clause_id}")
        doc, rest = clause_id.split("#")
        m = re.match(r"D(\d+[a-z]?)\.K(\d+[a-z]?)$", rest)
        if not m:
            raise ValueError(f"Unexpected clause_id format: {clause_id}")
        return {
            "doc_id": doc,
            "article": m.group(1),
            "clause": m.group(2),
            "clause_id": clause_id,
            "citation": cite(clause_id),
            "in_corpus": True,
        }


def cite(clause_id: str) -> str:
    doc, rest = clause_id.split("#")
    art, cl = re.match(r"D(\d+[a-z]?)\.K(\d+[a-z]?)$", rest).groups()
    m = re.match(r"(NQ|LUAT)-(\d+)-(\d{4})-(\w+)$", doc)
    kind, num, year, body = m.groups()
    if body == "UBTVQH15":
        name = f"NQ {num}/NQ-UBTVQH15" if int(num) > 1000 else f"NQ {num}/{year}/UBTVQH15"
    elif kind == "LUAT":
        name = f"Luật {num}/{year}/{body}"
    else:
        name = f"NQ {num}/{year}/{body}"
    return f"{name}, Điều {art}, khoản {cl}"


def ext_ev(citation: str, doc_id: str | None = None) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "article": None,
        "clause": None,
        "clause_id": None,
        "citation": citation,
        "in_corpus": False,
    }


def make_item(
    corpus: Corpus,
    ctrl_map: dict[str, bool],
    *,
    category: str,
    subtype: str,
    item_role: str = "trap",
    question: str,
    gold_text: str,
    answer_type: str,
    aliases: list[str] | None = None,
    entities: list[str] | None = None,
    obs_text: str = "",
    obs_entities: list[str] | None = None,
    gold_clauses: list[str] | None = None,
    extra_in_corpus: list[str] | None = None,
    extra_external: list[dict[str, Any]] | None = None,
    province_new: str | None = None,
    hops: int = 2,
    difficulty: str = "medium",
    source_url: str = "",
    note: str = "",
) -> dict[str, Any]:
    if province_new is not None and province_new not in ctrl_map:
        raise ValueError(f"Unknown province_new (not in entity_map): {province_new!r}")
    prov_ctrl = None if province_new is None else ctrl_map[province_new]

    if item_role == "control":
        obs_text = ""
        obs_entities = []

    evidence: list[dict[str, Any]] = []
    seen_cids: set[str] = set()
    for cid in (gold_clauses or []):
        if cid != TODO_CLAUSE and cid not in seen_cids:
            evidence.append(corpus.ev(cid))
            seen_cids.add(cid)
    for cid in (extra_in_corpus or []):
        if cid not in seen_cids:
            evidence.append(corpus.ev(cid))
            seen_cids.add(cid)
    for ext in (extra_external or []):
        evidence.append(ext)

    gids = list(gold_clauses) if gold_clauses else [TODO_CLAUSE]

    return {
        "id": None,
        "source_set": "vinh_v03",
        "source_id": None,
        "category": category,
        "subtype": subtype,
        "item_role": item_role,
        "question": nfc(question),
        "reference_date": REF_DATE,
        "gold_answer": {
            "text": nfc(gold_text),
            "aliases": [nfc(x) for x in (aliases or [])],
            "answer_type": answer_type,
            "entities": [nfc(x) for x in (entities or [])],
        },
        "obsolete_answer": {
            "text": nfc(obs_text),
            "obsolete_entities": [nfc(x) for x in (obs_entities or [])],
        },
        "evidence": evidence,
        "gold_clause_ids": gids,
        "source_url": source_url,
        "province_new": None if province_new is None else nfc(province_new),
        "province_is_control": prov_ctrl,
        "hops": hops,
        "difficulty": difficulty,
        "annotator": ["TV3"],
        "verified": False,
        "verification_note": nfc(note or "Soạn tay từ văn bản pháp lý gốc (TV3); chờ TV1 kiểm chéo."),
        "version": VERSION,
    }


def build_c(corpus: Corpus, ctrl: dict[str, bool]) -> list[dict[str, Any]]:
    """26 câu C_multihop_spatial: 22 trap + 4 control."""
    m = lambda **kw: make_item(corpus, ctrl, category="C_multihop_spatial", **kw)
    return [
        # --- C1: Địa danh / thành phố cũ / di sản -> tỉnh mới (12 câu trap) ---
        m(
            subtype="city_to_province",
            question="Thành phố Vũng Tàu trước đây hiện nay thuộc tỉnh, thành phố trực thuộc trung ương nào?",
            gold_text="Thành phố Hồ Chí Minh. Tỉnh Bà Rịa - Vũng Tàu đã hợp nhất với Thành phố Hồ Chí Minh và tỉnh Bình Dương thành Thành phố Hồ Chí Minh; khu vực Vũng Tàu cũ nay gồm các phường trực thuộc TP Hồ Chí Minh.",
            answer_type="entity",
            aliases=["Thành phố Hồ Chí Minh", "TP Hồ Chí Minh", "Hồ Chí Minh"],
            entities=["Hồ Chí Minh"],
            obs_text="Vũng Tàu là thành phố thuộc tỉnh Bà Rịa - Vũng Tàu.",
            obs_entities=["Bà Rịa - Vũng Tàu", "thành phố Vũng Tàu"],
            gold_clauses=["NQ-202-2025-QH15#D1.K16", "NQ-1685-2025-UBTVQH15#D1.K102"],
            province_new="Hồ Chí Minh",
            hops=2,
            difficulty="medium",
            note="NQ 202 K16 hợp nhất Bà Rịa - Vũng Tàu vào TP.HCM; NQ 1685 K102 thành lập phường Vũng Tàu thuộc TP.HCM. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Phan Rang - Tháp Chàm trước đây hiện nay thuộc tỉnh nào?",
            gold_text="Tỉnh Khánh Hòa. Tỉnh Ninh Thuận đã hợp nhất với tỉnh Khánh Hòa thành tỉnh Khánh Hòa từ ngày 01/07/2025; khu vực Phan Rang cũ nay là các phường (trong đó có phường Phan Rang) thuộc tỉnh Khánh Hòa.",
            answer_type="entity",
            aliases=["tỉnh Khánh Hòa", "Khánh Hòa"],
            entities=["Khánh Hòa"],
            obs_text="Phan Rang - Tháp Chàm là thành phố tỉnh lỵ của tỉnh Ninh Thuận.",
            obs_entities=["Ninh Thuận", "thành phố Phan Rang - Tháp Chàm"],
            gold_clauses=["NQ-202-2025-QH15#D1.K13", "NQ-1667-2025-UBTVQH15#D1.K60"],
            province_new="Khánh Hòa",
            hops=2,
            difficulty="medium",
            note="NQ 202 K13 hợp nhất Ninh Thuận vào Khánh Hòa; NQ 1667 K60 thành lập phường Phan Rang thuộc Khánh Hòa. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Tuy Hòa trước đây hiện nay thuộc tỉnh nào?",
            gold_text="Tỉnh Đắk Lắk. Tỉnh Phú Yên đã hợp nhất với tỉnh Đắk Lắk thành tỉnh Đắk Lắk từ ngày 01/07/2025; khu vực Tuy Hòa cũ nay là các phường (trong đó có phường Tuy Hòa) thuộc tỉnh Đắk Lắk.",
            answer_type="entity",
            aliases=["tỉnh Đắk Lắk", "Đắk Lắk"],
            entities=["Đắk Lắk"],
            obs_text="Tuy Hòa là thành phố tỉnh lỵ của tỉnh Phú Yên.",
            obs_entities=["Phú Yên", "thành phố Tuy Hòa"],
            gold_clauses=["NQ-202-2025-QH15#D1.K15", "NQ-1660-2025-UBTVQH15#D1.K90"],
            province_new="Đắk Lắk",
            hops=2,
            difficulty="medium",
            note="NQ 202 K15 hợp nhất Phú Yên vào Đắk Lắk; NQ 1660 K90 thành lập phường Tuy Hòa thuộc Đắk Lắk. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Rạch Giá trước đây hiện nay thuộc tỉnh nào?",
            gold_text="Tỉnh An Giang. Tỉnh Kiên Giang đã hợp nhất với tỉnh An Giang thành tỉnh An Giang từ ngày 01/07/2025; khu vực Rạch Giá cũ nay là phường Rạch Giá thuộc tỉnh An Giang.",
            answer_type="entity",
            aliases=["tỉnh An Giang", "An Giang"],
            entities=["An Giang"],
            obs_text="Rạch Giá là thành phố tỉnh lỵ của tỉnh Kiên Giang.",
            obs_entities=["Kiên Giang", "thành phố Rạch Giá"],
            gold_clauses=["NQ-202-2025-QH15#D1.K23", "NQ-1654-2025-UBTVQH15#D1.K91"],
            province_new="An Giang",
            hops=2,
            difficulty="medium",
            note="NQ 202 K23 hợp nhất Kiên Giang vào An Giang; NQ 1654 K91 thành lập phường Rạch Giá thuộc An Giang. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Mỹ Tho trước đây hiện nay thuộc tỉnh nào?",
            gold_text="Tỉnh Đồng Tháp. Tỉnh Tiền Giang đã hợp nhất với tỉnh Đồng Tháp thành tỉnh Đồng Tháp từ ngày 01/07/2025; khu vực Mỹ Tho cũ nay có phường Mỹ Tho thuộc tỉnh Đồng Tháp.",
            answer_type="entity",
            aliases=["tỉnh Đồng Tháp", "Đồng Tháp"],
            entities=["Đồng Tháp"],
            obs_text="Mỹ Tho là thành phố tỉnh lỵ của tỉnh Tiền Giang.",
            obs_entities=["Tiền Giang", "thành phố Mỹ Tho"],
            gold_clauses=["NQ-202-2025-QH15#D1.K21", "NQ-1663-2025-UBTVQH15#D1.K83"],
            province_new="Đồng Tháp",
            hops=2,
            difficulty="medium",
            note="NQ 202 K21 hợp nhất Tiền Giang vào Đồng Tháp; NQ 1663 K83 thành lập phường Mỹ Tho thuộc Đồng Tháp. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Bến Tre trước đây hiện nay thuộc tỉnh nào?",
            gold_text="Tỉnh Vĩnh Long. Tỉnh Bến Tre và tỉnh Trà Vinh đã hợp nhất với tỉnh Vĩnh Long thành tỉnh Vĩnh Long từ ngày 01/07/2025; khu vực Bến Tre cũ nay có phường Bến Tre thuộc tỉnh Vĩnh Long.",
            answer_type="entity",
            aliases=["tỉnh Vĩnh Long", "Vĩnh Long"],
            entities=["Vĩnh Long"],
            obs_text="Bến Tre là thành phố tỉnh lỵ của tỉnh Bến Tre.",
            obs_entities=["tỉnh Bến Tre", "thành phố Bến Tre"],
            gold_clauses=["NQ-202-2025-QH15#D1.K20", "NQ-1687-2025-UBTVQH15#D1.K118"],
            province_new="Vĩnh Long",
            hops=2,
            difficulty="medium",
            note="NQ 202 K20 hợp nhất Bến Tre, Trà Vinh, Vĩnh Long; NQ 1687 K118 thành lập phường Bến Tre thuộc Vĩnh Long. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="city_to_province",
            question="Thành phố Sóc Trăng trước đây hiện nay thuộc tỉnh, thành phố trực thuộc trung ương nào?",
            gold_text="Thành phố Cần Thơ. Tỉnh Sóc Trăng và tỉnh Hậu Giang đã hợp nhất với thành phố Cần Thơ thành thành phố Cần Thơ từ ngày 01/07/2025; khu vực Sóc Trăng cũ nay có phường Sóc Trăng thuộc thành phố Cần Thơ.",
            answer_type="entity",
            aliases=["thành phố Cần Thơ", "Cần Thơ"],
            entities=["Cần Thơ"],
            obs_text="Sóc Trăng là thành phố tỉnh lỵ của tỉnh Sóc Trăng.",
            obs_entities=["tỉnh Sóc Trăng", "thành phố Sóc Trăng"],
            gold_clauses=["NQ-202-2025-QH15#D1.K19", "NQ-1668-2025-UBTVQH15#D1.K24"],
            province_new="Cần Thơ",
            hops=2,
            difficulty="medium",
            note="NQ 202 K19 hợp nhất Cần Thơ, Sóc Trăng, Hậu Giang; NQ 1668 K24 thành lập phường Sóc Trăng thuộc Cần Thơ. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="landmark_to_province",
            question="Vườn quốc gia Phong Nha - Kẻ Bàng hiện nằm trên địa bàn tỉnh nào?",
            gold_text="Tỉnh Quảng Trị. Tỉnh Quảng Bình (nơi có Vườn quốc gia Phong Nha - Kẻ Bàng) đã hợp nhất với tỉnh Quảng Trị thành tỉnh Quảng Trị từ ngày 01/07/2025.",
            answer_type="entity",
            aliases=["tỉnh Quảng Trị", "Quảng Trị"],
            entities=["Quảng Trị"],
            obs_text="Vườn quốc gia Phong Nha - Kẻ Bàng thuộc tỉnh Quảng Bình.",
            obs_entities=["Quảng Bình"],
            gold_clauses=["NQ-202-2025-QH15#D1.K9", "NQ-1680-2025-UBTVQH15#D1.K19"],
            province_new="Quảng Trị",
            hops=2,
            difficulty="medium",
            note="Bước 'Phong Nha - Kẻ Bàng ở Quảng Bình cũ' là kiến thức nền; NQ 202 K9 hợp nhất Quảng Bình vào Quảng Trị, NQ 1680 K19 thành lập xã Phong Nha thuộc Quảng Trị. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="landmark_to_province",
            question="Cao nguyên đá Đồng Văn hiện nằm trên địa bàn tỉnh nào?",
            gold_text="Tỉnh Tuyên Quang. Tỉnh Hà Giang (nơi có Cao nguyên đá Đồng Văn) đã hợp nhất với tỉnh Tuyên Quang thành tỉnh Tuyên Quang từ ngày 01/07/2025.",
            answer_type="entity",
            aliases=["tỉnh Tuyên Quang", "Tuyên Quang"],
            entities=["Tuyên Quang"],
            obs_text="Cao nguyên đá Đồng Văn thuộc tỉnh Hà Giang.",
            obs_entities=["Hà Giang", "huyện Đồng Văn"],
            gold_clauses=["NQ-202-2025-QH15#D1.K1"],
            province_new="Tuyên Quang",
            hops=2,
            difficulty="medium",
            note="Bước 'Cao nguyên đá Đồng Văn ở Hà Giang cũ' là kiến thức nền; NQ 202 K1 hợp nhất Hà Giang vào Tuyên Quang. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="landmark_to_province",
            question="Khu di tích Thánh địa Mỹ Sơn hiện nằm trên địa bàn tỉnh, thành phố nào?",
            gold_text="Thành phố Đà Nẵng. Tỉnh Quảng Nam (nơi có Thánh địa Mỹ Sơn) đã hợp nhất với thành phố Đà Nẵng thành thành phố Đà Nẵng từ ngày 01/07/2025.",
            answer_type="entity",
            aliases=["thành phố Đà Nẵng", "Đà Nẵng"],
            entities=["Đà Nẵng"],
            obs_text="Thánh địa Mỹ Sơn thuộc huyện Duy Xuyên, tỉnh Quảng Nam.",
            obs_entities=["Quảng Nam", "huyện Duy Xuyên"],
            gold_clauses=["NQ-202-2025-QH15#D1.K10"],
            province_new="Đà Nẵng",
            hops=2,
            difficulty="medium",
            note="Bước 'Thánh địa Mỹ Sơn ở Quảng Nam cũ' là kiến thức nền; NQ 202 K10 hợp nhất Quảng Nam vào TP Đà Nẵng. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="landmark_to_province",
            question="Khu du lịch núi Bà Đen và địa bàn tỉnh Long An cũ hiện nay có cùng thuộc một tỉnh không? Nếu có thì là tỉnh nào?",
            gold_text="Có, cùng thuộc tỉnh Tây Ninh. Tỉnh Long An và tỉnh Tây Ninh đã hợp nhất thành tỉnh Tây Ninh từ ngày 01/07/2025.",
            answer_type="entity",
            aliases=["Có", "tỉnh Tây Ninh", "Tây Ninh"],
            entities=["Tây Ninh"],
            obs_text="Không, núi Bà Đen thuộc tỉnh Tây Ninh còn Long An là một tỉnh riêng.",
            obs_entities=["tỉnh Long An"],
            gold_clauses=["NQ-202-2025-QH15#D1.K18"],
            province_new="Tây Ninh",
            hops=2,
            difficulty="hard",
            note="NQ 202 K18 hợp nhất Long An và Tây Ninh thành tỉnh Tây Ninh. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="landmark_to_province",
            question="Hồ thủy điện Hòa Bình và Khu di tích Đền Hùng hiện nay có nằm trong cùng một tỉnh không? Nếu có thì là tỉnh nào?",
            gold_text="Có, cùng thuộc tỉnh Phú Thọ. Tỉnh Vĩnh Phúc, tỉnh Hòa Bình và tỉnh Phú Thọ đã hợp nhất thành tỉnh Phú Thọ từ ngày 01/07/2025.",
            answer_type="entity",
            aliases=["Có", "tỉnh Phú Thọ", "Phú Thọ"],
            entities=["Phú Thọ"],
            obs_text="Không, Hồ Hòa Bình thuộc tỉnh Hòa Bình còn Đền Hùng thuộc tỉnh Phú Thọ.",
            obs_entities=["tỉnh Hòa Bình"],
            gold_clauses=["NQ-202-2025-QH15#D1.K4"],
            province_new="Phú Thọ",
            hops=2,
            difficulty="hard",
            note="NQ 202 K4 hợp nhất Vĩnh Phúc, Hòa Bình và Phú Thọ thành tỉnh Phú Thọ. Chờ TV1 kiểm chéo.",
        ),
        # --- C2: Không gian mới — giáp biển / biên giới quốc tế / tiếp giáp tỉnh (10 câu trap) ---
        m(
            subtype="spatial_sea",
            question="Tỉnh Gia Lai hiện nay có giáp Biển Đông không? Vì sao?",
            gold_text="Có. Tỉnh Gia Lai mới được hợp nhất từ tỉnh Bình Định và tỉnh Gia Lai; theo Nghị quyết 202/2025/QH15, tỉnh Gia Lai giáp tỉnh Đắk Lắk, tỉnh Quảng Ngãi, Vương quốc Campuchia và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "giáp Biển Đông", "Bình Định"],
            entities=["Gia Lai"],
            obs_text="Không, Gia Lai là tỉnh Tây Nguyên không giáp biển.",
            obs_entities=["không giáp biển"],
            gold_clauses=["NQ-202-2025-QH15#D1.K12"],
            province_new="Gia Lai",
            hops=2,
            difficulty="medium",
            note="NQ 202 K12 nêu trực tiếp tỉnh Gia Lai giáp Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_sea",
            question="Tỉnh Đắk Lắk hiện nay có giáp Biển Đông không? Vì sao?",
            gold_text="Có. Tỉnh Đắk Lắk mới được hợp nhất từ tỉnh Phú Yên và tỉnh Đắk Lắk; theo Nghị quyết 202/2025/QH15, tỉnh Đắk Lắk giáp Gia Lai, Khánh Hòa, Lâm Đồng, Vương quốc Campuchia và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "giáp Biển Đông", "Phú Yên"],
            entities=["Đắk Lắk"],
            obs_text="Không, Đắk Lắk là tỉnh Tây Nguyên không giáp biển.",
            obs_entities=["không giáp biển"],
            gold_clauses=["NQ-202-2025-QH15#D1.K15"],
            province_new="Đắk Lắk",
            hops=2,
            difficulty="medium",
            note="NQ 202 K15 nêu trực tiếp tỉnh Đắk Lắk giáp Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_sea",
            question="Tỉnh Hưng Yên hiện nay có giáp Biển Đông không? Vì sao?",
            gold_text="Có. Tỉnh Hưng Yên mới được hợp nhất từ tỉnh Thái Bình và tỉnh Hưng Yên; theo Nghị quyết 202/2025/QH15, tỉnh Hưng Yên giáp Bắc Ninh, Ninh Bình, Hà Nội, Hải Phòng và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "giáp Biển Đông", "Thái Bình"],
            entities=["Hưng Yên"],
            obs_text="Không, Hưng Yên là tỉnh đồng bằng sông Hồng nằm trong nội địa, không giáp biển.",
            obs_entities=["không giáp biển"],
            gold_clauses=["NQ-202-2025-QH15#D1.K6"],
            province_new="Hưng Yên",
            hops=2,
            difficulty="medium",
            note="NQ 202 K6 nêu trực tiếp tỉnh Hưng Yên giáp Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_sea",
            question="Thành phố Cần Thơ hiện nay có giáp Biển Đông không? Vì sao?",
            gold_text="Có. Thành phố Cần Thơ mới được hợp nhất từ thành phố Cần Thơ, tỉnh Sóc Trăng và tỉnh Hậu Giang; theo Nghị quyết 202/2025/QH15, thành phố Cần Thơ giáp An Giang, Đồng Tháp, Cà Mau, Vĩnh Long và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "giáp Biển Đông", "Sóc Trăng"],
            entities=["Cần Thơ"],
            obs_text="Không, Cần Thơ nằm sâu trong vùng Đồng bằng sông Cửu Long, không giáp biển.",
            obs_entities=["không giáp biển"],
            gold_clauses=["NQ-202-2025-QH15#D1.K19"],
            province_new="Cần Thơ",
            hops=2,
            difficulty="medium",
            note="NQ 202 K19 nêu trực tiếp thành phố Cần Thơ giáp Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_sea",
            question="Tỉnh An Giang hiện nay có giáp Biển Đông không? Vì sao?",
            gold_text="Có. Tỉnh An Giang mới được hợp nhất từ tỉnh Kiên Giang và tỉnh An Giang; theo Nghị quyết 202/2025/QH15, tỉnh An Giang giáp Cà Mau, Đồng Tháp, Cần Thơ, Vương quốc Campuchia và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "giáp Biển Đông", "Kiên Giang"],
            entities=["An Giang"],
            obs_text="Không, An Giang là tỉnh đầu nguồn sông Cửu Long không giáp biển.",
            obs_entities=["không giáp biển"],
            gold_clauses=["NQ-202-2025-QH15#D1.K23"],
            province_new="An Giang",
            hops=2,
            difficulty="medium",
            note="NQ 202 K23 nêu trực tiếp tỉnh An Giang giáp Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_border",
            question="Tỉnh Tuyên Quang hiện nay có chung đường biên giới quốc tế với nước nào không?",
            gold_text="Có, giáp nước Cộng hòa Nhân dân Trung Hoa (Trung Quốc), vì tỉnh Hà Giang đã hợp nhất với tỉnh Tuyên Quang thành tỉnh Tuyên Quang.",
            answer_type="entity",
            aliases=["Trung Quốc", "Cộng hòa Nhân dân Trung Hoa"],
            entities=["Trung Quốc"],
            obs_text="Không, Tuyên Quang là tỉnh nội địa không có biên giới quốc tế.",
            obs_entities=["không có biên giới"],
            gold_clauses=["NQ-202-2025-QH15#D1.K1"],
            province_new="Tuyên Quang",
            hops=2,
            difficulty="medium",
            note="NQ 202 K1 nêu tỉnh Tuyên Quang giáp nước Cộng hòa Nhân dân Trung Hoa. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_border",
            question="Thành phố Đà Nẵng hiện nay có chung đường biên giới trên bộ với nước nào không?",
            gold_text="Có, giáp nước Cộng hòa Dân chủ Nhân dân Lào (Lào), vì tỉnh Quảng Nam đã hợp nhất với thành phố Đà Nẵng thành thành phố Đà Nẵng.",
            answer_type="entity",
            aliases=["Lào", "Cộng hòa Dân chủ Nhân dân Lào"],
            entities=["Lào"],
            obs_text="Không, Đà Nẵng không có biên giới trên bộ với nước ngoài.",
            obs_entities=["không có biên giới"],
            gold_clauses=["NQ-202-2025-QH15#D1.K10"],
            province_new="Đà Nẵng",
            hops=2,
            difficulty="medium",
            note="NQ 202 K10 nêu thành phố Đà Nẵng giáp nước Cộng hòa Dân chủ Nhân dân Lào. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_border",
            question="Tỉnh Đồng Nai hiện nay có chung đường biên giới với nước nào không?",
            gold_text="Có, giáp Vương quốc Campuchia (Campuchia), vì tỉnh Bình Phước đã hợp nhất với tỉnh Đồng Nai thành tỉnh Đồng Nai.",
            answer_type="entity",
            aliases=["Campuchia", "Vương quốc Campuchia"],
            entities=["Campuchia"],
            obs_text="Không, Đồng Nai không có đường biên giới quốc tế.",
            obs_entities=["không có biên giới"],
            gold_clauses=["NQ-202-2025-QH15#D1.K17"],
            province_new="Đồng Nai",
            hops=2,
            difficulty="medium",
            note="NQ 202 K17 nêu tỉnh Đồng Nai giáp Vương quốc Campuchia. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_adjacency",
            question="Thành phố Hồ Chí Minh hiện nay có tiếp giáp trực tiếp với tỉnh Lâm Đồng không?",
            gold_text="Có. Sau khi hợp nhất với Bà Rịa - Vũng Tàu và Bình Dương (và Lâm Đồng hợp nhất với Bình Thuận, Đắk Nông), Thành phố Hồ Chí Minh giáp Đồng Nai, Đồng Tháp, Lâm Đồng, Tây Ninh và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "tiếp giáp", "giáp Lâm Đồng"],
            entities=["Hồ Chí Minh", "Lâm Đồng"],
            obs_text="Không, TP Hồ Chí Minh và Lâm Đồng ngăn cách bởi Đồng Nai và Bình Thuận.",
            obs_entities=["không giáp", "Bình Thuận"],
            gold_clauses=["NQ-202-2025-QH15#D1.K16", "NQ-202-2025-QH15#D1.K14"],
            province_new="Hồ Chí Minh",
            hops=2,
            difficulty="hard",
            note="NQ 202 K16 nêu TP.HCM giáp Lâm Đồng; K14 nêu Lâm Đồng giáp TP.HCM. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_adjacency",
            question="Tỉnh Đồng Tháp hiện nay có tiếp giáp trực tiếp với Thành phố Hồ Chí Minh và Biển Đông không?",
            gold_text="Có. Vì tỉnh Tiền Giang đã hợp nhất với tỉnh Đồng Tháp thành tỉnh Đồng Tháp; theo Nghị quyết 202/2025/QH15, tỉnh Đồng Tháp giáp An Giang, Tây Ninh, Vĩnh Long, Cần Thơ, Thành phố Hồ Chí Minh, Vương quốc Campuchia và Biển Đông.",
            answer_type="yes_no",
            aliases=["Có", "tiếp giáp Thành phố Hồ Chí Minh", "giáp Biển Đông"],
            entities=["Đồng Tháp", "Hồ Chí Minh"],
            obs_text="Không, Đồng Tháp không giáp TP Hồ Chí Minh và không giáp biển.",
            obs_entities=["không giáp biển", "Tiền Giang"],
            gold_clauses=["NQ-202-2025-QH15#D1.K21"],
            province_new="Đồng Tháp",
            hops=2,
            difficulty="hard",
            note="NQ 202 K21 nêu tỉnh Đồng Tháp giáp Thành phố Hồ Chí Minh và Biển Đông. Chờ TV1 kiểm chéo.",
        ),
        # --- C3: Đối chứng không gian (4 câu control) ---
        m(
            subtype="spatial_control",
            item_role="control",
            question="Sau đợt sắp xếp năm 2025, tỉnh Nghệ An và tỉnh Hà Tĩnh có còn là hai tỉnh riêng biệt không?",
            gold_text="Có. Cả tỉnh Nghệ An và tỉnh Hà Tĩnh đều thuộc danh sách 11 tỉnh, thành phố không thực hiện sắp xếp cấp tỉnh năm 2025 theo Nghị quyết 202/2025/QH15.",
            answer_type="yes_no",
            aliases=["Có", "hai tỉnh riêng", "không thực hiện sắp xếp"],
            entities=["Nghệ An", "Hà Tĩnh"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24"],
            province_new=None,
            hops=2,
            difficulty="easy",
            note="Câu đối chứng nhóm C: NQ 202 K24 xác nhận cả Nghệ An và Hà Tĩnh đều không sắp xếp. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_control",
            item_role="control",
            question="Thành phố Hà Nội hiện nay vẫn tiếp giáp trực tiếp với tỉnh Thái Nguyên và tỉnh Bắc Ninh mới đúng không?",
            gold_text="Đúng. Thành phố Hà Nội giữ nguyên không sắp xếp (NQ 202 K24), và theo NQ 202 K3 và K5, cả tỉnh Thái Nguyên mới và tỉnh Bắc Ninh mới đều giáp thành phố Hà Nội.",
            answer_type="yes_no",
            aliases=["Đúng", "Có", "giáp Hà Nội"],
            entities=["Hà Nội", "Thái Nguyên", "Bắc Ninh"],
            gold_clauses=["NQ-202-2025-QH15#D1.K3", "NQ-202-2025-QH15#D1.K5", "NQ-202-2025-QH15#D1.K24"],
            province_new="Hà Nội",
            hops=2,
            difficulty="medium",
            note="Câu đối chứng nhóm C: trước và sau 01/07/2025 Hà Nội đều giáp Thái Nguyên và Bắc Ninh. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_control",
            item_role="control",
            question="Tỉnh Lào Cai sau khi hợp nhất với tỉnh Yên Bái có còn chung đường biên giới với Trung Quốc không?",
            gold_text="Có. Theo Nghị quyết 202/2025/QH15 Điều 1 khoản 2, tỉnh Lào Cai mới giáp Lai Châu, Phú Thọ, Sơn La, Tuyên Quang và nước Cộng hòa Nhân dân Trung Hoa.",
            answer_type="yes_no",
            aliases=["Có", "Trung Quốc", "Cộng hòa Nhân dân Trung Hoa"],
            entities=["Lào Cai", "Trung Quốc"],
            gold_clauses=["NQ-202-2025-QH15#D1.K2"],
            province_new="Lào Cai",
            hops=2,
            difficulty="easy",
            note="Câu đối chứng nhóm C: đường biên giới với Trung Quốc của Lào Cai không thay đổi sau hợp nhất. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="spatial_control",
            item_role="control",
            question="Tỉnh Thanh Hóa hiện nay có còn tiếp giáp với tỉnh Ninh Bình không?",
            gold_text="Có. Tỉnh Thanh Hóa là một trong 11 tỉnh không thực hiện sắp xếp (NQ 202 K24), và tỉnh Ninh Bình mới (hợp nhất Hà Nam, Nam Định, Ninh Bình) vẫn giáp tỉnh Thanh Hóa (NQ 202 K8).",
            answer_type="yes_no",
            aliases=["Có", "giáp Thanh Hóa", "giáp Ninh Bình"],
            entities=["Thanh Hóa", "Ninh Bình"],
            gold_clauses=["NQ-202-2025-QH15#D1.K8", "NQ-202-2025-QH15#D1.K24"],
            province_new="Thanh Hóa",
            hops=2,
            difficulty="easy",
            note="Câu đối chứng nhóm C: trước và sau 01/07/2025 Thanh Hóa đều giáp Ninh Bình. Chờ TV1 kiểm chéo.",
        ),
    ]


def build_d(corpus: Corpus, ctrl: dict[str, bool]) -> list[dict[str, Any]]:
    """22 câu D_before_after: 19 trap + 3 control."""
    m = lambda **kw: make_item(corpus, ctrl, category="D_before_after", **kw)
    return [
        # --- D1: Trước/sau về cấp tỉnh (8 câu trap) ---
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, số lượng đơn vị hành chính cấp tỉnh và số thành phố trực thuộc trung ương của Việt Nam thay đổi như thế nào?",
            gold_text="Trước 01/07/2025 (từ 01/01/2025 sau khi Huế lên thành phố trực thuộc trung ương): 63 đơn vị (57 tỉnh, 6 thành phố trực thuộc trung ương). Sau 01/07/2025: còn 34 đơn vị, gồm 28 tỉnh và 6 thành phố trực thuộc trung ương.",
            answer_type="free_text",
            aliases=["63", "34", "28 tỉnh", "6 thành phố"],
            obs_text="Việt Nam vẫn có 63 tỉnh, thành phố trực thuộc trung ương (hoặc 58 tỉnh và 5 thành phố).",
            obs_entities=["63 tỉnh", "5 thành phố"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24", "NQ-202-2025-QH15#D2.K2"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K24 nêu 34 ĐVHC cấp tỉnh (28 tỉnh, 6 thành phố); Điều 2 K2 nêu mốc 01/07/2025. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Bà Rịa - Vũng Tàu thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là một tỉnh riêng thuộc vùng Đông Nam Bộ. Sau 01/07/2025: hợp nhất cùng Thành phố Hồ Chí Minh và tỉnh Bình Dương thành Thành phố Hồ Chí Minh mới (diện tích 6.772,59 km², dân số 14.002.598 người), không còn là tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất vào Thành phố Hồ Chí Minh", "Thành phố Hồ Chí Minh"],
            entities=["Hồ Chí Minh"],
            obs_text="Bà Rịa - Vũng Tàu vẫn là tỉnh riêng thuộc vùng Đông Nam Bộ.",
            obs_entities=["tỉnh Bà Rịa - Vũng Tàu"],
            gold_clauses=["NQ-202-2025-QH15#D1.K16"],
            province_new="Hồ Chí Minh",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K16. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Kon Tum thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là một tỉnh riêng ở Bắc Tây Nguyên. Sau 01/07/2025: hợp nhất với tỉnh Quảng Ngãi thành tỉnh Quảng Ngãi mới (diện tích 14.832,55 km², dân số 2.161.755 người), không còn là tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất với Quảng Ngãi", "tỉnh Quảng Ngãi"],
            entities=["Quảng Ngãi"],
            obs_text="Kon Tum vẫn là một tỉnh riêng ở Tây Nguyên.",
            obs_entities=["tỉnh Kon Tum"],
            gold_clauses=["NQ-202-2025-QH15#D1.K11"],
            province_new="Quảng Ngãi",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K11. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Bạc Liêu thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là một tỉnh riêng ở Đồng bằng sông Cửu Long. Sau 01/07/2025: hợp nhất với tỉnh Cà Mau thành tỉnh Cà Mau mới (diện tích 7.942,39 km², dân số 2.606.672 người), không còn là tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất với Cà Mau", "tỉnh Cà Mau"],
            entities=["Cà Mau"],
            obs_text="Bạc Liêu vẫn là một tỉnh riêng ở Đồng bằng sông Cửu Long.",
            obs_entities=["tỉnh Bạc Liêu"],
            gold_clauses=["NQ-202-2025-QH15#D1.K22"],
            province_new="Cà Mau",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K22. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Hậu Giang thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là một tỉnh riêng ở Đồng bằng sông Cửu Long. Sau 01/07/2025: hợp nhất cùng thành phố Cần Thơ và tỉnh Sóc Trăng thành thành phố Cần Thơ mới (diện tích 6.360,83 km², dân số 4.199.824 người), không còn là tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất vào Cần Thơ", "thành phố Cần Thơ"],
            entities=["Cần Thơ"],
            obs_text="Hậu Giang vẫn là một tỉnh riêng, tỉnh lỵ là thành phố Vị Thanh.",
            obs_entities=["tỉnh Hậu Giang", "thành phố Vị Thanh"],
            gold_clauses=["NQ-202-2025-QH15#D1.K19"],
            province_new="Cần Thơ",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K19. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Vĩnh Phúc và tỉnh Hòa Bình thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là hai tỉnh riêng biệt. Sau 01/07/2025: cả hai cùng hợp nhất với tỉnh Phú Thọ thành tỉnh Phú Thọ mới (diện tích 9.361,38 km², dân số 4.022.638 người), không còn là các tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất thành tỉnh Phú Thọ", "Phú Thọ"],
            entities=["Phú Thọ"],
            obs_text="Vĩnh Phúc và Hòa Bình vẫn là hai tỉnh riêng biệt.",
            obs_entities=["tỉnh Vĩnh Phúc", "tỉnh Hòa Bình"],
            gold_clauses=["NQ-202-2025-QH15#D1.K4"],
            province_new="Phú Thọ",
            hops=1,
            difficulty="medium",
            note="NQ 202 Điều 1 K4. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Bến Tre và tỉnh Trà Vinh thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là hai tỉnh riêng biệt. Sau 01/07/2025: cả hai cùng hợp nhất với tỉnh Vĩnh Long thành tỉnh Vĩnh Long mới (diện tích 6.296,20 km², dân số 4.257.581 người), không còn là các tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất thành tỉnh Vĩnh Long", "Vĩnh Long"],
            entities=["Vĩnh Long"],
            obs_text="Bến Tre và Trà Vinh vẫn là hai tỉnh riêng biệt ở Đồng bằng sông Cửu Long.",
            obs_entities=["tỉnh Bến Tre", "tỉnh Trà Vinh"],
            gold_clauses=["NQ-202-2025-QH15#D1.K20"],
            province_new="Vĩnh Long",
            hops=1,
            difficulty="medium",
            note="NQ 202 Điều 1 K20. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="province_before_after",
            question="Trước và sau ngày 01/07/2025, tỉnh Hải Dương thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là một tỉnh riêng ở vùng Đồng bằng sông Hồng. Sau 01/07/2025: hợp nhất với thành phố Hải Phòng thành thành phố Hải Phòng mới (diện tích 3.194,72 km², dân số 4.664.124 người), không còn là tỉnh riêng.",
            answer_type="free_text",
            aliases=["hợp nhất với Hải Phòng", "thành phố Hải Phòng"],
            entities=["Hải Phòng"],
            obs_text="Hải Dương vẫn là một tỉnh riêng, tỉnh lỵ là thành phố Hải Dương.",
            obs_entities=["tỉnh Hải Dương", "thành phố Hải Dương"],
            gold_clauses=["NQ-202-2025-QH15#D1.K7"],
            province_new="Hải Phòng",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K7. Chờ TV1 kiểm chéo.",
        ),
        # --- D2: Trước/sau về huyện đảo -> đặc khu (4 câu trap) ---
        m(
            subtype="special_zone_before_after",
            question="Trước và sau ngày 01/07/2025, huyện đảo Lý Sơn thay đổi về loại đơn vị hành chính như thế nào?",
            gold_text="Trước 01/07/2025: là huyện Lý Sơn (đơn vị hành chính cấp huyện) thuộc tỉnh Quảng Ngãi. Sau 01/07/2025: chuyển thành đặc khu Lý Sơn (đơn vị hành chính cấp xã ở hải đảo) trực thuộc tỉnh Quảng Ngãi.",
            answer_type="free_text",
            aliases=["đặc khu Lý Sơn", "tỉnh Quảng Ngãi"],
            entities=["Quảng Ngãi"],
            obs_text="Lý Sơn vẫn là huyện đảo trực thuộc tỉnh Quảng Ngãi.",
            obs_entities=["huyện Lý Sơn", "huyện đảo Lý Sơn"],
            gold_clauses=["NQ-1677-2025-UBTVQH15#D1.K91", "LUAT-72-2025-QH15#D1.K1"],
            province_new="Quảng Ngãi",
            hops=2,
            difficulty="medium",
            note="NQ 1677 K91 chuyển huyện Lý Sơn thành đặc khu Lý Sơn; Luật 72 Điều 1 K1 định nghĩa đặc khu là ĐVHC cấp xã ở hải đảo. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="special_zone_before_after",
            question="Trước và sau ngày 01/07/2025, huyện Cát Hải và huyện Bạch Long Vĩ của thành phố Hải Phòng thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là hai huyện (cấp huyện) thuộc thành phố Hải Phòng. Sau 01/07/2025: chuyển thành đặc khu Cát Hải và đặc khu Bạch Long Vĩ (đơn vị hành chính cấp xã) trực thuộc thành phố Hải Phòng.",
            answer_type="free_text",
            aliases=["đặc khu Cát Hải", "đặc khu Bạch Long Vĩ"],
            entities=["Hải Phòng"],
            obs_text="Cát Hải và Bạch Long Vĩ vẫn là hai huyện thuộc thành phố Hải Phòng.",
            obs_entities=["huyện Cát Hải", "huyện Bạch Long Vĩ"],
            gold_clauses=["NQ-1669-2025-UBTVQH15#D1.K113", "NQ-1669-2025-UBTVQH15#D1.K114"],
            province_new="Hải Phòng",
            hops=2,
            difficulty="medium",
            note="NQ 1669 K113 (đặc khu Cát Hải) và K114 (đặc khu Bạch Long Vĩ). Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="special_zone_before_after",
            question="Trước và sau ngày 01/07/2025, huyện Vân Đồn và huyện Cô Tô của tỉnh Quảng Ninh thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là hai huyện (cấp huyện) thuộc tỉnh Quảng Ninh. Sau 01/07/2025: chuyển thành đặc khu Vân Đồn và đặc khu Cô Tô (đơn vị hành chính cấp xã) trực thuộc tỉnh Quảng Ninh.",
            answer_type="free_text",
            aliases=["đặc khu Vân Đồn", "đặc khu Cô Tô"],
            entities=["Quảng Ninh"],
            obs_text="Vân Đồn và Cô Tô vẫn là hai huyện thuộc tỉnh Quảng Ninh.",
            obs_entities=["huyện Vân Đồn", "huyện Cô Tô"],
            gold_clauses=["NQ-1679-2025-UBTVQH15#D1.K52", "NQ-1679-2025-UBTVQH15#D1.K53"],
            province_new="Quảng Ninh",
            hops=2,
            difficulty="medium",
            note="NQ 1679 K52 (đặc khu Vân Đồn) và K53 (đặc khu Cô Tô). Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="special_zone_before_after",
            question="Trước và sau ngày 01/07/2025, huyện đảo Cồn Cỏ và huyện đảo Hoàng Sa thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: là các huyện đảo (cấp huyện) thuộc tỉnh Quảng Trị và thành phố Đà Nẵng. Sau 01/07/2025: chuyển thành đặc khu Cồn Cỏ (thuộc tỉnh Quảng Trị) và đặc khu Hoàng Sa (thuộc thành phố Đà Nẵng).",
            answer_type="free_text",
            aliases=["đặc khu Cồn Cỏ", "đặc khu Hoàng Sa"],
            entities=["Quảng Trị", "Đà Nẵng"],
            obs_text="Cồn Cỏ và Hoàng Sa vẫn là các huyện đảo thuộc Quảng Trị và Đà Nẵng.",
            obs_entities=["huyện Cồn Cỏ", "huyện Hoàng Sa"],
            gold_clauses=["NQ-1680-2025-UBTVQH15#D1.K77", "NQ-1659-2025-UBTVQH15#D1.K92"],
            province_new=None,
            hops=2,
            difficulty="medium",
            note="NQ 1680 K77 (đặc khu Cồn Cỏ) và NQ 1659 K92 (đặc khu Hoàng Sa). Chờ TV1 kiểm chéo.",
        ),
        # --- D3: Trước/sau về thể chế, tổ chức chính quyền địa phương (7 câu trap) ---
        m(
            subtype="institution_before_after",
            question="Trước và sau ngày 01/07/2025, các loại hình đơn vị hành chính cấp xã ở Việt Nam thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: cấp xã gồm xã, phường và thị trấn. Sau 01/07/2025: không còn thị trấn (thị trấn sắp xếp với xã thành xã); cấp xã gồm 3 loại là xã, phường và đặc khu.",
            answer_type="free_text",
            aliases=["xã, phường, đặc khu", "không còn thị trấn"],
            obs_text="Đơn vị hành chính cấp xã gồm xã, phường và thị trấn.",
            obs_entities=["thị trấn"],
            gold_clauses=["LUAT-72-2025-QH15#D1.K1", "NQ-76-2025-UBTVQH15#D1.K3"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="Luật 72 Điều 1 K1 quy định cấp xã gồm xã, phường, đặc khu; NQ 76 Điều 1 K3 quy định sắp xếp xã, thị trấn thành xã. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Trước và sau ngày 01/07/2025, mô hình tổ chức chính quyền tại các phường thuộc Hà Nội, Thành phố Hồ Chí Minh và Đà Nẵng (vốn không tổ chức HĐND phường) thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: các phường này thực hiện mô hình chính quyền đô thị không tổ chức HĐND phường (theo Luật Thủ đô, NQ 131/2020/QH14, NQ 136/2024/QH15). Sau 01/07/2025: các quy định này bị bãi bỏ và chính quyền tại các phường ở Hà Nội, TP Hồ Chí Minh, Đà Nẵng là cấp chính quyền địa phương gồm đầy đủ HĐND và UBND phường.",
            answer_type="free_text",
            aliases=["có HĐND và UBND phường", "bãi bỏ mô hình không tổ chức HĐND phường"],
            obs_text="Các phường ở Hà Nội, TP Hồ Chí Minh và Đà Nẵng tiếp tục thí điểm không tổ chức HĐND phường.",
            obs_entities=["không tổ chức HĐND phường", "không có HĐND phường"],
            gold_clauses=["LUAT-72-2025-QH15#D53.K1", "LUAT-72-2025-QH15#D52.K3"],
            province_new=None,
            hops=2,
            difficulty="hard",
            note="Luật 72 Điều 53 K1 khôi phục HĐND phường ở Hà Nội, TP.HCM, Đà Nẵng từ 01/07/2025; Điều 52 K3 bãi bỏ NQ 131/2020, điều 7-8 NQ 136/2024, NQ 169/2024. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Trước và sau ngày 01/07/2025, chủ thể quyết định điều động và cách chức Chủ tịch, Phó Chủ tịch UBND cấp xã thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: thuộc thẩm quyền của Chủ tịch UBND cấp huyện. Sau 01/07/2025 (khi bỏ cấp huyện): thuộc thẩm quyền quyết định của Chủ tịch UBND cấp tỉnh.",
            answer_type="entity",
            aliases=["Chủ tịch UBND cấp tỉnh", "Chủ tịch Ủy ban nhân dân cấp tỉnh"],
            obs_text="Chủ tịch UBND cấp huyện quyết định điều động, cách chức Chủ tịch, Phó Chủ tịch UBND cấp xã.",
            obs_entities=["Chủ tịch UBND cấp huyện", "UBND cấp huyện"],
            gold_clauses=["LUAT-72-2025-QH15#D41.K1", "LUAT-72-2025-QH15#D41.K2"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="Luật 72 Điều 41 K1 và K2. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Trong năm 2025, cách kiện toàn các chức danh lãnh đạo HĐND và UBND tại các đơn vị hành chính hình thành sau sắp xếp có gì khác so với quy trình bầu thông thường?",
            gold_text="Thông thường HĐND bầu các chức danh lãnh đạo HĐND và UBND cùng cấp. Nhưng khi kiện toàn năm 2025 sau sắp xếp và bỏ cấp huyện, không tiến hành bầu mà thực hiện chỉ định: UBTVQH chỉ định lãnh đạo HĐND cấp tỉnh, Thủ tướng chỉ định Chủ tịch và Phó Chủ tịch UBND cấp tỉnh, Thường trực HĐND cấp tỉnh chỉ định lãnh đạo HĐND và UBND cấp xã.",
            answer_type="free_text",
            aliases=["không tiến hành bầu", "chỉ định"],
            obs_text="HĐND tỉnh mới và xã mới họp bầu Chủ tịch HĐND, Chủ tịch UBND như thông thường.",
            obs_entities=["họp bầu"],
            gold_clauses=["NQ-203-2025-QH15#D2.K3"],
            province_new=None,
            hops=1,
            difficulty="hard",
            note="NQ 203 Điều 2 K3 quy định rõ cơ chế không bầu mà chỉ định năm 2025. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Trước và sau ngày 01/07/2025, chủ thể phê chuẩn kết quả bầu Chủ tịch và Phó Chủ tịch UBND cấp xã thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: kết quả bầu Chủ tịch, Phó Chủ tịch UBND cấp xã do Chủ tịch UBND cấp huyện phê chuẩn. Sau 01/07/2025: do Chủ tịch UBND cấp tỉnh phê chuẩn.",
            answer_type="entity",
            aliases=["Chủ tịch UBND cấp tỉnh", "Chủ tịch Ủy ban nhân dân cấp tỉnh"],
            obs_text="Kết quả bầu Chủ tịch, Phó Chủ tịch UBND cấp xã do Chủ tịch UBND cấp huyện phê chuẩn.",
            obs_entities=["Chủ tịch UBND cấp huyện", "cấp huyện"],
            gold_clauses=["LUAT-72-2025-QH15#D36.K4"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="Luật 72 Điều 36 K4. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Trước và sau ngày 01/07/2025, thẩm quyền giải tán Hội đồng nhân dân cấp xã (khi làm thiệt hại nghiêm trọng đến lợi ích của Nhân dân) thay đổi như thế nào?",
            gold_text="Trước 01/07/2025: HĐND cấp huyện giải tán HĐND cấp xã (trình HĐND cấp tỉnh phê chuẩn). Sau 01/07/2025: Hội đồng nhân dân cấp tỉnh giải tán Hội đồng nhân dân cấp xã và trình Ủy ban Thường vụ Quốc hội phê chuẩn.",
            answer_type="free_text",
            aliases=["Hội đồng nhân dân cấp tỉnh", "Ủy ban Thường vụ Quốc hội phê chuẩn"],
            obs_text="HĐND cấp huyện giải tán HĐND cấp xã và trình HĐND cấp tỉnh phê chuẩn.",
            obs_entities=["HĐND cấp huyện", "cấp huyện"],
            gold_clauses=["LUAT-72-2025-QH15#D50.K2", "LUAT-72-2025-QH15#D50.K3"],
            province_new=None,
            hops=1,
            difficulty="hard",
            note="Luật 72 Điều 50 K2 và K3. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="institution_before_after",
            question="Sau khi sắp xếp đơn vị hành chính năm 2025, khóa của Hội đồng nhân dân ở đơn vị hành chính mới được xác định khác nhau thế nào giữa trường hợp giữ nguyên tên gọi và trường hợp đổi tên hoặc đổi loại đơn vị?",
            gold_text="Nếu đơn vị hành chính mới giữ nguyên tên gọi của một trong các đơn vị trước sắp xếp thì tiếp tục tính theo khóa của HĐND ở đơn vị giữ nguyên tên gọi. Nếu thay đổi tên gọi hoặc thay đổi loại đơn vị hành chính thì khóa của HĐND được tính lại từ đầu (khóa I) kể từ thời điểm thành lập.",
            answer_type="free_text",
            aliases=["giữ nguyên tên gọi thì tiếp tục tính theo khóa cũ", "tính lại từ đầu", "khóa I"],
            obs_text="Mọi đơn vị hành chính mới sau sáp nhập đều tính lại từ khóa I.",
            obs_entities=[],
            gold_clauses=["NQ-76-2025-UBTVQH15#D10.K3", "LUAT-72-2025-QH15#D49.K1"],
            province_new=None,
            hops=1,
            difficulty="hard",
            note="NQ 76 Điều 10 K3 và Luật 72 Điều 49 K1 quy định giống nhau về xác định khóa HĐND. Chờ TV1 kiểm chéo.",
        ),
        # --- D4: Đối chứng trước/sau không thay đổi (3 câu control) ---
        m(
            subtype="before_after_control",
            item_role="control",
            question="Trước và sau ngày 01/07/2025, thời hạn nhiệm kỳ của mỗi khóa Hội đồng nhân dân ở Việt Nam có thay đổi không?",
            gold_text="Không thay đổi. Theo khoản 4 Điều 5 Luật Tổ chức chính quyền địa phương số 72/2025/QH15, nhiệm kỳ của mỗi khóa Hội đồng nhân dân vẫn là 05 năm.",
            answer_type="number",
            aliases=["không thay đổi", "5 năm", "05 năm"],
            gold_clauses=["LUAT-72-2025-QH15#D5.K4"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="Câu đối chứng nhóm D: nhiệm kỳ HĐND vẫn là 5 năm theo Luật 72 Điều 5 K4. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="before_after_control",
            item_role="control",
            question="Trước và sau ngày 01/07/2025, cơ quan nào có thẩm quyền quyết định thành lập, giải thể, nhập, chia đơn vị hành chính cấp tỉnh và cấp xã?",
            gold_text="Không thay đổi: Quốc hội quyết định đối với đơn vị hành chính cấp tỉnh; Ủy ban Thường vụ Quốc hội quyết định đối với đơn vị hành chính cấp xã.",
            answer_type="entity_list",
            aliases=["Quốc hội", "Ủy ban Thường vụ Quốc hội"],
            entities=["Quốc hội", "Ủy ban Thường vụ Quốc hội"],
            gold_clauses=["LUAT-72-2025-QH15#D9.K1", "LUAT-72-2025-QH15#D9.K2"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="Câu đối chứng nhóm D: Luật 72 Điều 9 K1 và K2 giữ nguyên phân cấp thẩm quyền của Quốc hội và UBTVQH. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="before_after_control",
            item_role="control",
            question="Trước và sau ngày 01/07/2025, địa giới cấp tỉnh của tỉnh Quảng Ninh và tỉnh Lạng Sơn có thay đổi do hợp nhất tỉnh không?",
            gold_text="Không. Cả tỉnh Quảng Ninh và tỉnh Lạng Sơn đều nằm trong danh sách 11 tỉnh, thành phố không thực hiện sắp xếp cấp tỉnh theo Nghị quyết 202/2025/QH15.",
            answer_type="yes_no",
            aliases=["Không", "không thực hiện sắp xếp", "giữ nguyên"],
            entities=["Quảng Ninh", "Lạng Sơn"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="Câu đối chứng nhóm D: NQ 202 K24 xác nhận Quảng Ninh và Lạng Sơn không sắp xếp cấp tỉnh. Chờ TV1 kiểm chéo.",
        ),
    ]


def build_f(corpus: Corpus, ctrl: dict[str, bool]) -> list[dict[str, Any]]:
    """12 câu F_rumor: tin đồn có văn bản/quy định chính thức bác bỏ."""
    m = lambda **kw: make_item(corpus, ctrl, category="F_rumor", **kw)
    return [
        m(
            subtype="debunked_rumor_official",
            question="Trên mạng xã hội lan truyền tin sau khi bỏ cấp huyện, từ năm 2026 Nhà nước sẽ xóa bỏ hoàn toàn thôn và tổ dân phố, đúng không?",
            gold_text="Không đúng. Thôn và tổ dân phố không bị xóa bỏ mà tiếp tục tồn tại là tổ chức tự quản của cộng đồng dân cư dưới cấp xã (được quy định tại Nghị định 185/2026/NĐ-CP; Thông tư 31/2026/TT-BNV chỉ bãi bỏ các thông tư cũ để đồng bộ hóa pháp luật).",
            answer_type="premise_rejection",
            aliases=["không đúng", "không xóa bỏ thôn, tổ dân phố"],
            obs_text="Đúng, Nhà nước sẽ bãi bỏ thôn và tổ dân phố cùng với cấp huyện.",
            obs_entities=["bỏ thôn", "bỏ tổ dân phố"],
            gold_clauses=[TODO_CLAUSE],
            extra_external=[
                ext_ev("Nghị định 185/2026/NĐ-CP về tổ chức, hoạt động của thôn, tổ dân phố"),
                ext_ev("Thông tư 31/2026/TT-BNV ngày 20/11/2026 của Bộ Nội vụ"),
            ],
            province_new=None,
            hops=1,
            difficulty="medium",
            source_url="https://baochinhphu.vn",
            note="Tin đồn ngoài kho văn bản 39 file (văn bản 2026); gold_clause_ids để TODO_VERIFY_CLAUSE. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_official",
            question="Có tin đồn trên mạng rằng Bộ Nội vụ đang trình phương án tiếp tục sáp nhập đại trà các xã, phường trên toàn quốc trong năm 2026, thông tin này có đúng không?",
            gold_text="Không đúng. Tại Công văn 10988/BNV-CQĐP ngày 21/11/2025 và các thông tin chính thức, Bộ Nội vụ khẳng định Đảng, Nhà nước, Quốc hội và Chính phủ không có chủ trương tiếp tục thực hiện sắp xếp, sáp nhập tỉnh, thành phố và đơn vị hành chính cấp xã trên cả nước.",
            answer_type="premise_rejection",
            aliases=["không đúng", "không có chủ trương tiếp tục sáp nhập"],
            obs_text="Đúng, Bộ Nội vụ chuẩn bị đợt sáp nhập xã, phường đại trà lần 2 năm 2026.",
            obs_entities=["sáp nhập đợt 2"],
            gold_clauses=[TODO_CLAUSE],
            extra_external=[
                ext_ev("Công văn 10988/BNV-CQĐP ngày 21/11/2025 của Bộ Nội vụ"),
            ],
            province_new=None,
            hops=1,
            difficulty="medium",
            source_url="https://chinhphu.vn",
            note="Văn bản bác bỏ chính thức ngoài kho 39 văn bản (Công văn 10988/BNV-CQĐP). Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Có tin đồn sau khi sáp nhập tỉnh, người dân bắt buộc phải đi đổi biển số xe và giấy đăng ký xe theo tên tỉnh mới ngay lập tức nếu không sẽ bị xử phạt, đúng không?",
            gold_text="Không đúng. Theo khoản 1 và khoản 2 Điều 10 Nghị quyết 190/2025/QH15 (và hướng dẫn của Bộ Công an), giấy tờ đã cấp trước khi sắp xếp còn thời hạn sử dụng tiếp tục có giá trị; không được yêu cầu người dân làm thủ tục cấp đổi chỉ vì sắp xếp đơn vị hành chính.",
            answer_type="premise_rejection",
            aliases=["không đúng", "không bắt buộc đổi biển số xe", "tiếp tục sử dụng"],
            obs_text="Đúng, chủ xe bắt buộc phải đổi lại biển số và đăng ký xe theo tên tỉnh mới.",
            obs_entities=["bắt buộc đổi biển số"],
            gold_clauses=["NQ-190-2025-QH15#D10.K1", "NQ-190-2025-QH15#D10.K2"],
            extra_external=[ext_ev("Hướng dẫn của Bộ Công an về đăng ký, biển số xe sau sắp xếp ĐVHC")],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="Bác bỏ trực tiếp bằng NQ 190 Điều 10 K1–K2 (trong kho). Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Nghe nói hộ chiếu phổ thông còn hạn nhưng ghi nơi sinh là tên tỉnh cũ (như Bình Dương, Quảng Nam, Thái Bình) sẽ hết hiệu lực từ 01/07/2025 và bắt buộc làm hộ chiếu mới, đúng không?",
            gold_text="Không đúng. Theo khoản 1 và khoản 2 Điều 10 Nghị quyết 190/2025/QH15 (được dẫn chiếu tại khoản 1 Điều 14 Nghị quyết 76/2025/UBTVQH15), giấy tờ đã cấp trước khi sắp xếp mà chưa hết thời hạn sử dụng tiếp tục được sử dụng, không bắt buộc cấp đổi.",
            answer_type="premise_rejection",
            aliases=["không đúng", "không bắt buộc đổi hộ chiếu", "tiếp tục sử dụng"],
            obs_text="Đúng, hộ chiếu ghi tỉnh cũ không còn giá trị và phải cấp đổi ngay.",
            obs_entities=["hết hiệu lực", "bắt buộc đổi hộ chiếu"],
            gold_clauses=["NQ-190-2025-QH15#D10.K1", "NQ-190-2025-QH15#D10.K2", "NQ-76-2025-UBTVQH15#D14.K1"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="NQ 190 Điều 10 K1–K2 và NQ 76 Điều 14 K1. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Có tin lan truyền rằng sau khi sáp nhập tỉnh, xã, người dân ở vùng khó khăn, vùng dân tộc thiểu số sẽ bị cắt ngay chế độ, chính sách đặc thù vì tên xã, tỉnh cũ không còn, đúng không?",
            gold_text="Không đúng. Theo Điều 13 Nghị quyết 76/2025/UBTVQH15, người dân, cán bộ, công chức, viên chức, người lao động và lực lượng vũ trang trên địa bàn sau sắp xếp tiếp tục hưởng chế độ, chính sách đặc thù theo vùng, khu vực như trước khi sắp xếp (dùng tên gọi ĐVHC mới) cho đến khi có quyết định khác của cấp có thẩm quyền.",
            answer_type="premise_rejection",
            aliases=["không đúng", "tiếp tục hưởng chế độ, chính sách đặc thù"],
            obs_text="Đúng, khi xã cũ bị sáp nhập thì các chế độ vùng đặc thù bị chấm dứt ngay.",
            obs_entities=["cắt chế độ đặc thù"],
            gold_clauses=["NQ-76-2025-UBTVQH15#D13.K1", "NQ-76-2025-UBTVQH15#D13.K3"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="NQ 76 Điều 13 K1 và K3 bác bỏ trực tiếp tin đồn cắt chế độ đặc thù. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Trên mạng có tin cán bộ, công chức chịu ảnh hưởng của sáp nhập đơn vị hành chính bị cắt ngay phụ cấp chức vụ và hạ lương từ ngày bố trí công tác mới, có đúng không?",
            gold_text="Không đúng. Theo khoản 4 Điều 11 Nghị quyết 76/2025/UBTVQH15, cán bộ, công chức, viên chức chịu ảnh hưởng của việc sắp xếp mà vẫn công tác trong hệ thống chính trị được giữ nguyên chế độ, chính sách tiền lương và phụ cấp chức vụ hiện hưởng trong thời gian 06 tháng kể từ khi có văn bản bố trí công tác.",
            answer_type="premise_rejection",
            aliases=["không đúng", "giữ nguyên trong 06 tháng", "6 tháng"],
            obs_text="Đúng, cán bộ mất chức vụ cũ sẽ bị cắt ngay phụ cấp và hạ lương.",
            obs_entities=["cắt ngay phụ cấp"],
            gold_clauses=["NQ-76-2025-UBTVQH15#D11.K4"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="NQ 76 Điều 11 K4 quy định bảo lưu lương và phụ cấp 06 tháng. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_merger",
            question="Có tin đồn rằng thành phố Huế đã bị sáp nhập vào thành phố Đà Nẵng trong đợt sắp xếp đơn vị hành chính năm 2025, đúng không?",
            gold_text="Không đúng. Theo khoản 24 Điều 1 Nghị quyết 202/2025/QH15, thành phố Huế là một trong 11 tỉnh, thành phố trực thuộc trung ương không thực hiện sắp xếp cấp tỉnh năm 2025; còn thành phố Đà Nẵng hợp nhất với tỉnh Quảng Nam (khoản 10 Điều 1).",
            answer_type="premise_rejection",
            aliases=["không đúng", "Huế không thực hiện sắp xếp"],
            entities=["Huế", "Đà Nẵng"],
            obs_text="Đúng, Huế và Đà Nẵng đã sáp nhập thành một thành phố.",
            obs_entities=["Huế sáp nhập Đà Nẵng"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24", "NQ-202-2025-QH15#D1.K10"],
            province_new="Huế",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K24 và K10 bác bỏ tin đồn sáp nhập Huế – Đà Nẵng. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_merger",
            question="Trên mạng từng lan truyền danh sách cho rằng tỉnh Nghệ An và tỉnh Hà Tĩnh đã tái hợp nhất thành tỉnh Nghệ Tĩnh năm 2025, thông tin này có đúng không?",
            gold_text="Không đúng. Theo khoản 24 Điều 1 Nghị quyết 202/2025/QH15, cả tỉnh Nghệ An và tỉnh Hà Tĩnh đều thuộc danh sách 11 tỉnh, thành phố không thực hiện sắp xếp cấp tỉnh trong năm 2025.",
            answer_type="premise_rejection",
            aliases=["không đúng", "không thực hiện sắp xếp", "không hợp nhất"],
            entities=["Nghệ An", "Hà Tĩnh"],
            obs_text="Đúng, Nghệ An và Hà Tĩnh đã hợp nhất thành tỉnh Nghệ Tĩnh.",
            obs_entities=["tỉnh Nghệ Tĩnh"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24"],
            province_new=None,
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K24 bác bỏ trực tiếp tin đồn tái lập tỉnh Nghệ Tĩnh. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_merger",
            question="Có tin đồn rằng tỉnh Thanh Hóa đã sáp nhập với tỉnh Ninh Bình trong đợt sắp xếp đơn vị hành chính năm 2025, đúng không?",
            gold_text="Không đúng. Theo Nghị quyết 202/2025/QH15, tỉnh Thanh Hóa nằm trong 11 đơn vị cấp tỉnh không thực hiện sắp xếp (khoản 24 Điều 1); còn tỉnh Ninh Bình mới được hợp nhất từ Hà Nam, Nam Định và Ninh Bình (khoản 8 Điều 1).",
            answer_type="premise_rejection",
            aliases=["không đúng", "Thanh Hóa không thực hiện sắp xếp"],
            entities=["Thanh Hóa", "Ninh Bình"],
            obs_text="Đúng, Thanh Hóa và Ninh Bình đã sáp nhập thành một tỉnh.",
            obs_entities=["Thanh Hóa sáp nhập Ninh Bình"],
            gold_clauses=["NQ-202-2025-QH15#D1.K24", "NQ-202-2025-QH15#D1.K8"],
            province_new="Thanh Hóa",
            hops=1,
            difficulty="easy",
            note="NQ 202 Điều 1 K24 và K8. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Nghe nói sau khi sắp xếp bộ máy và bỏ cấp huyện, các vụ án tố tụng hoặc thi hành án đang làm dở ở cấp huyện đều bị hủy bỏ và phải điều tra, giải quyết lại từ đầu, đúng không?",
            gold_text="Không đúng. Theo khoản 2 Điều 6 Nghị quyết 190/2025/QH15, cơ quan, người có thẩm quyền tiếp nhận chức năng, nhiệm vụ trong hoạt động tạm giữ, tạm giam, tố tụng, thi hành án không thực hiện lại các nội dung đã làm đúng pháp luật trước khi sắp xếp và tiếp tục giải quyết vụ án, vụ việc đúng thời hạn, trình tự, thủ tục.",
            answer_type="premise_rejection",
            aliases=["không đúng", "không thực hiện lại", "tiếp tục giải quyết"],
            obs_text="Đúng, các vụ án ở cấp huyện bị hủy bỏ để làm lại từ đầu ở cơ quan mới.",
            obs_entities=["phải làm lại từ đầu"],
            gold_clauses=["NQ-190-2025-QH15#D6.K2"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="NQ 190 Điều 6 K2 bác bỏ trực tiếp. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Có tin đồn rằng ngay sau ngày 01/07/2025, tất cả Phó Chủ tịch UBND và cấp phó dôi dư tại các tỉnh mới đều bắt buộc phải thôi chức ngay lập tức để đúng khung số lượng, đúng không?",
            gold_text="Không đúng. Theo khoản 3 Điều 11 Nghị quyết 76/2025/UBTVQH15 và khoản 6 Điều 54 Luật 72/2025/QH15, tại thời điểm sắp xếp số lượng cấp phó có thể nhiều hơn quy định; thời hạn sắp xếp về đúng quy định là chậm nhất 05 năm.",
            answer_type="premise_rejection",
            aliases=["không đúng", "chậm nhất 05 năm", "5 năm"],
            obs_text="Đúng, mọi cấp phó dôi dư phải giảm ngay lập tức từ ngày 01/07/2025.",
            obs_entities=["giảm ngay lập tức"],
            gold_clauses=["NQ-76-2025-UBTVQH15#D11.K3", "LUAT-72-2025-QH15#D54.K6"],
            province_new=None,
            hops=1,
            difficulty="medium",
            note="NQ 76 Điều 11 K3 và Luật 72 Điều 54 K6 quy định lộ trình tối đa 5 năm. Chờ TV1 kiểm chéo.",
        ),
        m(
            subtype="debunked_rumor_policy",
            question="Có tin đồn rằng từ ngày 01/07/2025, mọi thỏa thuận quốc tế do UBND cấp huyện ký kết trước đó đều tự động chấm dứt hiệu lực vì cấp huyện đã giải thể, đúng không?",
            gold_text="Không đúng. Theo khoản 3 Điều 54 Luật 72/2025/QH15, kể từ ngày 01/07/2025, Ủy ban nhân dân cấp tỉnh kế thừa các thỏa thuận quốc tế do Ủy ban nhân dân cấp huyện ký kết trước đó và chịu trách nhiệm điều chỉnh, cập nhật tên gọi mới của đơn vị hành chính.",
            answer_type="premise_rejection",
            aliases=["không đúng", "UBND cấp tỉnh kế thừa"],
            obs_text="Đúng, thỏa thuận quốc tế cấp huyện tự động chấm dứt khi bỏ cấp huyện.",
            obs_entities=["tự động chấm dứt"],
            gold_clauses=["LUAT-72-2025-QH15#D54.K3"],
            province_new=None,
            hops=1,
            difficulty="hard",
            note="Luật 72 Điều 54 K3 quy định UBND cấp tỉnh kế thừa các thỏa thuận quốc tế cấp huyện. Chờ TV1 kiểm chéo.",
        ),
    ]


def main() -> None:
    corpus = Corpus(ROOT / "data/parsed")
    with (ROOT / "data/processed/entity_map_63_34_v1.csv").open(encoding="utf-8") as f:
        ctrl = {r["new_province"]: r["is_control"] == "True" for r in csv.DictReader(f)}

    parts = {
        "C": build_c(corpus, ctrl),
        "D": build_d(corpus, ctrl),
        "F": build_f(corpus, ctrl),
    }

    rows: list[dict[str, Any]] = []
    for prefix, items in parts.items():
        for i, rec in enumerate(items, 1):
            rec["id"] = f"{prefix}-{i:04d}"
            rec["source_id"] = rec["id"]
            rows.append(rec)

    out_path = ROOT / "data/benchmark/tv3_v0.3.jsonl"
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in rows:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    counts = collections.Counter((r["category"], r["item_role"]) for r in rows)
    recall_ready = sum(r["gold_clause_ids"] != [TODO_CLAUSE] for r in rows)
    print(f"{len(rows)} câu mới -> {out_path} ({recall_ready}/{len(rows)} Recall@k-ready)")
    for k in sorted(counts):
        print("  ", k, counts[k])


if __name__ == "__main__":
    main()
