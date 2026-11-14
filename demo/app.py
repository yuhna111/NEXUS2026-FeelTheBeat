"""Side-by-side demo: closed-book (C0) vs full RAG (C4). Reads cached outputs only.

    streamlit run demo/app.py
"""
import json
from pathlib import Path

import streamlit as st

OUT = Path("outputs")


@st.cache_data
def load(config: str, model: str) -> dict[str, dict]:
    p = OUT / config / f"{model}.jsonl"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8") as f:
        return {r["question_id"]: r for r in map(json.loads, f)}


st.set_page_config(page_title="VN-Admin2025 – Closed-book vs RAG", layout="wide")
st.title("VN-Admin2025: LLM có còn dùng bản đồ hành chính cũ?")

models = sorted({p.stem for p in OUT.glob("C0/*.jsonl")})
if not models:
    st.info("Chưa có đầu ra trong outputs/C0 — chạy `make c0` trước.")
    st.stop()

model = st.selectbox("Mô hình", models)
left, right = load("C0", model), load("C4", model)
qid = st.selectbox("Câu hỏi", sorted(left))

col1, col2 = st.columns(2)
with col1:
    st.subheader("C0 · Closed-book")
    st.write(left.get(qid, {}).get("output", "—"))
with col2:
    st.subheader("C4 · Hybrid RAG + prompt thời gian")
    st.write(right.get(qid, {}).get("output", "—"))
