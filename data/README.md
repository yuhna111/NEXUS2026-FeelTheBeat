# data/

| Thư mục | Nội dung | Người phụ trách |
|---------|----------|-----------------|
| `raw/` | Văn bản pháp lý gốc (NQ 202/2025/QH15, NQ 76/2025/UBTVQH15, Luật Tổ chức CQĐP 2025, 34 NQ cấp xã) + `manifest.csv` (URL, số hiệu, ngày hiệu lực, SHA-256). PDF không commit, chỉ commit Markdown đã chuyển. | TV1 |
| `parsed/` | JSON theo Chương–Điều–Khoản–Điểm, mỗi file `{doc_id, text, articles[...]}` | TV1 |
| `processed/` | `entity_map_63_34.csv` (63 dòng), `commune_lineage.csv` (3.321 xã mới), `popularity.csv` | TV1 |
| `benchmark/` | `vn_admin2025_qa_vX.Y.jsonl`, `datasheet.md`, `oracle_contexts.jsonl`, `distractors.jsonl` | TV1 |

Lược đồ bản ghi benchmark: xem `benchmark/sample.jsonl` và plan §1.2.

**Lưu ý:** số hiệu nghị quyết cấp xã trong ví dụ (NQ 1656) cần TV1 đối chiếu lại với Công báo.
