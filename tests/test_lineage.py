"""Integrity checks for commune_lineage.csv and entity_map (Week 2, TV1).

Skipped until the tables are filled in.
"""
from pathlib import Path

import pandas as pd
import pytest

PROC = Path("data/processed")
LINEAGE = PROC / "commune_lineage.csv"
ENTITY = PROC / "entity_map_63_34_v1.csv"


def _load(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    if df.empty:
        pytest.skip(f"{p.name} not populated yet")
    return df


def test_new_commune_total():
    df = _load(LINEAGE)
    assert df["new_commune_code"].nunique() == 3321


def test_new_commune_types():
    df = _load(LINEAGE).drop_duplicates("new_commune_code")
    counts = df["new_type"].value_counts().to_dict()
    assert counts == {"xã": 2621, "phường": 687, "đặc khu": 13}


def test_each_commune_one_province():
    df = _load(LINEAGE)
    assert (df.groupby("new_commune_code")["new_province"].nunique() == 1).all()


def test_entity_map_shape():
    df = _load(ENTITY)
    assert len(df) == 63
    assert df["new_province"].nunique() == 34
    assert df.loc[df["is_control"], "new_province"].nunique() == 11
