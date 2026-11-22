from eval.normalize import ALIASES_CSV, load_aliases, normalize


def test_aliases_csv_loaded():
    assert ALIASES_CSV.is_file()
    assert normalize("TP.HCM") == normalize("Thành phố Hồ Chí Minh") == "hồ chí minh"
    assert normalize("Dak Nong") == normalize("Đắc Nông") == "đắk nông"
    assert normalize("Ba Ria - Vung Tau") == normalize("Bà Rịa – Vũng Tàu")


def test_thua_thien_hue_not_merged_into_hue():
    assert normalize("Tp. Huế") == "huế"
    assert normalize("Thừa Thiên Huế") != "huế"


def test_load_aliases_edge_cases(tmp_path):
    assert load_aliases(tmp_path / "missing.csv") == {}
    p = tmp_path / "a.csv"
    p.write_text("alias,canonical,source\nTP. X,Tỉnh Y,t\n,Z,t\nW,,t\n", encoding="utf-8")
    assert load_aliases(p) == {"x": "y"}
