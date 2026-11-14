import pytest

from eval.metrics import (
    exact_match, knowledge_override_rate, mrr, prior_bias_error_rate,
    recall_at_k, set_f1, staleness_rate, token_f1,
)
from eval.normalize import normalize


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
    import unicodedata
    assert normalize(unicodedata.normalize("NFD", "Lâm Đồng")) == "lâm đồng"


def test_exact_match_alias():
    assert exact_match("TP.HCM", ["Thành phố Hồ Chí Minh"]) == 1.0
    assert exact_match("Tỉnh Tuyên Quang", ["Tuyên Quang"]) == 1.0
    assert exact_match("Hà Giang", ["Tuyên Quang"]) == 0.0


def test_token_f1():
    assert token_f1("lâm đồng", "lâm đồng") == 1.0
    assert token_f1("abc", "xyz") == 0.0
    assert 0 < token_f1("lâm đồng đắk nông", "lâm đồng") < 1


def test_set_f1():
    assert set_f1(["Lâm Đồng", "Đắk Nông", "Bình Thuận"], ["lâm đồng", "đắk nông", "bình thuận"]) == 1.0
    assert set_f1([], []) == 1.0
    assert set_f1(["Lâm Đồng"], []) == 0.0
    assert set_f1(["Lâm Đồng"], ["Lâm Đồng", "Đắk Nông"]) == pytest.approx(2 / 3)


def test_staleness_rate():
    assert staleness_rate([True, False, True, False]) == 0.5
    assert staleness_rate([]) == 0.0


def test_kor():
    assert knowledge_override_rate([True, True, False], [True, False, True]) == 0.5
    assert knowledge_override_rate([False], [True]) == 0.0


def test_pber():
    assert prior_bias_error_rate([True, True, False], [True, False, True]) == 0.5


def test_recall_mrr():
    gold = [{"a"}, {"b"}]
    ret = [["x", "a", "y"], ["b", "z"]]
    assert recall_at_k(gold, ret, 1) == 0.5
    assert recall_at_k(gold, ret, 2) == 1.0
    assert mrr(gold, ret) == pytest.approx((0.5 + 1.0) / 2)
