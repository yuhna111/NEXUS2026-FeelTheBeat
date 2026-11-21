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
