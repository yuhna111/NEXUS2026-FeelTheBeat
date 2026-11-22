.PHONY: install test lint qdrant index recall c0 demo

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

qdrant:
	docker compose up -d qdrant

# Week 2: BGE-M3 indexes from data/parsed (rebuilt from scratch), then Recall@5 table
index:
	python -m rag.index_build --chunker fixed --collection vnadmin_fixed
	python -m rag.index_build --chunker legal --collection vnadmin_legal

recall:
	python -m rag.eval_retrieval

# Closed-book run. Narrow with: make c0 ARGS="--models qwen-7b --limit 30"
c0:
	python -m rag.run_inference --config C0 $(ARGS)

demo:
	streamlit run demo/app.py
