# Nhật ký nghiên cứu hằng tuần

Mỗi tuần đúng 5 trường: **Đã làm gì · Kết quả · Khó khăn · Kế hoạch tuần tới · Số giờ làm việc**. Ô `[số]` điền số liệu thực tế trước khi nộp.

## Tuần 1 (09/11 – 15/11/2026)
**Đã làm gì**
- TV1: [điền]
- TV2: Rà soát và sửa bộ khung repo (CI về `.github/workflows`, nới ràng buộc Python, thêm Makefile, sửa prompt LLM-as-a-Judge lỗi định dạng). Hoàn thiện `rag/run_inference.py` (bắt buộc ghim snapshot, chạy tiếp thay vì ghi đè, hỗ trợ tập con câu hỏi). Viết 5 unit test cho `rag/llm_client.py` (lưu đệm JSONL, thử lại khi lỗi). Thêm Qdrant nhúng (`rag/vector_store.py`) cho máy không có Docker. Viết `scripts/fetch_raw.py` (tải PDF theo manifest, kiểm SHA-256, chuyển Markdown, OCR khi là PDF scan). Chạy thử BGE-M3 trên 10 nghị quyết cấp xã với 2 cách chia đoạn (`notebooks/01_embedding_trial.ipynb`). Soạn notebook chạy thử vLLM 7B cho Colab/Kaggle.
- TV3: [điền]

**Kết quả**
- TV1: [điền]
- TV2: Bộ kiểm thử 33 đạt, 4 bỏ qua (chờ bảng truy vết xã). Trên 10 nghị quyết (38.212 từ, bản OCR): 87 đoạn cố định 512/64 và 780 đoạn theo Điều/Khoản. BGE-M3 trên GTX 1660 Ti 6 GB (fp16): 85,2 giây cho 87 đoạn cố định, 102,2 giây cho 780 đoạn Điều/Khoản, VRAM đỉnh 1,2 GB, không đoạn nào bị cắt ở 1.024 token. Truy vấn thử 6 câu: cả hai cách chia đoạn đều có văn bản đúng trong top-3 (6/6). Đây là kiểm tra hạ tầng, không phải số liệu cho bài báo.
- TV3: [điền]

**Khó khăn**
- TV1: [điền]
- TV2: Nghị quyết cấp xã trên Cổng văn bản Chính phủ là PDF scan, OCR còn lỗi dấu và mất dấu chấm sau số Khoản (đã chuyển sang dùng bản chữ của TV1 từ tuần 2). Máy cá nhân không có Docker/WSL nên dùng Qdrant nhúng. vLLM không chạy trên Windows, GPU 6 GB không đủ cho mô hình 7B nên chưa chạy thử vLLM. Chưa có API key mô hình đóng; chưa chốt snapshot và cutoff trong `configs/models.yaml`.
- TV3: [điền]

**Kế hoạch tuần tới**
- TV1: [điền]
- TV2: Chạy notebook vLLM 7B (AWQ 4-bit) trên Colab/Kaggle, ghi VRAM và tốc độ sinh. Tạo API key, gọi thử 3 mô hình đóng, điền snapshot và cutoff. Hoàn thiện `rag/index_build.py` với 2 collection Qdrant chính thức trên kho văn bản chữ đầy đủ, thêm ChromaDB dự phòng. Cài BM25 (rank_bm25 + underthesea) và chạy thử truy xuất trên 50 câu mẫu. Thống nhất với TV1 cách khớp bằng chứng vàng với mã chunk.
- TV3: [điền]

**Số giờ làm việc**
- TV1: [số] giờ · TV2: [số] giờ · TV3: [số] giờ

## Tuần 2 (16/11 – 22/11/2026)
**Đã làm gì**
- TV1: [điền]
- TV2: Kéo main về nhánh của TV2, xoá bản OCR nháp, gộp 50 câu TV1 + 30 câu TV3 thành `data/benchmark/pilot_80_v0.2.jsonl` theo `docs/qa_schema.md` v1.0 (PR #5). Đổi mã đoạn của `rag/chunkers.legal_chunks` sang dạng mã khoản `<doc_id>#D<điều>.K<khoản>` để khớp trực tiếp với bộ câu hỏi. Hoàn thiện `rag/index_build.py` (BGE-M3 → Qdrant, dựng lại từ đầu mỗi lần chạy) và dựng 2 collection `vnadmin_fixed`, `vnadmin_legal` trên 38 văn bản dạng chữ. Viết `rag/retriever.py`: BM25 (rank_bm25 + underthesea, từ điển địa danh lấy từ `commune_lineage.csv` và `entity_map_63_34_v1.csv`), dense (BGE-M3 + Qdrant), kết hợp (RRF, k = 60, 20 ứng viên mỗi bên). Viết `rag/eval_retrieval.py` tính Recall@5 và MRR@5, lưu log truy xuất top-20 từng câu vào `outputs/retrieval_w2/` để TV3 kiểm chéo.
- TV3: [điền]

**Kết quả**
- TV1: [điền]
- TV2: Chia đoạn trên 38 văn bản: 398 đoạn cố định (512/64, trung bình 491 từ, 594 token) và 3.825 đoạn theo Điều–Khoản (trung bình 59 từ, 72 token), không đoạn nào bị cắt ở 1.024 token. Nhúng BGE-M3 trên GTX 1660 Ti 6 GB: 275 giây cho đoạn cố định, 397 giây cho đoạn Điều–Khoản, VRAM đỉnh 1,5 GB. Recall@5 trên 55 câu có khoản nguồn trong kho (`pilot_80_v0.2`):

  | Truy xuất | Chia cố định | Chia theo Điều–Khoản |
  |---|---|---|
  | BM25 | 0,455 (25/55) | 0,582 (32/55) |
  | Vector (BGE-M3) | 0,545 (30/55) | **0,800 (44/55)** |
  | Kết hợp (RRF) | 0,691 (38/55) | 0,764 (42/55) |

  Trên 33 câu theo cách đếm của TV1 (`pilot_80.jsonl`, evidence `in_corpus`): vector và kết hợp theo Điều–Khoản cùng đạt 0,879 (29/33). Cột Điều–Khoản khớp với `eval.metrics.recall_at_k` của TV3. Chia theo Điều–Khoản tốt hơn chia cố định ở cả 3 cách truy xuất; RRF chưa có reranker làm giảm nhẹ so với vector đơn thuần ở cách chia Điều–Khoản. Số liệu pilot, 80 câu chưa được kiểm (`verified = false`). Bảng đầy đủ: `results/retrieval_w2/recall.md`.
- TV2 (vLLM): `notebooks/02_vllm_smoke_colab.ipynb` chạy được trên Colab, GPU Tesla T4 15 GB, mô hình `Qwen/Qwen2.5-7B-Instruct-AWQ` (4-bit), `max-model-len` 4096, `gpu-memory-utilization` 0,90. Khởi động máy chủ 310 giây (gồm tải mô hình). VRAM khi máy chủ chạy 12.529/15.360 MiB (vLLM giữ trước bộ nhớ cho KV cache theo `gpu-memory-utilization`, không phải lượng mô hình thực dùng). Tốc độ sinh ổn định khoảng 42 token/giây (43,3 và 41,6 token/giây ở câu 2, 3); câu đầu chậm (3,1 token/giây) do khởi động. Gọi lại câu đã hỏi lấy từ bộ đệm JSONL trong 0,000 giây. Cả 3 câu thử ở chế độ không truy xuất đều trả lời theo bản đồ cũ: "63 tỉnh", Lâm Đồng "không phải kết quả hợp nhất", và nêu trụ sở UBND huyện Gia Lâm (bịa địa chỉ). Đây là quan sát định tính, chưa phải số liệu.
- TV2 (API): tạo key Gemini (Google AI Studio), gọi thử qua `rag/llm_client.py` với `gemini-3.5-flash-lite` (bậc rẻ nhất; phiên bản 3.5-flash-lite-07-2026), khoảng 2–4 giây/câu, bộ đệm hoạt động. Cùng 3 câu thử, mô hình cũng trả lời theo bản đồ cũ: "63 tỉnh", Lâm Đồng "không sáp nhập tỉnh", và nêu trụ sở UBND huyện Gia Lâm. Sửa lỗi trong `llm_client.py` khiến mọi lượt gọi Gemini thất bại (client bị đóng trước khi gửi yêu cầu); ghi thêm số token và phiên bản mô hình thực trả lời vào bộ đệm.
- TV3: [điền]

**Khó khăn**
- TV1: [điền]
- TV2: `gemini-2.5-flash` không còn mở cho tài khoản mới; tên `gemini-3.5-flash` thực tế do bản 3.6 trả lời, nên không dùng làm mô hình cố định. Google không cho gọi theo mã phiên bản cố định, vì vậy mỗi lượt gọi lưu `model_version` để kiểm tra. Mốc cutoff của Gemini và Qwen chưa điền vì chưa tìm được nguồn công bố chính thức. Chưa có key OpenAI và Anthropic. Quy tắc chấm cho đoạn cố định (đoạn chứa 80 ký tự đầu của khoản đúng) đang tạm theo đề xuất của TV1, cần TV3 chốt (mục mở (3) trong `qa_schema.md`). `data/parsed` có 5 mã khoản lặp (NQ 203 Điều 1 khoản 1–3, Luật 72 Điều 30 khoản 1–2) do văn bản trích lại điều luật khác; đã xử lý khi lưu vào Qdrant, không câu pilot nào dùng các mã này. 25/80 câu chưa có khoản nguồn trong kho (NQ 76 chưa có) nên chưa tính Recall.
- TV3: [điền]

**Kế hoạch tuần tới**
- TV1: [điền]
- TV2: Thêm reranker `bge-reranker-v2-m3` vào cách kết hợp (cấu hình C3) và đo lại Recall@5. Chạy C0 (không truy xuất) trên bộ pilot với các mô hình đã có key. Chạy lại `notebooks/01_embedding_trial.ipynb` trên kho văn bản chữ.
- TV3: [điền]

**Số giờ làm việc**
- TV1: [số] giờ · TV2: [số] giờ · TV3: [số] giờ
