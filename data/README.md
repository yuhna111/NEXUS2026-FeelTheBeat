# data/

| Thư mục | Nội dung | Người phụ trách |
|---------|----------|-----------------|
| `raw/` | Văn bản pháp lý gốc (NQ 202/2025/QH15, NQ 76/2025/UBTVQH15, Luật Tổ chức CQĐP 2025, 34 NQ cấp xã) + `manifest.csv` (URL, số hiệu, ngày hiệu lực, SHA-256). PDF không commit, chỉ commit Markdown đã chuyển. | TV1 |
| `parsed/` | JSON theo Chương–Điều–Khoản–Điểm, mỗi file `{doc_id, text, articles[...]}` | TV1 |
| `processed/` | `entity_map_63_34.csv` (63 dòng), `commune_lineage.csv` (3.321 xã mới), `popularity.csv` | TV1 |
| `benchmark/` | `vn_admin2025_qa_vX.Y.jsonl`, `datasheet.md`, `oracle_contexts.jsonl`, `distractors.jsonl`, `subsets/<tên>.txt` (mỗi dòng một question id, ví dụ `stratified_600.txt` cho mô hình API đóng) | TV1 |

Lược đồ bản ghi benchmark: xem `benchmark/sample.jsonl` và plan §1.2.

**Bộ pilot gộp:** `benchmark/pilot_80_v0.2.jsonl` = 50 câu TV1 (`pilot_80.jsonl` trên `feat/data`, nâng lên v1.0) + 30 câu TV3 (`pilot_30_vinh.jsonl`), định dạng theo `docs/qa_schema.md`. Sinh lại bằng `scripts/merge_pilot_sets.py`; kiểm bằng `python -m eval.qa_schema benchmark/pilot_80_v0.2.jsonl`. `gold_clause_ids` của câu TV1 được suy tự động và đánh dấu trong `verification_note`, TV1 cần xác nhận.

**Lưu ý:** số hiệu nghị quyết cấp xã trong ví dụ (NQ 1656) cần TV1 đối chiếu lại với Công báo.

**Văn bản cấp xã:** 34 nghị quyết 1654–1687/NQ-UBTVQH15 nằm trong `raw/` dưới dạng chữ do TV1 chuẩn bị; đây là nguồn duy nhất cho chỉ mục và bằng chứng vàng. Bản OCR nháp tuần 1 (`raw/ocr_draft/`) đã bị xoá vì trùng và kém chính xác hơn. `scripts/fetch_raw.py` vẫn OCR được PDF scan nếu sau này cần thêm văn bản; kết quả OCR phải được soát lại trước khi dùng.
