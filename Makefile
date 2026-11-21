.PHONY: install test lint qdrant c0 demo

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

qdrant:
	docker compose up -d qdrant

# Closed-book run. Narrow with: make c0 ARGS="--models qwen-7b --limit 30"
c0:
	python -m rag.run_inference --config C0 $(ARGS)

demo:
	streamlit run demo/app.py
