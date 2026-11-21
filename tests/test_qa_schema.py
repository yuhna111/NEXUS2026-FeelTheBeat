import copy
import json

import pytest

from eval.qa_schema import (
    TODO_CLAUSE,
    chunk_id_to_clause_id,
    clause_id_to_chunk_id,
    load_clause_ids,
    recall_gold_ids,
    validate_record,
    validate_records,
)

CID = "NQ-202-2025-QH15#D1.K14"

VALID = {
    "id": "P-V-A02", "category": "A_direct", "item_role": "trap",
    "question": "Tỉnh Lâm Đồng hiện nay được hình thành từ những tỉnh nào?",
    "reference_date": "2026-11-19",
    "gold_answer": {"text": "Lâm Đồng, Đắk Nông, Bình Thuận.", "aliases": ["Đắk Nông"],
                    "answer_type": "entity_list", "entities": ["Lâm Đồng"]},
    "obsolete_answer": {"text": "Lâm Đồng là tỉnh riêng.", "obsolete_entities": ["tỉnh riêng"]},
    "evidence": [{"doc_id": "NQ-202-2025-QH15", "article": "1", "clause": "14", "clause_id": CID,
                  "citation": "NQ 202/2025/QH15, Điều 1, khoản 14", "in_corpus": True}],
    "gold_clause_ids": [CID], "verified": False, "version": "pilot-0.2",
    "province_is_control": False, "hops": None, "difficulty": None, "annotator": ["TV3"],
}


def mutate(**changes):
    rec = copy.deepcopy(VALID)
    for path, value in changes.items():
        node = rec
        *parents, leaf = path.split("__")
        for p in parents:
            node = node[p]
        node[leaf] = value
    return rec


def test_valid_record():
    assert validate_record(VALID, {CID}) == []


def test_todo_sentinel_valid_and_excluded_from_recall():
    rec = mutate(gold_clause_ids=[TODO_CLAUSE])
    assert validate_record(rec) == []
    assert recall_gold_ids(rec) is None


@pytest.mark.parametrize("changes,fragment", [
    ({"gold_clause_ids": [CID, TODO_CLAUSE]}, "only element"),
    ({"gold_clause_ids": []}, "non-empty"),
    ({"gold_clause_ids": ["NQ-202-2025-QH15#Art1.14"]}, "bad format"),
    ({"gold_clause_ids": ["NQ-202-2025-QH15#D1.K1"]}, "not listed in evidence"),
    ({"category": "Z"}, "category"),
    ({"reference_date": "19/11/2026"}, "reference_date"),
    ({"item_role": "control"}, "must be empty"),
    ({"gold_answer__answer_type": "list"}, "answer_type"),
    ({"evidence": []}, "evidence"),
    ({"hops": 0}, "hops"),
])
def test_invalid_records(changes, fragment):
    errors = validate_record(mutate(**changes))
    assert any(fragment in e for e in errors), errors


def test_unknown_clause_against_corpus():
    errors = validate_record(VALID, known_clause_ids={"NQ-202-2025-QH15#D1.K1"})
    assert any("not found in data/parsed" in e for e in errors)


def test_evidence_mismatch_doc_id():
    rec = mutate()
    rec["evidence"][0]["doc_id"] = "NQ-203-2025-QH15"
    assert any("doc_id does not match" in e for e in validate_record(rec))


def test_missing_field():
    rec = mutate()
    del rec["gold_clause_ids"]
    assert validate_record(rec) == ["missing field: gold_clause_ids"]


def test_recall_fallback_for_pilot_01_records():
    rec = mutate()
    del rec["gold_clause_ids"]
    assert recall_gold_ids(rec) == {CID}
    rec["evidence"][0]["in_corpus"] = False
    assert recall_gold_ids(rec) is None


def test_duplicate_ids():
    assert validate_records([VALID, VALID]) == {"P-V-A02": ["id: duplicate"]}


def test_id_bridge_round_trip():
    assert clause_id_to_chunk_id(CID) == "NQ-202-2025-QH15#Art1.14"
    assert chunk_id_to_clause_id("NQ-202-2025-QH15#Art1.14") == CID
    assert chunk_id_to_clause_id("NQ-202-2025-QH15#fixed3") is None
    with pytest.raises(ValueError):
        clause_id_to_chunk_id("NQ-202-2025-QH15#Art1.14")


def test_load_clause_ids(tmp_path):
    doc = {"doc_id": "X", "articles": [{"article": "1", "clauses": [{"id": "X-1-2025-QH15#D1.K1"}]},
                                       {"article": "2", "clauses": []}]}
    (tmp_path / "X.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert load_clause_ids(tmp_path) == {"X-1-2025-QH15#D1.K1"}
    assert load_clause_ids(tmp_path / "missing") == set()
