"""Thêm bí danh cấp xã vào eval/aliases.csv (TV1, tuần 3).

Chỉ thêm biến thể an toàn: cách bỏ dấu kiểu cũ của tên xã, phường, đặc khu mới
(dấu thanh đặt ở nguyên âm sau trong oa, oe, uy cuối âm tiết: "Hòa" -> "Hoà",
"Thủy" -> "Thuỷ"). Hai cách viết chỉ cùng một tên, nên không gây nhầm giữa các xã
trùng tên. Không thêm tên không dấu (trùng nhau quá nhiều).

Chạy: python scripts/build_commune_aliases.py
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "TV1 25/11: bỏ dấu kiểu cũ, commune_lineage"
TONE = {"̀": 0, "́": 1, "̉": 2, "̃": 3, "̣": 4}
FORMS = {"a": "àáảãạ", "e": "èéẻẽẹ", "y": "ỳýỷỹỵ", "o": "òóỏõọ", "u": "ùúủũụ"}


def tone_of(ch: str) -> int | None:
    for c in unicodedata.normalize("NFD", ch)[1:]:
        if c in TONE:
            return TONE[c]
    return None


def old_style(name: str) -> str:
    def fix(word: str) -> str:
        if len(word) < 2:
            return word
        a, b = word[-2], word[-1]
        base_a = unicodedata.normalize("NFD", a)[0]
        t = tone_of(a)
        if t is None or (base_a.lower(), b.lower()) not in {("o", "a"), ("o", "e"), ("u", "y")}:
            return word
        if base_a.lower() == "u" and len(word) >= 3 and word[-3].lower() == "q":
            return word
        new_a = base_a
        new_b = FORMS[b.lower()][t]
        if b.isupper():
            new_b = new_b.upper()
        return word[:-2] + new_a + new_b
    return " ".join(fix(w) for w in unicodedata.normalize("NFC", name).split(" "))


def main() -> None:
    path = ROOT / "eval/aliases.csv"
    rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
    have = {r["alias"] for r in rows}
    names = sorted({r["new_commune"] for r in csv.DictReader(open(ROOT / "data/processed/commune_lineage.csv", encoding="utf-8"))})
    added = []
    for n in names:
        v = old_style(n)
        if v != n and v not in have:
            added.append({"alias": v, "canonical": n, "source": SRC})
            have.add(v)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["alias", "canonical", "source"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows + added)
    print(f"{len(names)} tên xã mới; thêm {len(added)} bí danh -> {path}")


if __name__ == "__main__":
    main()
