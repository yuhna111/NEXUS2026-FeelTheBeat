# Định dạng câu hỏi VN-Admin2025-QA — v1.0

Thay cho bản nháp v0.1 (TV1, nhánh `feat/data`). Áp dụng cho mọi file `data/benchmark/*.jsonl` từ `pilot-0.2` trở đi.
Validator: `python -m eval.qa_schema <file.jsonl> --parsed data/parsed` (test: `tests/test_qa_schema.py`).

- Mỗi dòng là một object JSON, UTF-8, Unicode NFC, xuống dòng `\n`.
- `null` dùng cho trường tuỳ chọn không có giá trị; không bỏ khoá.
- Thay đổi so với v0.1: thêm trường bắt buộc `gold_clause_ids`; `evidence[].in_corpus` thành bắt buộc; `hops` có ràng buộc; ghi rõ cách nối ID với `rag/chunkers.py`.

## 1. Đặc tả trường

| Trường | Kiểu | Bắt buộc | Ràng buộc | Mô tả |
|---|---|---|---|---|
| `id` | str | ✔ | duy nhất trong file | Pilot: `P-T-<mã>` (TV1), `P-V-<mã>` (TV3). Bộ chính thức: `<nhóm>-<4 số>`, ví dụ `B-0142`. TV2 ghi lại thành `question_id` trong `outputs/<config>/*.jsonl` |
| `category` | enum | ✔ | `A_direct` · `B_obsolete_trap` · `C_multihop_spatial` · `D_before_after` · `E_procedure` · `F_rumor` | Mỗi câu một nhóm. Câu vừa tra cứu vừa bẫy xếp vào nhóm bẫy. E, F đang chờ chốt (mục 5) |
| `item_role` | enum | ✔ | `trap` · `control` | `control`: đáp án không đổi sau 01/07/2025 (đối chứng/đối chứng âm) |
| `question` | str | ✔ | không rỗng | Dán nguyên văn cho mô hình; `rag/run_inference.py` đọc trường này |
| `reference_date` | str | ✔ | ISO `YYYY-MM-DD` | Ngày mà đáp án chuẩn đúng; điền vào `{reference_date}` của prompt |
| `gold_answer.text` | str | ✔ | không rỗng | Đáp án chuẩn |
| `gold_answer.aliases` | list[str] | ✔ | có thể rỗng | Từ khoá/cách viết chấp nhận (EM, token-F1) |
| `gold_answer.answer_type` | enum | ✔ | `entity` · `entity_list` · `number` · `date` · `yes_no` · `premise_rejection` · `free_text` | Chọn độ đo: `entity_list` → set-F1; `premise_rejection` → chấm bác bỏ tiền giả định |
| `gold_answer.entities` | list[str] | — | tên tỉnh theo `entity_map` | Thực thể đáp án cho set-F1 |
| `obsolete_answer.text` | str | ✔ | `""` nếu `control` | Câu trả lời lỗi thời điển hình |
| `obsolete_answer.obsolete_entities` | list[str] | ✔ | `[]` nếu `control`; không chứa chú thích trong ngoặc | Chuỗi mà `eval/staleness_rules.py` dò (khớp chuỗi con sau `normalize`) |
| `evidence` | list[obj] | ✔ | ≥ 1 phần tử, xem mục 2 | Mọi căn cứ, kể cả văn bản chưa có trong kho |
| `gold_clause_ids` | list[str] | ✔ | ≥ 1; hoặc toàn ID khoản hợp lệ, hoặc đúng `["TODO_VERIFY_CLAUSE"]` | **Nhãn đúng cho Recall@k/MRR**, xem mục 3 |
| `verified` | bool | ✔ | | `true` chỉ khi 2 người đã đối chiếu văn bản gốc |
| `version` | str | ✔ | | `pilot-0.1`, `pilot-0.2`, `v1.0`… |
| `source_set` | str | — | `toan50` · `vinh30` · … | Bộ gốc |
| `source_id` | str | — | | Mã trong file gốc |
| `subtype` | str \| null | — | | Phân loại con tự do |
| `province_new` | str \| null | — | như cột `new_province` của `entity_map` (không thêm "TP") | `null` nếu câu toàn quốc |
| `province_is_control` | bool \| null | — | | Tỉnh mới thuộc 11 đơn vị không sắp xếp |
| `hops` | int \| null | — | ≥ 1 | Số bước suy luận |
| `difficulty` | enum \| null | — | `easy` · `medium` · `hard` | |
| `annotator` | list[str] | — | | Mã người soạn/gán nhãn |
| `source_url` | str | — | | |
| `verification_note` | str | — | | Ghi chú khi kiểm thấy sai/thiếu căn cứ |
| `duplicate_of` | str | — | `id` có trong bộ gộp | Câu trùng ý ở bộ khác |

## 2. `evidence[]`

| Khoá | Kiểu | Ràng buộc |
|---|---|---|
| `doc_id` | str \| null | trùng `doc_id` trong `data/raw/manifest.csv`; `null` nếu chưa xác định văn bản |
| `article` | str \| null | số Điều, khớp `clause_id` |
| `clause` | str \| null | số khoản, khớp `clause_id` |
| `clause_id` | str \| null | `<doc_id>#D<điều>.K<khoản>`, trùng `id` của khoản trong `data/parsed/<doc_id>.json`; `null` nếu chưa định vị khoản |
| `citation` | str | không rỗng; dạng người đọc, ví dụ `NQ 202/2025/QH15, Điều 1, khoản 14`. Số hiệu chưa dò: thêm `[TODO_VERIFY]` |
| `in_corpus` | bool | `true` ⇔ `clause_id` có trong `data/parsed`; `true` bắt buộc có `clause_id` |

`evidence` được phép chứa khoản chỉ hỗ trợ một phần (ví dụ khoản hợp nhất tỉnh khi câu hỏi hỏi trung tâm hành chính). Khoản đó **không** đưa vào `gold_clause_ids`.

## 3. `gold_clause_ids` và Recall@k

- Chỉ chứa khoản **mang thông tin trả lời**; mỗi phần tử phải xuất hiện trong `evidence[].clause_id` và có trong `data/parsed`.
- Chưa định vị được khoản nào → `["TODO_VERIFY_CLAUSE"]`. Câu này bị **loại khỏi mẫu số** Recall@k/MRR (không tính là trượt).
- Lấy nhãn: `eval.qa_schema.recall_gold_ids(rec)` → `set[str] | None`. Bản ghi `pilot-0.1` (chưa có trường này, ví dụ `pilot_80.jsonl`) được suy ra từ `evidence[]` có `in_corpus = true`.
- Hit: `recall_at_k(gold_ids, retrieved, k)` trong `eval/metrics.py`, với `retrieved` là `context_ids` trong output của TV2.

**Nối ID với TV2.** `rag/chunkers.legal_chunks` đặt `chunk_id = <doc_id>#Art<điều>.<khoản>`, còn `data/parsed` dùng `<doc_id>#D<điều>.K<khoản>`. Hai dạng chuyển qua lại một-một bằng `clause_id_to_chunk_id` / `chunk_id_to_clause_id` (`eval/qa_schema.py`). Chunk `#fixed<i>` (C1) và chunk cấp Điều `#Art<điều>` không có khoản tương ứng → Recall@k của C1 cần quy tắc riêng (mục 5).

## 4. Ví dụ hợp lệ

```json
{"id": "P-V-C05", "source_set": "vinh30", "source_id": "C05", "category": "C_multihop_spatial", "subtype": null, "item_role": "trap", "question": "Tỉnh Quảng Ngãi hiện có chung đường biên giới với những nước nào?", "reference_date": "2026-11-19", "gold_answer": {"text": "Lào và Campuchia, vì tỉnh Kon Tum (giáp Lào và Campuchia) đã hợp nhất vào tỉnh Quảng Ngãi.", "aliases": ["Lào", "Campuchia"], "answer_type": "entity_list", "entities": ["Lào", "Campuchia"]}, "obsolete_answer": {"text": "Không có. Quảng Ngãi là tỉnh duyên hải Nam Trung Bộ, không có biên giới quốc tế.", "obsolete_entities": ["không có biên giới", "duyên hải"]}, "evidence": [{"doc_id": "NQ-202-2025-QH15", "article": "1", "clause": "11", "clause_id": "NQ-202-2025-QH15#D1.K11", "citation": "NQ 202/2025/QH15, Điều 1, khoản 11", "in_corpus": true}], "gold_clause_ids": ["NQ-202-2025-QH15#D1.K11"], "source_url": "", "province_new": "Quảng Ngãi", "province_is_control": false, "hops": 2, "difficulty": null, "annotator": ["TV3"], "verified": false, "verification_note": "Sheet: Cần dò đường biên giới với Campuchia. K11 nêu Quảng Ngãi giáp Lào và Campuchia (giải quyết mục 'cần dò biên giới Campuchia').", "version": "pilot-0.2"}
```

## 5. Quy ước và việc còn mở

- Câu `control`: `obsolete_answer` rỗng. Mục tiêu ~20% câu nhóm B là control (`qgen/templates.py`).
- `obsolete_entities` chỉ chứa chuỗi khớp được; không ghi mô tả ("chỉ nêu…", "(nói như vẫn còn)").
- Không bịa số hiệu, Điều, khoản. Thiếu → `null` + `[TODO_VERIFY]` trong `citation`, hoặc `TODO_VERIFY_CLAUSE` trong `gold_clause_ids`.
- Mở: (1) giữ hay gộp `E_procedure`, `F_rumor` (TV1 + TV3); (2) TV2 chọn: đổi `chunk_id` sang dạng `#D.K` hay dùng hàm nối ID ở mục 3; (3) quy tắc Recall@k cho chunk cố định C1 (đề xuất: hit nếu chunk chứa trọn văn bản một khoản vàng); (4) `scripts/build_pilot_jsonl.py` của TV1 cần sinh thêm `gold_clause_ids`.
