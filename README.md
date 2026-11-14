# NEXUS2026 – Feel The Beat · VN-Admin2025

> Đo mức độ **lỗi thời (staleness)** của LLM khi trả lời câu hỏi về đơn vị hành chính Việt Nam sau cải cách 01/07/2025 (63 → 34 tỉnh, bỏ cấp huyện), và mức độ **RAG** khắc phục được.

Sản phẩm của đề tài:

- **`VN-Admin2025-QA`**: benchmark 1.200 câu hỏi đã kiểm chứng (4 nhóm A/B/C/D)
- **Pipeline RAG tái lập được**: BM25 + BGE-M3 + reranker, chia đoạn theo cấu trúc pháp lý
- **Bộ độ đo** tách *lỗi thời* khỏi *sai thông thường*: EM, F1, SR, KOR, PBER, Blending, Over-rejection
- **Bài báo** (IMRaD) và **demo** so sánh closed-book với RAG

## Câu hỏi nghiên cứu

| RQ | Nội dung |
|----|----------|
| RQ1 | Ở closed-book, LLM trả lời theo bản đồ cũ với tần suất bao nhiêu, phụ thuộc họ mô hình / kích thước / cutoff ra sao? |
| RQ2 | Cấu hình RAG nào ghi đè tri thức tham số tốt nhất; chia đoạn theo Điều/Khoản có hơn chunk cố định? |
| RQ3 | Có ngữ cảnh đúng (oracle), mô hình còn trả lời theo trí nhớ / trộn cũ–mới bao nhiêu? |

## Cấu trúc repo

```
data/
  raw/            # văn bản pháp lý gốc (PDF/MD) + manifest.csv
  parsed/         # JSON theo Chương–Điều–Khoản–Điểm
  processed/      # entity_map_63_34.csv, commune_lineage.csv, popularity.csv
  benchmark/      # vn_admin2025_qa_vX.Y.jsonl, datasheet.md
qgen/             # sinh câu hỏi từ template
rag/              # llm_client, chunkers, index_build, retriever, run_inference
eval/             # normalize, metrics, staleness_rules, judge
configs/          # models.yaml, retrieval.yaml (C0–C6), prompts
outputs/          # đầu ra thô của mô hình (JSONL, theo cấu hình C0..C6)
results/          # bảng kết quả CSV
figures/          # biểu đồ cho bài báo
notebooks/        # phân tích
paper/            # bài báo, related work
demo/             # Streamlit demo (đọc kết quả lưu đệm)
docs/             # hướng dẫn gán nhãn, nhật ký nghiên cứu
release/          # dataset card, gói tái lập
tests/            # PyTest
```

## Ma trận cấu hình

| Mã | Cấu hình | Truy xuất | Chia đoạn | Reranker | Prompt |
|----|----------|-----------|-----------|----------|--------|
| C0 | Closed-book | – | – | – | trung tính |
| C1 | Naive RAG | Dense BGE-M3 top-5 | cố định 512/64 | – | dùng ngữ cảnh |
| C2 | Naive RAG (cấu trúc) | Dense BGE-M3 top-5 | Điều/Khoản | – | như C1 |
| C3 | Hybrid RAG | BM25 + dense, RRF top-20 | Điều/Khoản | bge-reranker-v2-m3 → top-5 | như C1 |
| C4 | Đầy đủ | như C3 | Điều/Khoản | như C3 | **prompt thời gian** |
| C5 | Oracle | chèn bằng chứng vàng | – | – | prompt thời gian |
| C6 | *(T7)* C4 + tài liệu gây nhiễu | | | | |

## Cài đặt

Yêu cầu: Python ≥ 3.11 (CI và môi trường chuẩn của nhóm dùng 3.11), Docker.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |  Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"            # lõi + test
pip install -e ".[rag]"            # FlagEmbedding, qdrant-client, rank-bm25, underthesea
pip install -e ".[ocr]"            # easyocr, cho PDF scan
pip install -e ".[demo]"           # streamlit

cp .env.example .env               # điền API key
docker compose up -d qdrant        # Qdrant tại http://localhost:6333
python scripts/fetch_raw.py        # tải PDF theo data/raw/manifest.csv, chuyển sang Markdown
pytest
```

- **GPU:** `pip` mặc định cài PyTorch bản CPU trên Windows. Có GPU NVIDIA thì cài trước: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`.
- **Không có Docker:** đặt `QDRANT_PATH=qdrant_storage/local` trong `.env` để dùng Qdrant dạng nhúng (`rag/vector_store.py`).
- **Thử client LLM:** `python -m rag.llm_client --provider vllm --model <mã> "Câu hỏi"`.
- **Notebook Tuần 1:** `notebooks/01_embedding_trial.ipynb` (BGE-M3 trên 10 văn bản), `notebooks/02_vllm_smoke_colab.ipynb` (vLLM 7B, chạy trên Colab/Kaggle).

vLLM (cho mô hình mở) cài riêng trên máy có GPU: `pip install -e ".[vllm]"`.

## Quy tắc làm việc

- Mọi đầu ra mô hình lưu JSONL trong `outputs/` → **không con số nào trong bài báo phải gọi lại API**.
- Sản phẩm có tag phiên bản theo ngày, ví dụ `v1.0-2026-12-02`, `final-2026-12-20`.
- Nhánh: `main` luôn chạy được; làm việc trên `feat/<tên>` rồi mở PR, thành viên phản biện chéo review.
- Không commit API key (`.env` đã nằm trong `.gitignore`).

| Thành viên | Vai trò | Thư mục chính |
|------------|---------|---------------|
| TV1 | Kiến trúc dữ liệu & Benchmark | `data/`, `qgen/`, `docs/annotation_guide*` |
| TV2 | Pipeline RAG & LLM | `rag/`, `configs/`, `outputs/`, `demo/` |
| TV3 | Đánh giá, Phân tích & Demo | `eval/`, `results/`, `figures/`, `paper/` |

## Mốc quan trọng

| Ngày | Mốc |
|------|-----|
| 02/12/2026 | Đóng băng benchmark v1.0 (1.200 câu, κ ≥ 0,75) |
| 05/12/2026 | Báo cáo tiến độ giữa kỳ |
| 13/12/2026 | Chạy xong C1–C5 |
| 16/12/2026 | Khóa số liệu |
| 20/12/2026 | **Chung kết** |
| 03/01/2027 | Công bố dataset (CC BY 4.0) + mã nguồn |

## Giấy phép

Bộ dữ liệu `VN-Admin2025-QA`: CC BY 4.0. Giấy phép mã nguồn: *(nhóm chọn, ví dụ MIT)*.
