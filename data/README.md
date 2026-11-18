# data/

| Thư mục | Nội dung | Người phụ trách |
|---------|----------|-----------------|
| `raw/` | Văn bản pháp lý gốc (NQ 202/2025/QH15, NQ 76/2025/UBTVQH15, Luật Tổ chức CQĐP 2025, 34 NQ cấp xã) + `manifest.csv` (URL, số hiệu, ngày hiệu lực, SHA-256). PDF không commit, chỉ commit Markdown đã chuyển. | TV1 |
| `parsed/` | JSON theo Điều–Khoản, mỗi khoản có `id` dạng `<doc_id>#D<điều>.K<khoản>` (dùng làm `clause_id` trong benchmark và id chunk). Sinh bằng `python scripts/parse_resolutions.py` | TV1 |
| `processed/` | `entity_map_63_34_v1.csv` (63 dòng, trung tâm hành chính theo NQ 60-NQ/TW), `commune_lineage.csv` (3.321 xã mới, 10.559 dòng; sinh bằng `python scripts/build_lineage.py`), `popularity.csv` | TV1 |
| `benchmark/` | `pilot_80.jsonl` + `pilot_80_report.md` (sinh bằng `python scripts/build_pilot_jsonl.py`), `vn_admin2025_qa_vX.Y.jsonl`, `datasheet.md`, `oracle_contexts.jsonl`, `distractors.jsonl` | TV1 |

Lược đồ bản ghi benchmark: xem `docs/qa_schema.md`.

**Lưu ý:** số hiệu nghị quyết cấp xã trong ví dụ (NQ 1656) cần TV1 đối chiếu lại với Công báo.

## Ghi chú về `commune_lineage.csv`

- `new_commune_code` là **mã nội bộ** `<số NQ>-<khoản>` (ví dụ `1656-005`); đơn vị không sắp xếp có mã `<số NQ>-U<nn>`. Đây không phải mã ĐVHC của Tổng cục Thống kê.
- `partial = False` chỉ khi NQ ghi "toàn bộ diện tích tự nhiên, quy mô dân số"; các trường hợp "một phần…", "phần còn lại…" là `True`.
- `old_district` chỉ có khi NQ tự ghi trong ngoặc (để phân biệt trùng tên); `old_province` mới điền cho 11 tỉnh không sắp xếp.
- Vùng không phải ĐVHC (ví dụ "Trường bắn TB1", "khu vực bãi bồi ven biển") được bỏ qua.
- Script tự đối chiếu với câu tổng kết cuối Điều 1 của từng NQ; cả 34 tỉnh khớp tổng số và số theo loại.
- Văn bản gốc trên web có lỗi chính tả (ví dụ "quy mô dân của", "Sắp xếp bộ diện tích"); `parse_resolutions.py` sửa các lỗi này khi tách khoản. NQ 1656 ghi "thông qua ngày 16 tháng 4 năm 2025": nhiều khả năng là lỗi của trang nguồn (các NQ cấp xã được thông qua ngày 16/6/2025), cần đối chiếu với Công báo.
