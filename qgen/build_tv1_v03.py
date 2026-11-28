"""Sinh câu hỏi nhóm A, B, E của TV1 cho bộ câu hỏi v0.3 (tuần 3).

Đầu vào:
  data/processed/entity_map_63_34_v1.csv, data/processed/commune_lineage.csv,
  data/parsed/*.json, data/benchmark/pilot_80_v0.2.jsonl (để tránh trùng),
  dvhcvn.json (danh mục ĐVHC 01/03/2025 của Tổng cục Thống kê, qua
  https://github.com/daohoangson/dvhcvn; chỉ dùng để lấy tên huyện cũ đặt vào câu hỏi).

Đầu ra: data/benchmark/tv1_v0.3.jsonl, theo docs/qa_schema.md v1.0.

Mọi đáp án và khoản căn cứ lấy từ nghị quyết trong data/parsed (NQ 202, NQ cấp xã,
NQ 203, Luật 72, NQ 190). Tên huyện cũ (từ dvhcvn) chỉ xuất hiện trong câu hỏi, không
dùng làm căn cứ. Tất cả câu sinh ra có verified = false cho tới khi người thứ hai kiểm.

Chạy:
  python qgen/build_tv1_v03.py --dvhcvn /tmp/dvhcvn/data/dvhcvn.json
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import random
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_DATE = "2026-11-25"
VERSION = "v0.3"
SEED = 2026
CITIES = {"Hà Nội", "Hồ Chí Minh", "Hải Phòng", "Đà Nẵng", "Cần Thơ", "Huế"}

# Đã có trong pilot 80 câu: không sinh lại cùng ý.
PILOT_OLD_PROV = {"Hà Giang", "Yên Bái", "Bắc Giang", "Thái Bình", "Hải Dương", "Quảng Bình",
                  "Bình Định", "Long An", "Kiên Giang", "Phú Yên", "Bình Dương"}
PILOT_NEW_PROV = {"Ninh Bình", "Hồ Chí Minh", "Lâm Đồng", "Gia Lai"}
PILOT_CONTROL = {"Thanh Hóa", "Huế"}
PILOT_COUNT = {"Hà Nội"}
PILOT_DISTRICTS = {"gia lâm", "cần giờ", "thủ đức", "hoàn kiếm", "mèo vạc", "sơn tây",
                   "đắk r'lấp", "phan thiết", "phú quý"}

N = lambda s: unicodedata.normalize("NFC", s).strip()
TONES = {"̀", "́", "̃", "̉", "̣"}


def toneless(s: str) -> str:
    return N("".join(c for c in unicodedata.normalize("NFD", N(s).lower()) if c not in TONES))


def prov_name(p: str, cap: bool = False) -> str:
    """'tỉnh Tuyên Quang' / 'thành phố Hồ Chí Minh' (Thành phố Hồ Chí Minh viết hoa theo NQ 202)."""
    if p == "Hồ Chí Minh":
        return "Thành phố Hồ Chí Minh"
    kind = "thành phố" if p in CITIES else "tỉnh"
    return f"{kind.capitalize() if cap else kind} {p}"


def lower_first(s: str) -> str:
    return s[:1].lower() + s[1:]


def join_vi(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " và " + items[-1]


# ---------------------------------------------------------------- corpus
class Corpus:
    def __init__(self, parsed: Path):
        self.text: dict[str, str] = {}
        self.docs: dict[str, dict] = {}
        for f in sorted(parsed.glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            self.docs[d["doc_id"]] = d
            for a in d["articles"]:
                for c in a["clauses"]:
                    cid = c.get("clause_id") or c.get("id")
                    self.text.setdefault(cid, c["text"])

    def ev(self, clause_id: str, citation: str) -> dict:
        assert clause_id in self.text, clause_id
        doc, rest = clause_id.split("#")
        m = re.match(r"D(\d+)\.K(\d+)$", rest)
        return {"doc_id": doc, "article": m.group(1), "clause": m.group(2), "clause_id": clause_id,
                "citation": citation, "in_corpus": True}

    def summary(self, doc_id: str) -> tuple[str, str]:
        art1 = self.docs[doc_id]["articles"][0]
        c = next(c for c in art1["clauses"] if c["text"].startswith("Sau khi sắp xếp"))
        return (c.get("clause_id") or c.get("id")), re.sub(r"\s+", " ", c["text"])


def cite(clause_id: str) -> str:
    doc, rest = clause_id.split("#")
    art, cl = re.match(r"D(\d+)\.K(\d+)$", rest).groups()
    m = re.match(r"(NQ|LUAT)-(\d+)-(\d{4})-(\w+)$", doc)
    kind, num, year, body = m.groups()
    if body == "UBTVQH15":
        name = f"NQ {num}/NQ-UBTVQH15" if int(num) > 1000 else f"NQ {num}/{year}/UBTVQH15"
    elif kind == "LUAT":
        name = f"Luật {num}/{year}/{body}"
    else:
        name = f"NQ {num}/{year}/{body}"
    return f"{name}, Điều {art}, khoản {cl}"


def item(**kw) -> dict:
    base = {
        "id": None, "source_set": "toan_v03", "source_id": None, "category": None, "subtype": None,
        "item_role": "trap", "question": None, "reference_date": REF_DATE,
        "gold_answer": None, "obsolete_answer": {"text": "", "obsolete_entities": []},
        "evidence": [], "gold_clause_ids": [], "source_url": None, "province_new": None,
        "province_is_control": None, "hops": None, "difficulty": None, "annotator": ["TV1"],
        "verified": False, "verification_note": "Sinh tự động bằng qgen/build_tv1_v03.py; chờ người thứ hai kiểm.",
        "version": VERSION,
    }
    base.update(kw)
    return base


def ga(text, answer_type, aliases=(), entities=()):
    return {"text": text, "aliases": list(aliases), "answer_type": answer_type, "entities": list(entities)}


# ---------------------------------------------------------------- generators
def gen_province(em, corpus, rng):
    out = []
    by_new = collections.defaultdict(list)
    for r in em:
        by_new[r["new_province"]].append(r)
    nq202 = lambda r: "NQ-202-2025-QH15#D1.K" + re.search(r"khoản (\d+)", r["legal_basis"]).group(1)

    # A1: tỉnh cũ không còn tên -> nay thuộc tỉnh nào
    q1 = ["{O} hiện nay thuộc tỉnh, thành phố nào?",
          "Sau đợt sắp xếp năm 2025, {o} cũ nay là một phần của đơn vị hành chính cấp tỉnh nào?",
          "{O} có còn là một tỉnh riêng không? Nếu không thì nay thuộc tỉnh, thành phố nào?"]
    for newp, rows in sorted(by_new.items()):
        if rows[0]["is_control"] == "True":
            continue
        for r in rows:
            o = r["old_province"]
            if o == newp or o in PILOT_OLD_PROV:
                continue
            others = [x["old_province"] for x in rows if x["old_province"] != o]
            cid = nq202(r)
            oname = f"tỉnh {o}" if o not in CITIES else f"thành phố {o}"
            q = rng.choice(q1).format(O=oname[:1].upper() + oname[1:], o=oname)
            out.append(item(category="A_direct", subtype="province", question=q,
                            gold_answer=ga(f"{oname[:1].upper() + oname[1:]} không còn là đơn vị hành chính cấp tỉnh riêng: từ 01/07/2025 đã hợp nhất với "
                                           f"{join_vi(others)} thành {prov_name(newp)}.", "entity",
                                           aliases=[newp, prov_name(newp)]),
                            obsolete_answer={"text": f"Coi {oname} vẫn là một tỉnh riêng.", "obsolete_entities": [oname]},
                            evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                            province_new=newp, province_is_control=False, hops=1, difficulty="easy"))

    # A2: tỉnh mới hợp nhất từ những tỉnh nào
    q2 = ["{N} hiện nay được hình thành từ những tỉnh, thành phố nào?",
          "{N} sau sắp xếp năm 2025 gồm những đơn vị hành chính cấp tỉnh cũ nào?"]
    for newp, rows in sorted(by_new.items()):
        if rows[0]["is_control"] == "True" or newp in PILOT_NEW_PROV:
            continue
        olds = [r["old_province"] for r in rows]
        cid = nq202(rows[0])
        out.append(item(category="A_direct", subtype="province",
                        question=rng.choice(q2).format(N=prov_name(newp, cap=True)),
                        gold_answer=ga(f"{prov_name(newp, cap=True)} được hình thành từ {join_vi(olds)}.", "entity_list",
                                       entities=olds),
                        obsolete_answer={"text": f"Nói {prov_name(newp)} không sáp nhập, vẫn giữ nguyên như trước 2025.",
                                         "obsolete_entities": ["không sáp nhập", "không hợp nhất", "giữ nguyên",
                                                               "không được hình thành từ"]},
                        evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                        province_new=newp, province_is_control=False, hops=1, difficulty="medium"))

    # A3 (đối chứng): 11 tỉnh không sắp xếp
    q3 = ["Trong đợt sắp xếp đơn vị hành chính năm 2025, {n} có hợp nhất với tỉnh, thành phố nào không?",
          "{N} có thuộc diện hợp nhất tỉnh năm 2025 không?"]
    cid = "NQ-202-2025-QH15#D1.K24"
    for newp, rows in sorted(by_new.items()):
        if rows[0]["is_control"] != "True" or newp in PILOT_CONTROL:
            continue
        out.append(item(category="A_direct", subtype="province", item_role="control",
                        question=rng.choice(q3).format(n=prov_name(newp), N=prov_name(newp, cap=True)),
                        gold_answer=ga(f"Không. {prov_name(newp, cap=True)} là một trong 11 tỉnh, thành phố không thực hiện "
                                       "sắp xếp cấp tỉnh (cấp huyện vẫn kết thúc hoạt động và cấp xã vẫn được sắp xếp lại).",
                                       "yes_no", aliases=["không hợp nhất", "giữ nguyên"]),
                        evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                        province_new=newp, province_is_control=True, hops=1, difficulty="easy"))
    return out


def gen_counts(lineage, em, corpus, rng):
    out = []
    ctrl = {r["new_province"]: r["is_control"] == "True" for r in em}
    doc_of = {}
    for r in lineage:
        num = re.match(r"NQ (\d+)/", r["legal_basis"]).group(1)
        doc_of[r["new_province"]] = f"NQ-{num}-2025-UBTVQH15"
    q = ["Sau sắp xếp năm 2025, {n} có bao nhiêu đơn vị hành chính cấp xã?",
         "{N} hiện có bao nhiêu xã, phường{dk}?",
         "Hiện nay {n} có tổng cộng bao nhiêu đơn vị hành chính cấp xã, gồm những loại nào?"]
    for newp in sorted(doc_of):
        if newp in PILOT_COUNT:
            continue
        cid, text = corpus.summary(doc_of[newp])
        m = re.search(r"có (\d+) đơn vị hành chính cấp xã,? gồm (.+?)(?:;|$)", text)
        total, parts = m.group(1), m.group(2).rstrip(". ")
        dk = ", đặc khu" if "đặc khu" in parts else ""
        out.append(item(category="A_direct", subtype="commune",
                        question=rng.choice(q).format(n=prov_name(newp), N=prov_name(newp, cap=True), dk=dk),
                        gold_answer=ga(f"{total} đơn vị hành chính cấp xã, gồm {parts}.", "number", aliases=[total]),
                        obsolete_answer={"text": "Nêu số xã, phường, thị trấn trước 01/07/2025, hoặc vẫn tính thị trấn và cấp huyện.",
                                         "obsolete_entities": ["thị trấn"]},
                        evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                        province_new=newp, province_is_control=ctrl[newp], hops=1, difficulty="medium"))
    return out


def load_dvhcvn(path, em):
    canon = {toneless(r["old_province"]): r["old_province"] for r in em}
    dv = json.loads(Path(path).read_text(encoding="utf-8"))["data"]
    communes = collections.defaultdict(list)   # (old_prov, toneless name, type) -> [district]
    districts = collections.defaultdict(list)  # old_prov -> [(type, name)]
    for p in dv:
        pn = canon[toneless(re.sub(r"^(Thành phố|Tỉnh)\s+", "", N(p["name"])))]
        for d in p["level2s"]:
            dn = N(d["name"])
            districts[pn].append(dn)
            for c in d["level3s"]:
                m = re.match(r"^(Xã|Phường|Thị trấn)\s+(.*)$", N(c["name"]))
                if m:
                    communes[(pn, toneless(m.group(2)), m.group(1).lower())].append(dn)
    return communes, districts


def gen_commune_lookup(lineage, em, corpus, dvc, rng):
    out = []
    ctrl = {r["new_province"]: r["is_control"] == "True" for r in em}
    groups = collections.defaultdict(list)
    for r in lineage:
        groups[r["new_commune_code"]].append(r)
    old_seen = collections.Counter((r["new_province"], r["old_commune"]) for r in lineage)
    cands = collections.defaultdict(list)
    for code, rows in groups.items():
        if len(rows) < 2:
            continue
        for r in rows:
            m = re.match(r"^(xã|phường|thị trấn)\s+(.*)$", N(r["old_commune"]))
            if not m or r["partial"] == "True" or not r["old_province"]:
                continue
            if old_seen[(r["new_province"], r["old_commune"])] > 1:
                continue
            if toneless(m.group(2)) == toneless(r["new_commune"]):
                continue
            dists = dvc.get((r["old_province"], toneless(m.group(2)), m.group(1)), [])
            if len(dists) != 1:
                continue
            cands[r["new_province"]].append((r, rows, dists[0]))
    q = ["{Old} ({dist}, {prov}) sau sắp xếp năm 2025 nay thuộc đơn vị hành chính cấp xã nào?",  # noqa: E501
         "Sau ngày 01/07/2025, {old} thuộc {dist}, {prov_tr} nay là {kind_q} nào?",
         "Tôi ở {old}, {dist}, {prov}. Sau sắp xếp năm 2025, tên đơn vị hành chính cấp xã mới nơi tôi ở là gì?"]
    for newp in sorted(cands):
        r, rows, dist = rng.choice(sorted(cands[newp], key=lambda x: (x[0]["new_commune_code"], x[0]["old_commune"])))
        oldp = r["old_province"]
        prov = f"{prov_name(oldp)}{' cũ' if oldp != newp else ''}"
        dist_l = lower_first(re.sub(r"\s+", " ", dist))
        old = N(r["old_commune"])
        new_full = f"{r['new_type']} {r['new_commune']}"
        cid = "NQ-" + re.match(r"NQ (\d+)/", r["legal_basis"]).group(1) + "-2025-UBTVQH15#D1.K" + \
              re.search(r"khoản (\d+)", r["legal_basis"]).group(1)
        ctext = corpus.text[cid]
        def part(x):
            o = N(x["old_commune"])
            if x["partial"] != "True":
                return o
            return ("phần còn lại của " if f"phần còn lại của {o}" in ctext else "một phần ") + o
        others = [part(x) for x in rows if x is not r]
        out.append(item(category="A_direct", subtype="commune",
                        question=rng.choice(q).format(Old=old[:1].upper() + old[1:], old=old, dist=dist_l, prov=prov,
                                                      prov_tr=prov if prov.endswith(" cũ") else prov + " trước đây",
                                                      kind_q="đặc khu, xã, phường" if r["new_type"] == "đặc khu" else "xã, phường"),
                        gold_answer=ga(f"{old[:1].upper() + old[1:]} ({dist_l}, {prov_name(oldp)}) đã được sắp xếp cùng {join_vi(others)} "
                                       f"thành {new_full}, {prov_name(newp)}.", "entity",
                                       aliases=[new_full, r["new_commune"]]),
                        obsolete_answer={"text": f"Coi {old} vẫn là đơn vị riêng thuộc {dist_l}.",
                                         "obsolete_entities": [dist_l]},
                        evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                        province_new=newp, province_is_control=ctrl[newp], hops=1, difficulty="medium",
                        verification_note="Sinh tự động bằng qgen/build_tv1_v03.py; tên huyện trong câu hỏi lấy từ "
                                          "danh mục 01/03/2025 (dvhcvn), không phải căn cứ; chờ người thứ hai kiểm."))
    return out


def gen_district_traps(em, corpus, dvd, rng):
    out = []
    by_new = collections.defaultdict(list)
    for r in em:
        by_new[r["new_province"]].append(r)
    gold_ids = ["NQ-203-2025-QH15#D2.K2", "LUAT-72-2025-QH15#D51.K3"]
    tpl = {
        "huyện": ["{D} ({p}) hiện có bao nhiêu xã?", "Trụ sở UBND {d} ({p}) hiện đặt ở đâu?",
                  "Chủ tịch UBND {d}, {p} hiện nay là ai?"],
        "quận": ["{D} ({p}) hiện có bao nhiêu phường?", "Tôi cần nộp hồ sơ tại UBND {d}, {p}. Trụ sở ở đâu?"],
        "thị xã": ["{D} ({p}) hiện có bao nhiêu phường và xã?", "Trụ sở UBND {d}, {p} hiện đặt ở đâu?"],
        "thành phố": ["{D} thuộc {p} hiện có bao nhiêu phường?", "Chủ tịch UBND {d} ({p}) hiện nay là ai?"],
    }
    for newp, rows in sorted(by_new.items()):
        r = rng.choice(rows)
        oldp = r["old_province"]
        pool = [d for d in dvd[oldp]
                if toneless(re.sub(r"^(Huyện|Quận|Thị xã|Thành phố)\s+", "", d)) not in {toneless(x) for x in PILOT_DISTRICTS}]
        d = re.sub(r"\s+", " ", rng.choice(sorted(pool)))
        kind = re.match(r"^(Huyện|Quận|Thị xã|Thành phố)", d).group(1).lower()
        d_l = lower_first(d)
        p = prov_name(oldp)
        q = rng.choice(tpl[kind]).format(D=d, d=d_l, p=p)
        extra = "" if oldp == newp else f" {p[:1].upper() + p[1:]} cũng đã hợp nhất vào {prov_name(newp)}."
        nq202 = "NQ-202-2025-QH15#D1.K" + re.search(r"khoản (\d+)", r["legal_basis"]).group(1)
        ev = [corpus.ev(c, cite(c)) for c in gold_ids] + [corpus.ev("LUAT-72-2025-QH15#D1.K1", cite("LUAT-72-2025-QH15#D1.K1"))]
        if oldp != newp:
            ev.append(corpus.ev(nq202, cite(nq202)))
        out.append(item(category="B_obsolete_trap", subtype="district", question=q,
                        gold_answer=ga(f"Câu hỏi có tiền giả định sai: {d_l} không còn là đơn vị hành chính, vì cấp huyện "
                                       f"kết thúc hoạt động từ 01/07/2025.{extra} Địa bàn cũ nay thuộc các xã, phường "
                                       f"trực thuộc {prov_name(newp)}.", "premise_rejection",
                                       aliases=["không còn cấp huyện", "bãi bỏ cấp huyện", "kết thúc hoạt động"],
                                       entities=[newp] if oldp != newp else []),
                        obsolete_answer={"text": f"Trả lời như thể {d_l} vẫn hoạt động (nêu số xã, trụ sở hoặc chủ tịch UBND).",
                                         "obsolete_entities": [d_l] + ([p] if oldp != newp else [])},
                        evidence=ev, gold_clause_ids=gold_ids + ([nq202] if oldp != newp else []),
                        province_new=newp, province_is_control=r["is_control"] == "True",
                        hops=1 if oldp == newp else 2, difficulty="medium" if oldp == newp else "hard",
                        verification_note="Sinh tự động bằng qgen/build_tv1_v03.py; tên huyện lấy từ danh mục 01/03/2025 "
                                          "(dvhcvn); chờ người thứ hai kiểm."))
    return out


def gen_unchanged_controls(lineage, em, corpus, rng, n=9):
    ctrl = {r["new_province"]: r["is_control"] == "True" for r in em}
    us = collections.defaultdict(list)
    for r in lineage:
        if "không thực hiện sắp xếp" in r["legal_basis"]:
            us[r["new_province"]].append(r)
    provs = rng.sample(sorted(us), n)
    q = ["{U} ({p}) có thuộc diện sắp xếp đơn vị hành chính cấp xã năm 2025 không?",
         "Sau đợt sắp xếp năm 2025, {u} của {p} có bị nhập với xã, phường khác không?"]
    q2 = ["{U} có thuộc diện sắp xếp đơn vị hành chính cấp xã năm 2025 không?",
          "Sau đợt sắp xếp năm 2025, {u} có bị nhập với xã, phường khác không?"]
    names = collections.defaultdict(collections.Counter)  # tên (bỏ loại) -> số mã xã mới khác nhau
    for x in lineage:
        for nm in (x["new_commune"], re.sub(r"^(xã|phường|thị trấn|đặc khu)\s+", "", N(x["old_commune"]))):
            names[x["new_province"]][(toneless(nm), x["new_commune_code"])] += 1

    def ambiguous(x):
        key = toneless(x["new_commune"])
        return len({code for (nm, code) in names[x["new_province"]] if nm == key}) > 1

    out = []
    for newp in sorted(provs):
        pool = sorted(us[newp], key=lambda x: x["new_commune_code"])
        r = rng.choice(pool)
        where = ""
        if ambiguous(r):  # kiểm chéo TV3 27/11: trùng tên với xã khác trong tỉnh mới
            if r["old_district"]:  # ghi kèm huyện cũ như nghị quyết tự ghi trong ngoặc
                old_p = r["old_province"]
                where = f", {r['old_district']}, {prov_name(old_p)}{' cũ' if old_p != newp else ''}"
            else:
                r = next(x for x in pool if not ambiguous(x))
        u = f"{r['new_type']} {r['new_commune']}"
        u_q = (f"{u} ({where[2:]}" + (f", nay thuộc {prov_name(newp)})" if where.endswith(" cũ") else ")")) if where else u
        num = re.match(r"NQ (\d+)/", r["legal_basis"]).group(1)
        cid, _ = corpus.summary(f"NQ-{num}-2025-UBTVQH15")
        out.append(item(category="B_obsolete_trap", subtype="commune", item_role="control",
                        question=(rng.choice(q).format(U=u_q[:1].upper() + u_q[1:], u=u_q, p=prov_name(newp)) if not where else
                                  rng.choice(q2).format(U=u_q[:1].upper() + u_q[1:], u=u_q)),
                        gold_answer=ga(f"Không. {u[:1].upper() + u[1:]}{' (' + where[2:] + ')' if where else ''} thuộc nhóm đơn vị hành chính cấp xã không thực hiện sắp xếp, "
                                       f"giữ nguyên và trực thuộc {prov_name(newp)}.", "yes_no",
                                       aliases=["không thực hiện sắp xếp", "giữ nguyên"]),
                        evidence=[corpus.ev(cid, cite(cid))], gold_clause_ids=[cid],
                        province_new=newp, province_is_control=ctrl[newp], hops=1, difficulty="medium"))
    return out


# E: soạn tay từ NQ 190/2025/QH15 và Luật 72/2025/QH15 (TV1, 25/11/2026)
E_ITEMS = [
    ("Hộ kinh doanh của tôi có giấy chứng nhận đăng ký do UBND huyện cấp năm 2024. Sau khi bỏ cấp huyện, giấy này còn dùng được không?",
     "Còn. Giấy tờ đã cấp trước khi sắp xếp, chưa hết hiệu lực hoặc thời hạn sử dụng thì tiếp tục được sử dụng cho đến khi hết hạn hoặc bị sửa đổi, thay thế, thu hồi.",
     "yes_no", ["NQ-190-2025-QH15#D10.K1"], "Khẳng định phải đổi giấy vì UBND huyện không còn."),
    ("Bằng lái xe của tôi còn hạn nhưng ghi địa chỉ tỉnh cũ. Tôi có bắt buộc phải đổi vì tỉnh đã sáp nhập không?",
     "Không bắt buộc. Không được yêu cầu cá nhân, tổ chức cấp đổi giấy tờ đã cấp trước khi sắp xếp khi giấy tờ còn thời hạn sử dụng, trừ trường hợp pháp luật có quy định khác.",
     "yes_no", ["NQ-190-2025-QH15#D10.K2"], "Khẳng định phải đổi giấy tờ theo tên tỉnh mới."),
    ("Cơ quan mới tiếp nhận yêu cầu tôi nộp lại toàn bộ hồ sơ đã nộp trước khi sắp xếp. Yêu cầu này có đúng không?",
     "Không đúng. Cơ quan tiếp nhận không được yêu cầu cá nhân, tổ chức nộp lại hồ sơ đã nộp và không thực hiện lại các bước của thủ tục đã làm trước khi sắp xếp.",
     "yes_no", ["NQ-190-2025-QH15#D5.K2"], "Khuyên nộp lại hồ sơ từ đầu tại cơ quan mới."),
    ("Tôi đang xin giấy phép tại UBND huyện nhưng đến 01/07/2025 vẫn chưa xong. Hồ sơ này sẽ do ai giải quyết tiếp?",
     "Cơ quan tiếp nhận chức năng, nhiệm vụ của chính quyền cấp huyện, hoặc chính quyền cấp xã mới nơi phát sinh công việc, tiếp tục giải quyết, bảo đảm không gián đoạn.",
     "free_text", ["LUAT-72-2025-QH15#D54.K8"], "Hướng dẫn tiếp tục liên hệ UBND huyện."),
    ("Đơn khiếu nại tôi gửi UBND huyện trước tháng 7/2025 chưa được giải quyết. Bây giờ ai có trách nhiệm giải quyết?",
     "Cơ quan tiếp nhận chức năng, nhiệm vụ của chính quyền cấp huyện, hoặc chính quyền cấp xã mới hình thành nơi phát sinh vụ việc, phối hợp với cơ quan liên quan để tiếp tục giải quyết.",
     "free_text", ["LUAT-72-2025-QH15#D54.K8"], "Nói UBND huyện vẫn giải quyết."),
    ("Thủ tục hành chính đang làm dở ở một cơ quan bị sắp xếp lại thì cơ quan nào tiếp tục thực hiện?",
     "Cơ quan tiếp nhận chức năng, nhiệm vụ, quyền hạn sau sắp xếp tiếp tục thực hiện các công việc, thủ tục mà cơ quan bị sắp xếp đang làm.",
     "free_text", ["NQ-190-2025-QH15#D4.K5"], "Nói thủ tục bị huỷ, phải làm lại."),
    ("Khi cơ quan có thẩm quyền giải quyết thủ tục hành chính thay đổi do sắp xếp, việc công bố lại thủ tục được thực hiện thế nào?",
     "Cơ quan, người có thẩm quyền công bố thủ tục hành chính phải điều chỉnh và công bố ngay thủ tục hành chính đã được sửa đổi theo cơ quan, chức danh mới.",
     "free_text", ["NQ-190-2025-QH15#D5.K1"], ""),
    ("Muốn biết cơ quan nào hiện giải quyết một thủ tục sau sắp xếp, người dân xem thông báo chính thức ở đâu?",
     "Trên Cổng hoặc Trang thông tin điện tử của cơ quan tiếp nhận chức năng, nhiệm vụ; đồng thời được công khai tập trung trên Cổng thông tin điện tử của UBND cấp tỉnh (với cơ quan cấp tỉnh).",
     "free_text", ["NQ-190-2025-QH15#D12.K2", "NQ-190-2025-QH15#D12.K1"], ""),
    ("Chức danh xử phạt vi phạm hành chính chỉ đổi tên do sắp xếp, nhiệm vụ không đổi, thì còn thẩm quyền xử phạt không?",
     "Còn. Chức danh chỉ thay đổi tên gọi mà không thay đổi nhiệm vụ, quyền hạn thì giữ nguyên thẩm quyền xử phạt vi phạm hành chính.",
     "yes_no", ["NQ-190-2025-QH15#D8.K1"], "Nói quyết định xử phạt không hợp lệ vì chức danh đã đổi tên."),
    ("Văn bản do UBND huyện ban hành trước 01/07/2025, chưa hết hiệu lực, có còn được áp dụng sau khi cấp huyện kết thúc hoạt động không?",
     "Còn. Văn bản đã ban hành trước khi sắp xếp mà chưa hết hiệu lực thì tiếp tục được áp dụng cho đến khi hết thời hạn hoặc bị sửa đổi, thay thế, bãi bỏ bởi cơ quan có thẩm quyền.",
     "yes_no", ["NQ-190-2025-QH15#D10.K1"], "Nói mọi văn bản của huyện hết hiệu lực từ 01/07/2025."),
    ("Ở đặc khu có dân số thường trú dưới 1.000 người thì có Hội đồng nhân dân không? Ai thực hiện vai trò chính quyền?",
     "Không tổ chức cấp chính quyền địa phương (không có HĐND). UBND đặc khu do UBND cấp tỉnh quyết định thành lập, là cơ quan hành chính nhà nước thực hiện vai trò chính quyền địa phương.",
     "free_text", ["LUAT-72-2025-QH15#D28.K1"], "Nói đặc khu có HĐND và UBND như huyện đảo trước đây."),
    ("Nghị quyết 190/2025/QH15 về xử lý các vấn đề khi sắp xếp bộ máy được thực hiện đến thời điểm nào?",
     "Đến hết ngày 28/02/2027 (trừ một số quy định), và Quốc hội có thể xem xét kéo dài nếu cần.",
     "date", ["NQ-190-2025-QH15#D15.K2", "NQ-190-2025-QH15#D15.K3"], ""),
]

# Bổ sung khoản căn cứ cho câu pilot của TV1 trước đây để TODO_VERIFY_CLAUSE
PILOT_FIX = {
    "P-T-C01": ["LUAT-72-2025-QH15#D1.K1", "LUAT-72-2025-QH15#D2.K1"],
    "P-T-C02": ["NQ-203-2025-QH15#D2.K2", "LUAT-72-2025-QH15#D51.K3"],
    "P-T-C03": ["LUAT-72-2025-QH15#D1.K1"],
    "P-T-D01": ["NQ-190-2025-QH15#D10.K2"],
    "P-T-D03": ["NQ-190-2025-QH15#D10.K1", "NQ-190-2025-QH15#D10.K2"],
    "P-T-D06": ["LUAT-72-2025-QH15#D54.K8"],
}


# Bổ sung sau kiểm chéo TV3 27/11 (theo thứ tự E_ITEMS, 0-based): aliases, đáp án lỗi thời, obsolete_entities
E_EXTRA = {
    3: {"obsolete_entities": ["UBND huyện"]},
    4: {"obsolete_entities": ["UBND huyện"]},
    6: {"obs": "Nói thủ tục vẫn công bố theo cơ quan, chức danh cũ (cấp huyện)."},
    7: {"obs": "Hướng dẫn xem trên Cổng thông tin điện tử của UBND cấp huyện."},
    9: {"obsolete_entities": ["UBND huyện"]},
    11: {"aliases": ["28/02/2027", "28 tháng 02 năm 2027", "28/2/2027"],
         "obs": "Nêu thời hạn khác hoặc nói nghị quyết đã hết hiệu lực."},
}


def gen_procedures(corpus):
    out = []
    for k, (q, a, at, cids, obs) in enumerate(E_ITEMS):
        x = E_EXTRA.get(k, {})
        out.append(item(category="E_procedure", subtype="procedure", question=q,
                        gold_answer=ga(a, at, aliases=x.get("aliases", ())),
                        obsolete_answer={"text": x.get("obs", obs), "obsolete_entities": x.get("obsolete_entities", [])},
                        evidence=[corpus.ev(c, cite(c)) for c in cids], gold_clause_ids=list(cids),
                        hops=1, difficulty="medium",
                        verification_note="Soạn tay từ văn bản gốc (TV1); chờ người thứ hai kiểm."))
    return out


def fix_pilot(pilot, corpus):
    fixed = []
    for r in pilot:
        if r["id"] in PILOT_FIX and r["gold_clause_ids"] == ["TODO_VERIFY_CLAUSE"]:
            cids = PILOT_FIX[r["id"]]
            keep = [e for e in r["evidence"] if e.get("in_corpus")]
            r["evidence"] = keep + [corpus.ev(c, cite(c)) for c in cids if c not in {e["clause_id"] for e in keep}]
            r["gold_clause_ids"] = cids
            r["verification_note"] = (r.get("verification_note") or "") + " TV1 25/11: bổ sung khoản căn cứ từ NQ 190, NQ 203, Luật 72."
            fixed.append(r["id"])
    return fixed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dvhcvn", required=True)
    ap.add_argument("--out", default=str(ROOT / "data/benchmark/tv1_v0.3.jsonl"))
    ap.add_argument("--pilot-out", default=str(ROOT / "data/benchmark/pilot_80_v0.3.jsonl"))
    a = ap.parse_args()
    rng = random.Random(SEED)
    corpus = Corpus(ROOT / "data/parsed")
    em = list(csv.DictReader(open(ROOT / "data/processed/entity_map_63_34_v1.csv", encoding="utf-8")))
    lineage = list(csv.DictReader(open(ROOT / "data/processed/commune_lineage.csv", encoding="utf-8")))
    dvc, dvd = load_dvhcvn(a.dvhcvn, em)

    parts = {
        "A": gen_province(em, corpus, rng) + gen_counts(lineage, em, corpus, rng)
             + gen_commune_lookup(lineage, em, corpus, dvc, rng),
        "B": gen_district_traps(em, corpus, dvd, rng) + gen_unchanged_controls(lineage, em, corpus, rng),
        "E": gen_procedures(corpus),
    }
    rows = []
    for g, items in parts.items():
        for i, r in enumerate(items, 1):
            r["id"] = f"{g}-{i:04d}"
            r["source_id"] = r["id"]
            rows.append(r)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    pilot = [json.loads(l) for l in open(ROOT / "data/benchmark/pilot_80_v0.2.jsonl", encoding="utf-8")]
    fixed = fix_pilot(pilot, corpus)
    with open(a.pilot_out, "w", encoding="utf-8", newline="\n") as f:
        for r in pilot:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    c = collections.Counter((r["category"], r["item_role"]) for r in rows)
    print(f"{len(rows)} câu mới -> {a.out}")
    for k in sorted(c):
        print("  ", k, c[k])
    print(f"pilot: bổ sung khoản cho {len(fixed)} câu {fixed} -> {a.pilot_out}")


if __name__ == "__main__":
    main()
