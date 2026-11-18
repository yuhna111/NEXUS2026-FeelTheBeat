"""Build data/processed/commune_lineage.csv from data/parsed/*.json.

One row per (new commune, old unit) pair:
  new_commune_code  internal id <NQ number>-<clause> (e.g. 1656-005); units left
                    unchanged get <NQ number>-U<nn>. NOT the official GSO code.
  new_commune, new_type, new_province
  old_commune       old unit name incl. type ("phường Hàng Bạc", "huyện Kiên Hải")
  old_district      only when the resolution itself names it in brackets
  old_province      filled for the 11 unchanged (control) provinces; blank for merged ones
  partial           False = whole unit; True = "một phần" / "phần còn lại"
  legal_basis       e.g. "NQ 1656/NQ-UBTVQH15, Điều 1, khoản 5"

Each resolution's own summary clause ("Sau khi sắp xếp, … có N đơn vị …") is used
as a check: formed + unchanged units must equal N and the per-type counts.

Usage:  python scripts/build_lineage.py [--province "Hà Nội"]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

PARSED = Path("data/parsed")
OUT = Path("data/processed/commune_lineage.csv")
ENTITY = Path("data/processed/entity_map_63_34_v1.csv")

TYPES = ["thị trấn", "đặc khu", "phường", "huyện", "quận", "xã"]
TYPE_RE = re.compile(r"^(?:các\s+)?(" + "|".join(TYPES) + r")\s+(.*)$", re.I)
FORM_RE = re.compile(
    r" thành (?:(?:xã|phường|đặc khu)(?: mới)? có tên gọi là )?(xã|phường|đặc khu) (.+?)\.?$",
    re.I)
RENAME_RE = re.compile(r"^Đổi tên (xã|phường) (.+?) thành (xã|phường) (.+?)\.?$")
FULL = "toàn bộ diện tích tự nhiên, quy mô dân số của"
QUAL_RE = re.compile(
    r"(toàn bộ diện tích tự nhiên, quy mô dân số của"
    r"|toàn bộ diện tích tự nhiên của"
    r"|một phần diện tích, quy mô dân số của"
    r"|phần quy mô dân số còn lại của"
    r"|một phần diện tích tự nhiên, toàn bộ quy mô dân số của"
    r"|một phần diện tích tự nhiên, quy mô dân số của"
    r"|một phần diện tích tự nhiên của"
    r"|một phần quy mô dân số của"
    r"|phần còn lại của)")
AFTER_RE = re.compile(r"\s*sau khi sắp xếp theo quy định tại .*?Điều này")
SUMMARY_RE = re.compile(r"có (\d+) đơn vị hành chính cấp xã,? gồm (.+?)(?:;|$)")
COUNT_RE = re.compile(r"(\d+)\s*(xã|phường|đặc khu)")
UNCHANGED_RE = re.compile(r"không thực hiện sắp xếp là (.+?)\.?$")


def split_units(text: str) -> list[tuple[str, str]]:
    """'các phường A, B, xã C (huyện X) và D' → [(type, name-with-bracket), ...]."""
    text = AFTER_RE.sub("", text)
    out, cur_type = [], None
    for tok in _tokens(text):
        tok = re.split(r"\s+sau khi\b", tok)[0].strip(" .;")
        if not tok or re.match(r"^(\d|khoản|Điều)", tok):
            continue
        m = TYPE_RE.match(tok)
        if m:
            cur_type, tok = m.group(1).lower(), m.group(2)
        elif not tok[0].isupper():
            cur_type = None          # non-administrative area, e.g. "khu vực bãi bồi"
            continue
        if cur_type and tok:
            out.append((cur_type, tok))
    return out


_SPLIT = re.compile(r",\s*|\s+và\s+|\s+(?=(?:các\s+)?(?:xã|phường|thị trấn|huyện|quận)\s+[A-ZĐ0-9])")


def _tokens(text: str) -> list[str]:
    """Split on commas / 'và' / a new type word, but never inside brackets."""
    out, depth, start = [], 0, 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            m = _SPLIT.match(text, i)
            if m and m.end() > i:
                out.append(text[start:i])
                start = i = m.end()
                continue
        i += 1
    out.append(text[start:])
    return out


def old_units(body: str) -> list[dict]:
    """Old units of one clause with their partial flag."""
    body = re.sub(r"^Sắp xếp\s*", "", body)
    parts = QUAL_RE.split(body)
    units = []
    for i in range(1, len(parts), 2):
        partial = parts[i] != FULL
        for typ, name in split_units(parts[i + 1]):
            dist = ""
            m = re.match(r"^(.*?)\s*\((.+)\)$", name)
            if m:
                name, dist = m.group(1), m.group(2)
            units.append({"old_commune": f"{typ} {name}", "old_district": dist,
                          "partial": partial})
    return units


def province_rows(doc: dict, control: set[str]) -> tuple[list[dict], list[str]]:
    num = doc["doc_number"].split("/")[0] or doc["doc_id"][3:7]
    prov = doc["province"]
    art1 = next(a for a in doc["articles"] if a["article"] == "1")
    rows, errors = [], []
    formed: dict[str, int] = {}
    expected_total, expected_types, unchanged = None, {}, []
    for c in art1["clauses"]:
        text, basis = c["text"], f"NQ {num}/NQ-UBTVQH15, Điều 1, khoản {c['clause']}"
        if text.startswith("Sau khi sắp xếp"):
            m = SUMMARY_RE.search(text)
            if m:
                expected_total = int(m.group(1))
                expected_types = {t: int(n) for n, t in COUNT_RE.findall(m.group(2))}
            m = UNCHANGED_RE.search(text)
            if m:
                unchanged = split_units(m.group(1))
            continue
        m = RENAME_RE.match(text)
        if m:
            new_type, new_name = m.group(3), m.group(4)
            olds = [{"old_commune": f"{m.group(1)} {m.group(2)}", "old_district": "",
                     "partial": False}]
        else:
            m = FORM_RE.search(text)
            if not m:
                errors.append(f"{basis}: no formation pattern: {text[:90]}")
                continue
            new_type, new_name = m.group(1).lower(), m.group(2)
            olds = old_units(text[: m.start()])
            if not olds:
                errors.append(f"{basis}: no old units parsed")
        formed[new_type] = formed.get(new_type, 0) + 1
        code = f"{num}-{int(c['clause']):03d}"
        for o in olds:
            rows.append({"new_commune_code": code, "new_commune": new_name,
                         "new_type": new_type, "new_province": prov,
                         "old_commune": o["old_commune"], "old_district": o["old_district"],
                         "old_province": prov if prov in control else "",
                         "partial": o["partial"], "legal_basis": basis})
    summ = next(c for c in art1["clauses"] if c["text"].startswith("Sau khi sắp xếp"))
    for i, (typ, name) in enumerate(unchanged, 1):
        dist = ""
        mm = re.match(r"^(.*?)\s*\((.+)\)$", name)
        if mm:
            name, dist = mm.group(1), mm.group(2)
        formed[typ] = formed.get(typ, 0) + 1
        rows.append({"new_commune_code": f"{num}-U{i:02d}", "new_commune": name,
                     "new_type": typ, "new_province": prov,
                     "old_commune": f"{typ} {name}", "old_district": dist,
                     "old_province": prov if prov in control else "", "partial": False,
                     "legal_basis": f"NQ {num}/NQ-UBTVQH15, Điều 1, khoản {summ['clause']} "
                                    "(không thực hiện sắp xếp)"})
    total = sum(formed.values())
    if expected_total is not None and total != expected_total:
        errors.append(f"{prov}: parsed {total} units, resolution says {expected_total}")
    if expected_types and formed != expected_types:
        errors.append(f"{prov}: types {formed} ≠ {expected_types}")
    return rows, errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--province", help="build only this new province (e.g. 'Hà Nội')")
    args = ap.parse_args()
    with open(ENTITY, encoding="utf-8") as f:
        control = {r["new_province"] for r in csv.DictReader(f) if r["is_control"] == "True"}
    all_rows, all_err = [], []
    for p in sorted(PARSED.glob("NQ-16*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if args.province and doc["province"] != args.province:
            continue
        rows, errs = province_rows(doc, control)
        all_rows += rows
        all_err += errs
    cols = ["new_commune_code", "new_commune", "new_type", "new_province", "old_commune",
            "old_district", "old_province", "partial", "legal_basis"]
    out = OUT if not args.province else OUT.with_name(f"commune_lineage_{args.province}.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)
    n_new = len({r["new_commune_code"] for r in all_rows})
    print(f"{n_new} new communes, {len(all_rows)} lineage rows → {out}")
    for e in all_err:
        print("  CHECK:", e)


if __name__ == "__main__":
    main()
