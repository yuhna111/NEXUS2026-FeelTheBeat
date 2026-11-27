"""Tests for eval/judge_prompt_v1.txt and eval/judge.py (TV3)."""
from __future__ import annotations

from eval.judge import (
    DEFAULT_PROMPT,
    compare_with_human,
    judge_predictions,
    load_prompt_template,
    parse_judge_response,
    render_prompt,
    same_model_family,
)


def test_prompt_template_has_group_d_examples_and_renders():
    tpl = load_prompt_template(DEFAULT_PROMPT)
    assert "Nhóm D" in tpl
    assert "thiếu vế sau" in tpl
    assert "BLENDED" in tpl
    q = {
        "id": "P-V-D01",
        "reference_date": "2026-11-27",
        "question": "Trước và sau ngày 01/07/2025, chính quyền địa phương có mấy cấp?",
        "gold_answer": {"text": "Trước 3 cấp, sau 2 cấp."},
        "obsolete_answer": {"obsolete_entities": ["3 cấp"]},
    }
    rendered = render_prompt(q, "Hiện nay gồm 3 cấp.", tpl)
    assert "2026-11-27" in rendered
    assert "Hiện nay gồm 3 cấp." in rendered
    assert '{"label":' in rendered


def test_parse_judge_response_variants():
    assert parse_judge_response('{"label": "STALE", "rationale": "Vẫn nói 63 tỉnh."}') == (
        "STALE",
        "Vẫn nói 63 tỉnh.",
    )
    fenced = '```json\n{"label": "blended", "rationale": "Trộn cũ mới."}\n```'
    assert parse_judge_response(fenced) == ("BLENDED", "Trộn cũ mới.")
    assert parse_judge_response("Nhãn phù hợp là OTHER_ERROR vì thiếu vế sau.")[0] == "OTHER_ERROR"
    assert parse_judge_response('{"label": "UNKNOWN", "rationale": "?"}')[0] is None


def test_same_model_family_guard():
    assert same_model_family("gemini", "gemini-3.5-flash-lite", "gemini-flash")
    assert same_model_family("vllm", "Qwen/Qwen2.5-7B-Instruct-AWQ", "qwen-7b")
    assert not same_model_family("anthropic", "claude-3-5-haiku-20241022", "gemini-flash")
    assert not same_model_family("vllm", "meta-llama/Llama-3.1-8B-Instruct", "qwen-7b")


def test_judge_predictions_and_human_comparison():
    class FakeClient:
        model = "fake-judge"

        def generate(self, prompt: str):
            lab = "STALE" if "Câu trả lời cần chấm: VN có 63 tỉnh." in prompt else "CORRECT_CURRENT"
            return {"output": f'{{"label": "{lab}", "rationale": "mock"}}', "model": self.model, "key": "k"}

    bench = {
        "Q1": {
            "id": "Q1",
            "reference_date": "2026-11-27",
            "question": "VN có mấy tỉnh?",
            "gold_answer": {"text": "34 tỉnh", "answer_type": "number", "aliases": ["34"]},
            "obsolete_answer": {"text": "63 tỉnh", "obsolete_entities": ["63 tỉnh"]},
        },
        "Q2": {
            "id": "Q2",
            "reference_date": "2026-11-27",
            "question": "VN có mấy cấp?",
            "gold_answer": {"text": "2 cấp", "answer_type": "number", "aliases": ["2"]},
            "obsolete_answer": {"text": "3 cấp", "obsolete_entities": ["3 cấp"]},
        },
    }
    preds = [
        {"question_id": "Q1", "model_id": "m1", "output": "VN có 63 tỉnh."},
        {"question_id": "Q2", "model_id": "m1", "output": "VN có 2 cấp."},
    ]
    rows = judge_predictions(preds, bench, FakeClient(), template=load_prompt_template())
    assert [r["label"] for r in rows] == ["STALE", "CORRECT_CURRENT"]
    human = [
        {"question_id": "Q1", "model_id": "m1", "label": "STALE"},
        {"question_id": "Q2", "model_id": "m1", "label": "CORRECT_CURRENT"},
    ]
    stats = compare_with_human(rows, human)
    assert stats["n"] == 2
    assert stats["agreement"] == 1.0
    assert stats["kappa"] == 1.0
