# Định dạng câu hỏi chung – VN-Admin2025-QA (bản nháp v0.1, chờ TV1 + TV3 chốt)

Mỗi câu hỏi là **một dòng JSON** trong `data/benchmark/*.jsonl`, UTF-8 (NFC).
Định dạng này mở rộng `data/benchmark/sample.jsonl`: giữ toàn bộ trường cũ và thêm một vài trường để gộp được bộ pilot của TV1 (50 câu) và TV3 (30 câu).

## Trường bắt buộc

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `id` | str | Mã duy nhất. Pilot: `P-T-<mã gốc>` (bộ TV1), `P-V-<mã gốc>` (bộ TV3). Bộ chính thức: `<nhóm>-<4 số>`, ví dụ `B-0142` |
| `category` | enum | `A_direct` · `B_obsolete_trap` · `C_multihop_spatial` · `D_before_after` · `E_procedure` · `F_rumor` (E, F là nhóm mới trong pilot của TV1, **cần chốt có giữ hay không**) |
| `item_role` | enum | `trap`: câu dễ bị trả lời theo thông tin cũ · `control`: câu đối chứng, đáp án không đổi sau 01/07/2025 |
| `question` | str | Câu hỏi, dán nguyên văn cho chatbot |
| `reference_date` | date | Ngày mà đáp án chuẩn đúng (ISO, ví dụ `2026-11-19`) |
| `gold_answer.text` | str | Đáp án chuẩn |
| `gold_answer.aliases` | list[str] | Từ khoá/cách viết được chấp nhận (dùng cho chấm tự động) |
| `gold_answer.answer_type` | enum | `entity` · `entity_list` · `number` · `date` · `yes_no` · `premise_rejection` · `free_text` |
| `obsolete_answer.text` | str | Câu trả lời lỗi thời điển hình (rỗng nếu là `control`) |
| `obsolete_answer.obsolete_entities` | list[str] | Tên đơn vị cũ/con số cũ. `eval/staleness_rules.py` dò các từ này để gắn nhãn STALE |
| `evidence` | list[obj] | Căn cứ, xem bên dưới. **Bắt buộc ít nhất 1** |
| `verified` | bool | `true` chỉ khi 2 người đã đối chiếu với văn bản gốc |
| `version` | str | `pilot-0.1`, `v1.0`… |

## Trường `evidence[]`

```json
{"doc_id": "NQ-1656-2025-UBTVQH15", "article": "1", "clause": "1",
 "clause_id": "NQ-1656-2025-UBTVQH15#D1.K1",
 "citation": "NQ 1656/NQ-UBTVQH15, Điều 1, khoản 1"}
```

- `clause_id` trùng với `id` của khoản trong `data/parsed/<doc_id>.json`. TV2 dùng trường này làm nhãn đúng khi tính Recall@k.
- Văn bản chưa có trong kho (Luật 72/2025, NQ 190/2025, thông báo của UBND…) thì để `doc_id`/`clause_id` là `null` và chỉ ghi `citation`. Câu loại này **không tính vào Recall@k**.

## Trường tuỳ chọn

`subtype`, `province_new`, `province_is_control`, `hops`, `difficulty` (`easy`/`medium`/`hard`), `annotator` (list mã người), `source_set` (`toan50`/`vinh30`), `source_id` (mã trong file gốc), `source_url`, `verification_note` (ghi chú khi kiểm thấy sai/thiếu), `duplicate_of` (id câu trùng ý).

## Quy ước

- Tên tỉnh viết như cột `new_province` trong `entity_map` (ví dụ `Hồ Chí Minh`, `Huế`, không thêm "TP").
- Câu `control` phải có `province_is_control = true` hoặc hỏi về sự kiện không đổi. Mục tiêu khoảng 20% câu nhóm B là control (`qgen/templates.py`).
- Một câu chỉ thuộc một `category`. Câu vừa tra cứu vừa bẫy thì xếp vào nhóm bẫy.

## Việc cần chốt (TV1 + TV3, thứ Năm 19/11)

1. Có giữ nhóm `E_procedure` và `F_rumor` không, hay gộp vào A/B?
2. Bộ TV1 chưa có `aliases` và `obsolete_entities`. Ai bổ sung?
3. Các câu trùng ý giữa hai bộ (danh sách tự phát hiện ở `data/benchmark/pilot_80_report.md`; trùng ý khác chữ cần người xem) giữ cả hai hay bỏ một?
