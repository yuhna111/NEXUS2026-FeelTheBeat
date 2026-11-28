"""Các file câu hỏi v0.3 của TV1 và TV3 phải hợp lệ theo docs/qa_schema.md và trỏ đúng khoản trong data/parsed."""
from pathlib import Path

import pytest

from eval.qa_schema import load_clause_ids, read_jsonl, validate_records

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "data/benchmark/tv1_v0.3.jsonl",
    "data/benchmark/tv3_v0.3.jsonl",
    "data/benchmark/pilot_80_v0.3.jsonl",
    "data/benchmark/benchmark_v0.3.jsonl",
]


@pytest.mark.parametrize("name", FILES)
def test_v03_valid(name):
    path = ROOT / name
    if not path.exists():
        pytest.skip(f"{name} chưa có")
    recs = read_jsonl(path)
    assert recs
    assert validate_records(recs, load_clause_ids(ROOT / "data/parsed")) == {}


def test_tv1_v03_shape():
    path = ROOT / "data/benchmark/tv1_v0.3.jsonl"
    if not path.exists():
        pytest.skip("chưa có")
    recs = read_jsonl(path)
    b = [r for r in recs if r["category"] == "B_obsolete_trap"]
    controls = sum(r["item_role"] == "control" for r in b)
    assert 0.15 <= controls / len(b) <= 0.30
    assert all(r["gold_clause_ids"] != ["TODO_VERIFY_CLAUSE"] for r in recs)
    assert all(r["verified"] for r in recs)


def test_tv3_v03_shape():
    path = ROOT / "data/benchmark/tv3_v0.3.jsonl"
    if not path.exists():
        pytest.skip("chưa có")
    recs = read_jsonl(path)
    assert len(recs) == 60
    cats = {r["category"] for r in recs}
    assert cats == {"C_multihop_spatial", "D_before_after", "F_rumor"}
    assert not any(r["verified"] for r in recs)
    # IDs must not collide with pilot_80_v0.3 or tv1_v0.3
    other_ids = set()
    for other in ("data/benchmark/pilot_80_v0.3.jsonl", "data/benchmark/tv1_v0.3.jsonl"):
        p = ROOT / other
        if p.exists():
            other_ids.update(r["id"] for r in read_jsonl(p))
    assert not (other_ids & {r["id"] for r in recs})


def test_benchmark_v03_merged_shape():
    path = ROOT / "data/benchmark/benchmark_v0.3.jsonl"
    if not path.exists():
        pytest.skip("chưa có")
    recs = read_jsonl(path)
    assert len(recs) == 308
    assert len({r["id"] for r in recs}) == 308
    assert sum(r["verified"] for r in recs) >= 168
