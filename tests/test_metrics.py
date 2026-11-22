import json
import unicodedata

import pytest

from eval.metrics import (
    NEEDS_JUDGE,
    Ratio,
    answer_match,
    answer_set_f1,
    auto_label,
    bootstrap_ci,
    clause_coverage,
    cohen_kappa,
    evaluate,
    exact_match,
    extract_entities,
    extract_numbers,
    fixed_chunk_hit,
    fixed_hit_rank,
    holm_bonferroni,
    knowledge_override_rate,
    load_labels,
    load_predictions,
    main,
    mcnemar_exact,
    mrr,
    paired_bootstrap,
    prior_bias_error_rate,
    read_jsonl,
    recall_at_k,
    set_f1,
    staleness_rate,
    token_f1,
    yes_no_polarity,
)
from eval.normalize import normalize
from eval.staleness_rules import (
    analyze,
    has_change_marker,
    is_abstention,
    mentions_obsolete,
    rejects_premise,
    rule_verdict,
)

GIA_LAM = ["huyện Gia Lâm", "thị trấn Trâu Quỳ", "UBND huyện"]
HOI_AN = ["Quảng Nam", "thành phố Hội An"]


def q(qid, category, answer_type, gold_text, entities=(), aliases=(), obsolete=(), role="trap",
      gold_clause_ids=("NQ-202-2025-QH15#D1.K10",), question="Câu hỏi?", province_is_control=False):
    return {
        "id": qid, "category": category, "item_role": role, "question": question,
        "reference_date": "2026-11-19",
        "gold_answer": {"text": gold_text, "aliases": list(aliases), "answer_type": answer_type,
                        "entities": list(entities)},
        "obsolete_answer": {"text": "" if role == "control" else "cũ",
                            "obsolete_entities": [] if role == "control" else list(obsolete)},
        "evidence": [], "gold_clause_ids": list(gold_clause_ids), "province_is_control": province_is_control,
        "verified": False, "version": "test",
    }


BENCH = {
    "P-V-C03": q("P-V-C03", "C_multihop_spatial", "entity", "TP Đà Nẵng", ["Đà Nẵng"], obsolete=HOI_AN,
                 question="Phố cổ Hội An hiện thuộc tỉnh/thành phố nào?"),
    "P-V-A02": q("P-V-A02", "A_direct", "entity_list", "Lâm Đồng, Đắk Nông, Bình Thuận",
                 ["Lâm Đồng", "Đắk Nông", "Bình Thuận"], obsolete=["tỉnh riêng"],
                 gold_clause_ids=("NQ-202-2025-QH15#D1.K14",)),
    "P-V-A01": q("P-V-A01", "A_direct", "number", "34 đơn vị", aliases=["34", "28 tỉnh"], obsolete=["63"],
                 gold_clause_ids=("NQ-202-2025-QH15#D1.K24",)),
    "P-V-A06": q("P-V-A06", "A_direct", "yes_no", "Không. Thanh Hóa giữ nguyên.", role="control",
                 gold_clause_ids=("TODO_VERIFY_CLAUSE",), province_is_control=True),
    "P-V-B01": q("P-V-B01", "B_obsolete_trap", "premise_rejection", "Không còn huyện Gia Lâm.",
                 ["Hà Nội"], obsolete=GIA_LAM, gold_clause_ids=("LUAT-72-2025-QH15#D51.K3",)),
    "P-V-B07": q("P-V-B07", "B_obsolete_trap", "entity", "Trung Quốc", ["Trung Quốc"], role="control",
                 gold_clause_ids=("TODO_VERIFY_CLAUSE",), province_is_control=True),
}


def pred(qid, output, config="C1", context_ids=(), model="qwen-7b", **extra):
    return {"model_id": model, "config": config, "question_id": qid, "prompt": "p",
            "context_ids": None if context_ids is None else list(context_ids), "output": output, "timestamp": "2026-11-21T10:00:00+0700",
            **extra}


@pytest.mark.parametrize("raw,expected", [
    ("Tỉnh Lâm Đồng", "lâm đồng"),
    ("TP. Hồ Chí Minh", "hồ chí minh"),
    ("Thành phố Hồ Chí Minh", "hồ chí minh"),
    ("TPHCM", "hồ chí minh"),
    ("Bà Rịa-Vũng Tàu", "bà rịa – vũng tàu"),
    ("  phường   Bến Nghé ", "bến nghé"),
    ("Xã Trâu Quỳ.", "trâu quỳ"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_normalize_nfc():
    assert normalize(unicodedata.normalize("NFD", "Lâm Đồng")) == "lâm đồng"


@pytest.mark.parametrize("answer", [
    "Huyện Gia Lâm đã không còn; địa bàn nay thuộc các xã mới của Hà Nội.",
    "Trước đây là huyện Gia Lâm, từ 01/07/2025 cấp huyện đã bị bãi bỏ.",
    "Huyện Gia Lâm cũ được sắp xếp thành các xã mới.",
    "Địa bàn huyện Gia Lâm (cũ) gồm các xã mới.",
    "Trước sáp nhập, khu vực này thuộc huyện Gia Lâm cũ, nay là xã Gia Lâm.",
    "Hiện nay không còn UBND huyện Gia Lâm vì cấp huyện đã kết thúc hoạt động.",
    "Xã Gia Lâm mới có trụ sở đặt tại khu vực Trâu Quỳ.",
])
def test_retrospective_mentions_are_not_stale(answer):
    assert rule_verdict(answer, GIA_LAM) == "NOT_STALE"


@pytest.mark.parametrize("answer,obsolete", [
    ("Hội An trước đây thuộc Quảng Nam, nay thuộc Đà Nẵng.", HOI_AN),
    ("Tỉnh Quảng Nam cũ đã sáp nhập vào thành phố Đà Nẵng.", HOI_AN),
    ("Từ 01/07/2025, tỉnh Bình Định được sáp nhập với tỉnh Gia Lai.", ["Bình Định"]),
    ("Cả nước giảm từ 63 tỉnh xuống còn 34 tỉnh, thành phố.", []),
    ("Trước ngày 01/07/2025: Trung tâm hành chính đặt tại thành phố Lào Cai.", ["TP Lào Cai"]),
])
def test_valid_comparative_mentions_with_cu_or_markers(answer, obsolete):
    assert rule_verdict(answer, obsolete) == "NOT_STALE"


@pytest.mark.parametrize("answer,obsolete", [
    ("Trụ sở UBND huyện Gia Lâm đặt tại thị trấn Trâu Quỳ.", GIA_LAM),
    ("Huyện Gia Lâm cũng có trụ sở tại Trâu Quỳ.", GIA_LAM),
    ("UBND huyện Gia Lâm vẫn làm việc ở trụ sở cũ tại thị trấn Trâu Quỳ.", GIA_LAM),
    ("Huyện Gia Lâm có trụ sở tại Trâu Quỳ, gần đường cũ.", GIA_LAM),
    ("Việt Nam hiện có 63 tỉnh, thành phố trực thuộc trung ương.", []),
    ("Chủ tịch UBND quận Hoàn Kiếm hiện nay là ông A.", []),
    ("Phố cổ Hội An hiện thuộc thành phố Hội An, tỉnh Quảng Nam.", HOI_AN),
    ("Huyện Gia Lâm không bị bãi bỏ, vẫn hoạt động bình thường.", GIA_LAM),
    ("Ở Việt Nam, chính quyền địa phương gồm 3 cấp: tỉnh, huyện, xã.", []),
])
def test_clearly_stale_answers(answer, obsolete):
    assert rule_verdict(answer, obsolete) == "STALE"


@pytest.mark.parametrize("answer,obsolete,current", [
    ("Hội An có thể thuộc Quảng Nam hoặc Đà Nẵng tùy thời điểm.", HOI_AN, None),
    ("Huyện Gia Lâm trước đây thuộc Hà Nội; hiện UBND huyện Gia Lâm vẫn đặt tại Trâu Quỳ.", GIA_LAM, None),
    ("Sau sắp xếp năm 2025, Côn Đảo thuộc tỉnh Bà Rịa - Vũng Tàu.", ["Bà Rịa – Vũng Tàu"], None),
    ("Hội An thuộc TP Đà Nẵng, tỉnh Quảng Nam.", HOI_AN, ["Đà Nẵng"]),
])
def test_ambiguous_or_blended_go_to_judge(answer, obsolete, current):
    assert rule_verdict(answer, obsolete, current) is None


def test_refusal_that_presupposes_district_is_stale():
    answer = "Tôi không có dữ liệu cập nhật để xác nhận ai đang giữ chức Chủ tịch UBND huyện Gia Lâm."
    assert is_abstention(answer)
    assert rule_verdict(answer, GIA_LAM) == "STALE"


def test_plain_refusal_is_not_stale_but_is_abstention():
    answer = "Xin lỗi, tôi không có thông tin về câu hỏi này."
    assert rule_verdict(answer, GIA_LAM) == "NOT_STALE"
    assert is_abstention(answer)
    assert is_abstention("") and is_abstention(None)


def test_rules_are_case_tone_and_unicode_safe():
    nfd = unicodedata.normalize("NFD", "HUYỆN GIA LÂM hiện có 20 xã.")
    assert rule_verdict(nfd, GIA_LAM) == "STALE"
    assert rule_verdict("Tỉnh Hoà Bình hiện có 10 huyện.", ["tỉnh Hòa Bình"]) == "STALE"
    assert rule_verdict("Uỷ ban nhân dân huyện Gia Lâm ở Trâu Quỳ.", ["UBND huyện"]) == "STALE"


def test_numbered_list_is_not_an_obsolete_count():
    answer = "Có 6 thành phố: 1. Hà Nội. 2. Huế. 3. Hải Phòng. 4. Đà Nẵng. 5. Thành phố Hồ Chí Minh. 6. Cần Thơ."
    assert rule_verdict(answer, ["5 thành phố"]) == "NOT_STALE"


def test_stray_cu_and_thuc_hien_are_not_markers():
    assert not has_change_marker("UBND vẫn làm việc ở trụ sở cũ.")
    assert has_change_marker("Trước khi thực hiện sắp xếp, huyện Mèo Vạc có 17 xã.")
    assert rule_verdict("Trước khi thực hiện sắp xếp, huyện Mèo Vạc có 17 xã.", ["huyện Mèo Vạc"]) == "NOT_STALE"


def test_dates_before_reform_are_not_retrospective():
    answer = "Trước ngày 01/01/2025, tỉnh Quảng Bình có 151 xã."
    assert rule_verdict(answer, ["tỉnh Quảng Bình"]) == "STALE"


def test_header_frame_applies_to_following_lines():
    answer = "Trước ngày 01/07/2025:\nTỉnh Nam Định có 10 huyện.\nSau ngày 01/07/2025:\nNinh Bình mới."
    assert rule_verdict(answer, ["tỉnh Nam Định"]) == "NOT_STALE"


def test_mentions_obsolete_keeps_unit_type():
    assert mentions_obsolete("Xã Gia Lâm và phường Thủ Đức", ["huyện Gia Lâm", "TP Thủ Đức"]) == []
    assert mentions_obsolete("TP. Thủ Đức có 34 phường", ["TP Thủ Đức", "34 phường"]) == ["TP Thủ Đức", "34 phường"]
    assert [m.status for m in analyze("Quận Hoàn Kiếm không còn là đơn vị cấp quận.", ["quận Hoàn Kiếm"])] == ["RETRO"]


def test_rule_inputs_none_or_empty():
    assert rule_verdict(None, GIA_LAM) == "NOT_STALE"
    assert rule_verdict("", []) == "NOT_STALE"
    assert rule_verdict("Huyện Gia Lâm có 20 xã.", ["", "huyện Gia Lâm"]) == "STALE"


def test_rejects_premise_respects_negation():
    assert rejects_premise("Từ 01/07/2025 không còn huyện Gia Lâm.")
    assert not rejects_premise("Huyện Gia Lâm không bị bãi bỏ.")
    assert not rejects_premise(None)


def test_exact_match_alias():
    assert exact_match("TP.HCM", ["Thành phố Hồ Chí Minh"]) == 1.0
    assert exact_match("Tỉnh Tuyên Quang", ["Tuyên Quang"]) == 1.0
    assert exact_match("Hà Giang", ["Tuyên Quang"]) == 0.0
    assert exact_match(None, None) == 0.0


def test_token_f1():
    assert token_f1("lâm đồng", "lâm đồng") == 1.0
    assert token_f1("abc", "xyz") == 0.0
    assert 0 < token_f1("lâm đồng đắk nông", "lâm đồng") < 1
    assert token_f1(None, "") == 1.0


def test_set_f1():
    assert set_f1(["Lâm Đồng", "Đắk Nông", "Bình Thuận"], ["lâm đồng", "đắk nông", "bình thuận"]) == 1.0
    assert set_f1([], []) == 1.0
    assert set_f1(["Lâm Đồng"], []) == 0.0
    assert set_f1(["Lâm Đồng"], ["Lâm Đồng", "Đắk Nông"]) == pytest.approx(2 / 3)
    assert set_f1(None, None) == 1.0


def test_spec_worked_example_f1_a02():
    assert answer_set_f1("Lâm Đồng và Đắk Nông", BENCH["P-V-A02"]) == pytest.approx(0.8)
    assert answer_match("Lâm Đồng và Đắk Nông", BENCH["P-V-A02"]) is False


def test_staleness_rate():
    assert staleness_rate([True, False, True, False]) == 0.5
    assert staleness_rate([]) == 0.0


def test_kor():
    assert knowledge_override_rate([True, True, False], [True, False, True]) == 0.5
    assert knowledge_override_rate([False], [True]) == 0.0
    with pytest.raises(ValueError):
        knowledge_override_rate([True], [True, False])


def test_pber():
    assert prior_bias_error_rate([True, True, False], [True, False, True]) == 0.5
    assert prior_bias_error_rate([], []) == 0.0


def test_recall_mrr():
    gold = [{"a"}, {"b"}]
    ret = [["x", "a", "y"], ["b", "z"]]
    assert recall_at_k(gold, ret, 1) == 0.5
    assert recall_at_k(gold, ret, 2) == 1.0
    assert mrr(gold, ret) == pytest.approx((0.5 + 1.0) / 2)
    assert mrr(gold, ret, k=1) == pytest.approx(0.5)
    assert recall_at_k([], [], 5) == 0.0 and mrr([], []) == 0.0
    assert recall_at_k([{"a"}], [None], 5) == 0.0


@pytest.mark.parametrize("text,expected", [
    ("Có 34 tỉnh và 3.321 xã", ["34", "3321"]),
    ("Từ ngày 01/07/2025, còn 34", ["34"]),
    ("", []),
])
def test_extract_numbers(text, expected):
    assert extract_numbers(text) == expected


def test_yes_no_and_entities():
    assert yes_no_polarity("Không. Thanh Hóa giữ nguyên.") is False
    assert yes_no_polarity("Có, giáp biển.") is True
    assert yes_no_polarity("Thanh Hóa giữ nguyên.") is None
    assert extract_entities("Bà Rịa - Vũng Tàu và Vũng Tàu", ["Vũng Tàu", "Bà Rịa – Vũng Tàu"]) == {
        "bà rịa – vũng tàu", "vũng tàu"}


@pytest.mark.parametrize("qid,output,expected", [
    ("P-V-C03", "Phố cổ Hội An hiện thuộc thành phố Đà Nẵng.", "CORRECT_CURRENT"),
    ("P-V-C03", "Phố cổ Hội An thuộc tỉnh Quảng Nam.", "STALE"),
    ("P-V-C03", "Hội An thuộc tỉnh Quảng Ngãi.", "OTHER_ERROR"),
    ("P-V-C03", "Xin lỗi, tôi không có thông tin.", "ABSTAIN"),
    ("P-V-C03", "Hội An thuộc TP Đà Nẵng, tỉnh Quảng Nam.", NEEDS_JUDGE),
    ("P-V-A01", "Hiện nay có 34 đơn vị hành chính cấp tỉnh.", "CORRECT_CURRENT"),
    ("P-V-A01", "Việt Nam có 63 tỉnh, thành phố.", "STALE"),
    ("P-V-B01", "Từ 01/07/2025 không còn huyện Gia Lâm.", "CORRECT_CURRENT"),
    ("P-V-B07", "Quảng Ninh giáp Trung Quốc.", "CORRECT_CURRENT"),
    ("P-V-B07", "Quảng Ninh đã sáp nhập nên không còn tồn tại.", "OTHER_ERROR"),
    ("P-V-A06", "Không, Thanh Hóa không hợp nhất.", "CORRECT_CURRENT"),
])
def test_auto_label(qid, output, expected):
    assert auto_label(output, BENCH[qid]) == expected


def test_ratio_and_bootstrap():
    assert Ratio(0, 0).value is None
    assert Ratio(3, 4).as_dict()["value"] == 0.75
    lo, hi = bootstrap_ci([1.0, 0.0, 1.0, 0.0], n_boot=200, seed=1)
    assert 0.0 <= lo <= 0.5 <= hi <= 1.0
    assert bootstrap_ci([], n_boot=100) is None
    assert bootstrap_ci([1.0, 1.0], n_boot=50) == (1.0, 1.0)


def test_statistical_tests():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 2 ** 10)
    assert mcnemar_exact(3, 3) == 1.0
    assert holm_bonferroni([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm_bonferroni([]) == []
    res = paired_bootstrap([1, 1, 1, 0], [0, 0, 1, 0], n_boot=200)
    assert res["diff"] == pytest.approx(0.5) and res["ci_lo"] <= 0.5 <= res["ci_hi"]
    assert paired_bootstrap([], []) is None
    with pytest.raises(ValueError):
        paired_bootstrap([1], [])


def test_cohen_kappa():
    assert cohen_kappa(["STALE", "CORRECT_CURRENT"], ["STALE", "CORRECT_CURRENT"]) == 1.0
    assert cohen_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"]) == pytest.approx(0.0)
    assert cohen_kappa([], []) is None
    assert cohen_kappa(["A", "A"], ["A", "A"]) == 1.0
    with pytest.raises(ValueError):
        cohen_kappa(["A"], [])


def test_read_jsonl_guards(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert read_jsonl(empty) == []
    assert read_jsonl(tmp_path / "missing.jsonl") == []
    messy = tmp_path / "messy.jsonl"
    messy.write_text('﻿{"a": 1}\n\nnot json\n[1, 2]\n{"b": "Đà Nẵng"}\n', encoding="utf-8")
    warnings: list[str] = []
    assert read_jsonl(messy, warnings.append) == [{"a": 1}, {"b": "Đà Nẵng"}]
    assert len(warnings) == 2


def test_load_predictions_tv2_schema(tmp_path):
    p = tmp_path / "qwen-7b.jsonl"
    rows = [pred("P-V-C03", None, context_ids=None), {"model_id": "m", "output": "x"},
            pred("P-V-A01", "34", context_ids=["NQ-202-2025-QH15#Art1.24", None])]
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    loaded = load_predictions(p)
    assert [r["question_id"] for r in loaded] == ["P-V-C03", "P-V-A01"]
    assert loaded[0]["output"] == "" and loaded[0]["context_ids"] == []
    assert loaded[1]["context_ids"] == ["NQ-202-2025-QH15#Art1.24"]


def test_load_labels_jsonl_and_csv(tmp_path):
    j = tmp_path / "labels.jsonl"
    j.write_text('{"question_id": "P-V-C03", "label": "stale"}\n{"question_id": "P-V-A01", "label": "??"}\n',
                 encoding="utf-8")
    assert load_labels(j) == {"P-V-C03": "STALE"}
    c = tmp_path / "labels.csv"
    c.write_text("question_id,label\nP-V-A01,CORRECT_CURRENT\n", encoding="utf-8")
    assert load_labels(c) == {"P-V-A01": "CORRECT_CURRENT"}


def test_evaluate_end_to_end_metrics():
    preds = [
        pred("P-V-C03", "Phố cổ Hội An thuộc tỉnh Quảng Nam.", context_ids=["NQ-202-2025-QH15#Art1.10"]),
        pred("P-V-A02", "Lâm Đồng và Đắk Nông", context_ids=["x", "y", "NQ-202-2025-QH15#Art1.14"]),
        pred("P-V-A01", "Hiện có 34 tỉnh, thành phố.", context_ids=["z"]),
        pred("P-V-B01", "Hội An", label="BLENDED"),
        pred("P-V-B07", "Quảng Ninh đã sáp nhập, không còn tồn tại."),
        pred("P-X-999", "ngoài benchmark"),
    ]
    r = evaluate(preds, BENCH, labels={"P-V-A02": "OTHER_ERROR"}, k=5, n_boot=0)
    assert r["unknown_question_ids"] == ["P-X-999"]
    assert r["label_sources"] == {"auto": 3, "labels_file": 1, "prediction": 1}
    assert r["SR"]["num"] == 1 and r["SR"]["den"] == 5
    assert r["SR_plus"]["num"] == 2
    assert r["OverRejection"] == {"num": 1, "den": 1, "value": 1.0, "ci95": None}
    assert r["Recall@5"]["num"] == 2 and r["Recall@5"]["den"] == 4
    assert r["MRR@5"]["value"] == pytest.approx((1 + 1 / 3) / 4)
    assert r["PBER"]["num"] == 1 and r["PBER"]["den"] == 2
    assert r["F1_set"]["mean"] == pytest.approx(0.8)
    assert r["by_category"]["C_multihop_spatial"]["SR"]["value"] == 1.0
    assert "P-V-A06" in r["missing_question_ids"]


def test_evaluate_kor_and_oracle():
    c0 = [pred("P-V-C03", "Hội An thuộc tỉnh Quảng Nam.", config="C0"),
          pred("P-V-A01", "Việt Nam có 63 tỉnh.", config="C0")]
    c5 = [pred("P-V-C03", "Hội An hiện thuộc thành phố Đà Nẵng.", config="C5"),
          pred("P-V-A01", "Việt Nam có 63 tỉnh.", config="C5")]
    r = evaluate(c5, BENCH, baseline=c0, n_boot=0)
    assert r["KOR"]["num"] == 1 and r["KOR"]["den"] == 2
    assert r["PBER"]["num"] == 1 and r["PBER"]["den"] == 2
    assert r["Recall@5"]["den"] == 0


def test_evaluate_empty_and_closed_book():
    r = evaluate([], BENCH, n_boot=0)
    assert r["SR"]["value"] is None and r["Recall@5"]["value"] is None
    r0 = evaluate([pred("P-V-C03", "Đà Nẵng", config="C0")], BENCH, n_boot=0)
    assert r0["Recall@5"]["den"] == 0 and r0["PBER"]["den"] == 0


def test_cli(tmp_path, capsys):
    bench = tmp_path / "bench.jsonl"
    bench.write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in BENCH.values()), encoding="utf-8")
    preds = tmp_path / "C1" / "qwen-7b.jsonl"
    preds.parent.mkdir()
    preds.write_text(json.dumps(pred("P-V-C03", "Hội An thuộc tỉnh Quảng Nam."), ensure_ascii=False) + "\n",
                     encoding="utf-8")
    out_json = tmp_path / "res" / "r.json"
    assert main([str(preds), "--bench", str(bench), "--bootstrap", "50", "--json", str(out_json),
                 "--entity-map", str(tmp_path / "none.csv")]) == 0
    printed = capsys.readouterr().out
    assert "SR" in printed and "1/1 = 100.0%" in printed
    assert json.loads(out_json.read_text(encoding="utf-8"))["SR"]["num"] == 1
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    assert main([str(empty), "--bench", str(bench)]) == 2
    assert main([str(tmp_path / "missing.jsonl"), "--bench", str(bench)]) == 2
    assert main([str(preds), "--bench", str(empty)]) == 2


CLAUSE = "Sắp xếp đơn vị hành chính cấp xã là việc thành lập, giải thể, nhập, chia đơn vị hành chính"
GOLD_FIXED = {"NQ-76-2025-UBTVQH15#D1.K3": CLAUSE}


def test_clause_coverage():
    assert clause_coverage(CLAUSE, "Điều 1. " + CLAUSE + " cấp xã.") == 1.0
    half = " ".join(CLAUSE.split()[:8])
    assert clause_coverage(CLAUSE, "đầu đoạn " + half) == pytest.approx(8 / len(CLAUSE.split()))
    assert clause_coverage(unicodedata.normalize("NFD", CLAUSE), CLAUSE.upper()) == 1.0
    assert clause_coverage("", CLAUSE) == 0.0 and clause_coverage(CLAUSE, None) == 0.0


def test_fixed_chunk_hit_rules():
    words = CLAUSE.split()
    assert fixed_chunk_hit("NQ-76-2025-UBTVQH15#fixed0", "abc " + CLAUSE, GOLD_FIXED)
    assert fixed_chunk_hit("NQ-76-2025-UBTVQH15#fixed1", " ".join(words[:10]), GOLD_FIXED)
    assert not fixed_chunk_hit("NQ-76-2025-UBTVQH15#fixed1", " ".join(words[:5]), GOLD_FIXED)
    assert not fixed_chunk_hit("NQ-203-2025-QH15#fixed1", CLAUSE, GOLD_FIXED)
    assert fixed_chunk_hit("NQ-76-2025-UBTVQH15#fixed0", CLAUSE,
                           {"NQ-76-2025-UBTVQH15#D1.K3": ["khác hẳn", CLAUSE]})
    assert not fixed_chunk_hit("NQ-76-2025-UBTVQH15#fixed0", CLAUSE, {})


def test_fixed_hit_rank():
    texts = {"NQ-202-2025-QH15#fixed0": "không liên quan",
             "NQ-76-2025-UBTVQH15#fixed2": CLAUSE}
    ids = ["NQ-202-2025-QH15#fixed0", "missing#fixed9", "NQ-76-2025-UBTVQH15#fixed2"]
    assert fixed_hit_rank(ids, texts, GOLD_FIXED) == 3
    assert fixed_hit_rank(ids, texts, GOLD_FIXED, k=2) is None
    assert fixed_hit_rank([], texts, GOLD_FIXED) is None
