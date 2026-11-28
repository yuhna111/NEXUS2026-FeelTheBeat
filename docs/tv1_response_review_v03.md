# TV1 sửa bộ `tv1_v0.3.jsonl` theo báo cáo kiểm chéo của TV3

- **Ngày:** 28/11/2026 · **Báo cáo gốc:** `docs/tv3_review_tv1_v03.md` (TV3, 27/11)
- **Cách sửa:** sửa trong `qgen/build_tv1_v03.py` rồi chạy lại (seed không đổi). 153/168 câu giữ nguyên câu hỏi, đáp án và căn cứ; 15 câu đổi nội dung (dưới đây), các câu còn lại chỉ thêm `obsolete_entities`.

## Mục 2: 7 câu cần sửa

| ID | Đã sửa |
|---|---|
| B-0039, B-0041, B-0043 | Ghi kèm huyện cũ đúng như NQ ghi trong ngoặc (Đăk Glei; Minh Hóa, Quảng Bình cũ; Định Quán). Quảng Trị chỉ có 1 xã giữ nguyên nên không đổi xã được. Bộ sinh tự kiểm trùng tên trong tỉnh mới |
| A-0091, A-0112 | Thêm "phần còn lại của" theo nguyên văn khoản; bộ sinh đọc khoản để chọn "phần còn lại của" hay "một phần" |
| A-0101 | Hỏi "đặc khu, xã, phường nào" khi đơn vị mới là đặc khu |
| E-0012 | Thêm `NQ-190-2025-QH15#D15.K3`; thêm `aliases` ngày 28/02/2027 |

## Mục 3: văn phong và hỗ trợ chấm tự động

- B-0029: bỏ dấu cách thừa (chuẩn hoá tên huyện lấy từ dvhcvn).
- 7 câu "cũ trước đây": bỏ "trước đây" khi đã có "cũ".
- `obsolete_entities` (73 câu): A-0001..A-0018 tên tỉnh cũ; A-0019..A-0037 các cụm "không sáp nhập", "không hợp nhất", "giữ nguyên", "không được hình thành từ"; A-0047..A-0079 "thị trấn" (không còn thị trấn từ 01/07/2025); E-0004, E-0005, E-0010 "UBND huyện". 9 câu E còn lại để giám khảo chấm vì câu trả lời lỗi thời không gắn với tên đơn vị.
- Đáp án lỗi thời cho E-0007, E-0008, E-0012.

## Kiểm tra

- `eval.qa_schema`: 168/168 hợp lệ, có khoản vàng. Toàn bộ test đạt.
- Chạy `auto_label` trên đáp án vàng: không câu nào bị chấm `STALE` (159 `CORRECT_CURRENT`, 9 chờ giám khảo, như trước).
- Chạy lại `auto_label` trên đầu ra C0 có sẵn của TV2 (`outputs/tv1_v0.3/C0/`): `STALE` tăng từ 37 lên 71 (Gemini) và 37 lên 69 (Qwen); TV1 đã đọc từng câu chuyển nhãn, đều là câu trả lời lỗi thời (ví dụ khẳng định tỉnh cũ vẫn là tỉnh riêng, hoặc nêu số xã kèm thị trấn). Số liệu trong `results/w3_eval/` cần TV3 chấm lại.

Đề nghị TV3 xem lại 15 câu đổi nội dung, đặt `verified = true` và gộp `benchmark_v0.3.jsonl`.
