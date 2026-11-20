import json
from pathlib import Path

import pytest

from eval.staleness_rules import rule_verdict
from rag.run_inference import done_ids, load_subset_ids, select_models

OBSOLETE = ["huyện Gia Lâm", "thị trấn Trâu Quỳ"]


@pytest.mark.parametrize("answer,expected", [
    ("Trụ sở đặt tại phường Long Biên, Hà Nội.", "NOT_STALE"),
    ("Trụ sở UBND huyện Gia Lâm đặt tại thị trấn Trâu Quỳ.", "STALE"),
    ("Huyện Gia Lâm cũng có trụ sở tại Trâu Quỳ.", "STALE"),  # "cũng" is not the marker "cũ"
    ("Huyện Gia Lâm đã không còn; địa bàn nay thuộc các xã mới của Hà Nội.", None),
    ("Trước đây là huyện Gia Lâm, từ 01/07/2025 cấp huyện đã bị bãi bỏ.", None),
    ("Huyện Gia Lâm cũ được sắp xếp thành các xã mới.", None),
    ("Địa bàn huyện Gia Lâm (cũ) gồm các xã mới.", None),
    # a stray "cũ" not attached to the obsolete entity is not a change marker
    ("UBND huyện Gia Lâm vẫn làm việc ở trụ sở cũ tại thị trấn Trâu Quỳ.", "STALE"),
    ("Huyện Gia Lâm có trụ sở tại Trâu Quỳ, gần đường cũ.", "STALE"),
])
def test_rule_verdict(answer, expected):
    assert rule_verdict(answer, OBSOLETE) == expected


def test_judge_prompt_formats():
    tpl = Path("eval/judge_prompt_v1.txt").read_text(encoding="utf-8")
    out = tpl.format(reference_date="2026-11-01", question="Q", gold_answer="G",
                     obsolete_entities="O", prediction="P")
    assert '{"label": "...", "rationale": "<1 câu>"}' in out


def test_done_ids(tmp_path):
    p = tmp_path / "m.jsonl"
    assert done_ids(p) == set()
    p.write_text("\n".join(json.dumps({"question_id": q}) for q in ["A-1", "B-2"]) + "\n",
                 encoding="utf-8")
    assert done_ids(p) == {"A-1", "B-2"}


def test_load_subset_ids(tmp_path):
    (tmp_path / "s.txt").write_text("A-1\n\nB-2\n", encoding="utf-8")
    assert load_subset_ids("s", tmp_path) == {"A-1", "B-2"}
    with pytest.raises(SystemExit):
        load_subset_ids("missing", tmp_path)


def test_select_models():
    models = [{"id": "a", "snapshot": "a-2026"}, {"id": "b", "snapshot": ""}]
    assert [m["id"] for m in select_models(models, "a")] == ["a"]
    with pytest.raises(SystemExit, match="snapshot"):
        select_models(models, "")
    with pytest.raises(SystemExit, match="nope"):
        select_models(models, "nope")
