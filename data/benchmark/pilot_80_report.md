# Báo cáo gộp bộ pilot (tự sinh bởi scripts/build_pilot_jsonl.py)

- Tổng: **80 câu** (toan50: 50, vinh30: 30)
- Theo nhóm: A_direct 39, B_obsolete_trap 16, C_multihop_spatial 7, D_before_after 7, E_procedure 6, F_rumor 5
- Câu `control`: 3
- Câu có căn cứ là khoản **đã có trong kho** `data/parsed/` (dùng được cho Recall@k): **14** — P-T-B02, P-T-B04, P-T-B05, P-T-B06, P-T-B07, P-T-B08, P-T-C05, P-T-C06, P-T-C07, P-T-E01, P-T-E07, P-V-B04, P-V-B08, P-V-C07
- Câu viện dẫn NQ 202/2025/QH15: có `clause_id` nhưng văn bản chưa vào kho (TV1 bổ sung tuần 2).
- Câu đã kiểm (`verified=true`): 0

## Câu gần như trùng chữ giữa hai bộ (độ giống ≥ 0,85)

Câu trùng ý nhưng khác chữ (ví dụ cùng hỏi số tỉnh) cần người xem lại.

| Câu TV3 | Gần giống câu TV1 | Độ giống |
|---|---|---|
| P-V-B08 | P-T-C07 | 0.87 |
| P-V-C07 | P-T-C06 | 1.0 |

## Ghi chú kiểm tra

- **P-T-B04**: Sheet ghi khoản 43 là sai: phường Hoàn Kiếm ở khoản 1. NQ không nêu phường giáp ranh → phần 'giáp với' chưa có căn cứ.
- **P-T-B05**: NQ không ghi tên huyện cũ; việc 3 xã này thuộc huyện Đắk R'lấp cũ cần nguồn khác.

## Còn thiếu

- Bộ TV1 chưa có `aliases`, `obsolete_entities`, `province_new`.
- Bộ TV1 chưa có câu `control`.
- Toàn bộ 80 câu `verified=false`: cần 2 người đối chiếu văn bản gốc.
