import importlib.util
from pathlib import Path

from eval.qa_schema import TODO_CLAUSE, validate_record

_spec = importlib.util.spec_from_file_location(
    "merge_pilot_sets", Path(__file__).resolve().parents[1] / "scripts" / "merge_pilot_sets.py")
mp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mp)


def _toan(qid, evidence):
    return {
        "id": qid, "source_set": "toan50", "source_id": qid[-3:], "category": "A_direct",
        "subtype": None, "item_role": "trap", "question": "Q?", "reference_date": "2026-11-19",
        "gold_answer": {"text": "G", "aliases": [], "answer_type": "free_text", "entities": []},
        "obsolete_answer": {"text": "O", "obsolete_entities": []}, "evidence": evidence,
        "verified": False, "verification_note": "", "version": "pilot-0.1",
    }


EV_IN = {"doc_id": "NQ-202-2025-QH15", "article": "1", "clause": "24",
         "clause_id": "NQ-202-2025-QH15#D1.K24", "citation": "NQ 202/2025/QH15, Điều 1, khoản 24",
         "in_corpus": True}
EV_OUT = {"doc_id": None, "article": None, "clause": None, "clause_id": None,
          "citation": "NQ 76/2025/UBTVQH15 [TODO_VERIFY]", "in_corpus": False}


def test_upgrade_derives_gold_and_flags_it():
    r = mp.upgrade_toan(_toan("P-T-A01", [EV_IN]))
    assert r["gold_clause_ids"] == ["NQ-202-2025-QH15#D1.K24"]
    assert "TV1 cần xác nhận" in r["verification_note"]
    assert r["version"] == "pilot-0.2" and r["hops"] is None
    assert validate_record(r) == []


def test_upgrade_without_corpus_evidence_is_todo():
    r = mp.upgrade_toan(_toan("P-T-E02", [EV_OUT]))
    assert r["gold_clause_ids"] == [TODO_CLAUSE]
    assert r["verification_note"] == ""
    assert validate_record(r) == []


def test_merge_drops_old_vinh_copy_and_keeps_content():
    toan = [_toan("P-T-A01", [EV_IN]), _toan("P-V-A01", [EV_IN])]  # P-V-* = stale copy
    vinh = [{**mp.upgrade_toan(_toan("P-V-A01", [EV_IN])), "source_set": "vinh30"}]
    out = mp.merge(toan, vinh)
    assert [r["id"] for r in out] == ["P-T-A01", "P-V-A01"]
    assert out[1]["source_set"] == "vinh30"
    assert out[0]["question"] == toan[0]["question"]
    assert list(out[0])[:3] == ["id", "source_set", "source_id"]
