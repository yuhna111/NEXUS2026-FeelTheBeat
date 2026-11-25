# data/

| Thư mục | Nội dung | Người phụ trách |
|---------|----------|-----------------|
| `raw/` | Văn bản pháp lý gốc (NQ 202/2025/QH15, NQ 76/2025/UBTVQH15, Luật Tổ chức CQĐP 2025, 34 NQ cấp xã) + `manifest.csv` (URL, số hiệu, ngày hiệu lực, SHA-256). PDF không commit, chỉ commit Markdown đã chuyển. | TV1 |
| `parsed/` | JSON `{doc_id, …, text, articles[...]}`; `text` là toàn văn, mỗi dòng một "Điều N. …" hoặc "K. …" (đọc thẳng bằng `rag/chunkers.py`). Mỗi khoản có `id` dạng `<doc_id>#D<điều>.K<khoản>` (dùng làm `clause_id` trong benchmark và id chunk). Sinh bằng `python scripts/parse_resolutions.py` | TV1 |
| `processed/` | `entity_map_63_34_v1.csv` (63 dòng, trung tâm hành chính theo NQ 60-NQ/TW), `commune_lineage.csv` (3.321 xã mới, 10.559 dòng; sinh bằng `python scripts/build_lineage.py`), `popularity.csv` | TV1 |
| `benchmark/` | `pilot_80.jsonl` + `pilot_80_report.md` (sinh bằng `python scripts/build_pilot_jsonl.py`), `vn_admin2025_qa_vX.Y.jsonl`, `datasheet.md`, `oracle_contexts.jsonl`, `distractors.jsonl` | TV1 |

Lược đồ bản ghi benchmark: xem `docs/qa_schema.md`.

**Bộ pilot gộp:** `benchmark/pilot_80_v0.2.jsonl` = 50 câu TV1 (`pilot_80.jsonl`, nâng lên v1.0) + 30 câu TV3 (`pilot_30_vinh.jsonl`), định dạng theo `docs/qa_schema.md`. Sinh lại bằng `python scripts/merge_pilot_sets.py --toan data/benchmark/pilot_80.jsonl`; kiểm bằng `python -m eval.qa_schema data/benchmark/pilot_80_v0.2.jsonl`. `gold_clause_ids` của câu TV1 được suy tự động và đánh dấu trong `verification_note`, TV1 cần xác nhận.

**Bộ câu hỏi v0.3 (tuần 3, TV1):** `benchmark/tv1_v0.3.jsonl` = 168 câu mới (A 113, B 43, E 12; 18 câu đối chứng), sinh bằng `python qgen/build_tv1_v03.py --dvhcvn <dvhcvn.json>`. Đáp án và `gold_clause_ids` lấy từ NQ 202, NQ cấp xã, NQ 203, Luật 72, NQ 190; tên huyện cũ trong câu hỏi lấy từ danh mục 01/03/2025 và không dùng làm căn cứ. Nhóm E soạn tay. Tất cả `verified = false`, chờ TV3 kiểm chéo. `benchmark/pilot_80_v0.3.jsonl` = pilot 80 câu, bổ sung khoản căn cứ cho 6 câu TV1 trước để `TODO_VERIFY_CLAUSE` (C01–C03, D01, D03, D06).

**Lưu ý:** số hiệu nghị quyết cấp xã trong ví dụ (NQ 1656) cần TV1 đối chiếu lại với Công báo.

**Văn bản cấp xã:** 34 nghị quyết 1654–1687/NQ-UBTVQH15 nằm trong `raw/` dưới dạng chữ do TV1 chuẩn bị; đây là nguồn duy nhất cho chỉ mục và bằng chứng vàng. Bản OCR nháp tuần 1 (`raw/ocr_draft/`) đã bị xoá vì trùng và kém chính xác hơn. `scripts/fetch_raw.py` vẫn OCR được PDF scan nếu sau này cần thêm văn bản; kết quả OCR phải được soát lại trước khi dùng.

## Văn bản khung trong `raw/` (tuần 2)

| File | Nguồn | Ghi chú |
|---|---|---|
| `NQ-202-2025-QH15.md` | Báo Đại biểu Nhân dân (toàn văn) | |
| `NQ-203-2025-QH15.md` | Báo Đại biểu Nhân dân (toàn văn) | Các điều Hiến pháp được sửa nằm trong khoản của Điều 1 |
| `LUAT-72-2025-QH15.md` | Công báo số 807+808 (PDF, datafiles.chinhphu.vn), chuyển chữ bằng pdf.js | 54 điều |
| `NQ-190-2025-QH15.md` | luatminhkhue.vn (toàn văn) | Bản gốc 19/02/2025, chưa gồm sửa đổi sau đó; nên đối chiếu Công báo |
| `NQ-76-2025-UBTVQH15.md` | xaydungchinhsach.chinhphu.vn (Cổng TTĐT Chính phủ, dẫn Quochoi.vn) | 17 điều, 4 chương |

## Ghi chú về `commune_lineage.csv`

- `new_commune_code` là **mã nội bộ** `<số NQ>-<khoản>` (ví dụ `1656-005`); đơn vị không sắp xếp có mã `<số NQ>-U<nn>`. Đây không phải mã ĐVHC của Tổng cục Thống kê.
- `partial = False` chỉ khi NQ ghi "toàn bộ diện tích tự nhiên, quy mô dân số"; các trường hợp "một phần…", "phần còn lại…" là `True`.
- `old_district` chỉ có khi NQ tự ghi trong ngoặc (để phân biệt trùng tên).
- `old_province` (tuần 3): NQ cấp xã của tỉnh hợp nhất không ghi tỉnh cũ, nên `scripts/fill_old_province.py` đối chiếu tên xã cũ với danh mục ĐVHC ngày 01/03/2025 của Tổng cục Thống kê (qua bộ dữ liệu [dvhcvn](https://github.com/daohoangson/dvhcvn), GPL-3.0, không chép vào repo). Đủ 10.559/10.559 dòng. Cách điền từng dòng ghi trong `processed/commune_lineage_old_province_audit.csv`: 7.061 khớp đúng tên, 146 khớp khi bỏ dấu thanh ("Hoà"/"Hòa"), 6 cấp huyện, 251 suy từ các đơn vị cùng xã mới, 8 ghi tay (tên viết khác giữa NQ và danh mục), 4 theo đa số cùng xã mới vì trùng tên (cần kiểm tay). Chạy lại `build_lineage.py` sẽ xoá cột này; chạy `fill_old_province.py` ngay sau đó.
- Vùng không phải ĐVHC (ví dụ "Trường bắn TB1", "khu vực bãi bồi ven biển") được bỏ qua.
- Script tự đối chiếu với câu tổng kết cuối Điều 1 của từng NQ; cả 34 tỉnh khớp tổng số và số theo loại.
- Văn bản gốc trên web có lỗi chính tả (ví dụ "quy mô dân của", "Sắp xếp bộ diện tích"); `parse_resolutions.py` sửa các lỗi này khi tách khoản. NQ 1656 ghi "thông qua ngày 16 tháng 4 năm 2025": nhiều khả năng là lỗi của trang nguồn (các NQ cấp xã được thông qua ngày 16/6/2025), cần đối chiếu với Công báo.
