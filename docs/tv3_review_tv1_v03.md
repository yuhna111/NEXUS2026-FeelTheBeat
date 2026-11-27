# Báo cáo kiểm chéo 168 câu `data/benchmark/tv1_v0.3.jsonl` (TV3 → TV1)

- **Người kiểm chéo:** TV3 (Vinh)
- **Ngày kiểm:** 27/11/2026
- **Đối tượng kiểm:** `data/benchmark/tv1_v0.3.jsonl` (168 câu: 113 `A_direct`, 43 `B_obsolete_trap`, 12 `E_procedure`)
- **Nguồn đối chiếu:** toàn bộ 39 văn bản gốc trong `data/parsed/*.json`, `data/processed/entity_map_63_34_v1.csv`, `data/processed/commune_lineage.csv`, `data/processed/commune_lineage_old_province_audit.csv`, và `data/benchmark/pilot_80_v0.3.jsonl`.

## 1. Tổng kết nhanh

- **Schema & mã khoản:** 168/168 câu qua được `eval.qa_schema` và trỏ tới mã khoản hợp lệ trong `data/parsed/`. Không có câu trùng nguyên văn với `pilot_80_v0.3.jsonl` hay `tv3_v0.3.jsonl`.
- **Độ chính xác pháp lý:** **161/168 câu đạt yêu cầu pháp lý** (khớp văn bản gốc).
- **7 câu cần sửa nội dung/căn cứ trước khi đặt `verified = true`** (mục 2): 3 câu đối chứng xã bị mơ hồ do trùng tên trong cùng tỉnh mới, 2 câu thiếu cụm "phần còn lại", 1 câu hỏi "xã, phường" cho đáp án là `đặc khu`, và 1 câu nhóm E thiếu khoản căn cứ cho vế thứ hai.
- **Vấn đề văn phong & hỗ trợ chấm tự động** (mục 3): 1 lỗi gõ thừa dấu cách (`B-0029`), 7 câu lặp chữ `"cũ trước đây"`, và 82 câu `trap` đang để trống `obsolete_entities` (cần bổ sung để `eval/staleness_rules.py` bắt tự động được).

| Nhóm / Tiểu nhóm | Số câu | Đạt pháp lý | Cần sửa trước khi `verified = true` |
|---|---:|---:|---|
| `A_direct` – cấp tỉnh (`A-0001`..`A-0046`) | 46 | 46/46 | 0 |
| `A_direct` – đếm số cấp xã (`A-0047`..`A-0079`) | 33 | 33/33 | 0 *(khớp 100% câu tổng kết NQ & `commune_lineage.csv`)* |
| `A_direct` – tra cứu xã cũ → mới (`A-0080`..`A-0113`) | 34 | 31/34 | 3 (`A-0091`, `A-0101`, `A-0112`) |
| `B_obsolete_trap` – bẫy cấp huyện (`B-0001`..`B-0034`) | 34 | 34/34 | 0 *(nhưng `B-0029` có lỗi 2 dấu cách)* |
| `B_obsolete_trap` – đối chứng xã giữ nguyên (`B-0035`..`B-0043`) | 9 | 6/9 | 3 (`B-0039`, `B-0041`, `B-0043`) |
| `E_procedure` – thủ tục hành chính (`E-0001`..`E-0012`) | 12 | 11/12 | 1 (`E-0012`) |
| **Tổng** | **168** | **161/168** | **7 câu cần sửa nội dung/căn cứ** |

---

## 2. 7 câu cần sửa nội dung / căn cứ trước khi chốt `verified = true`

### 2.1. 3 câu đối chứng nhóm B bị mơ hồ do trùng tên xã trong cùng tỉnh mới (`B-0039`, `B-0041`, `B-0043`)

Cả 3 nghị quyết gốc đều phải mở ngoặc ghi kèm tên huyện cũ để phân biệt 2 xã trùng tên trong cùng tỉnh mới; câu hỏi sinh tự động bỏ phần trong ngoặc nên bị mơ hồ (một xã giữ nguyên, một xã cùng tên lại **bị sáp nhập**):

| ID | Câu hỏi hiện tại | Xung đột trong `data/parsed/` & `commune_lineage.csv` | Đề xuất sửa |
|---|---|---|---|
| **`B-0039`** | *"Sau đợt sắp xếp năm 2025, xã Đăk Long của tỉnh Quảng Ngãi có bị nhập với xã, phường khác không?"* | Quảng Ngãi mới (gồm Kon Tum cũ) có **2 xã Đăk Long**: (1) `xã Đăk Long (huyện Đăk Glei)` giữ nguyên (`NQ-1677#D1.K92`); (2) `xã Đăk Long (huyện Đăk Hà)` **nhập** thành xã Đăk Pxi (`NQ-1677#D1.K52`). | Ghi rõ: *"xã Đăk Long (thuộc huyện Đăk Glei, tỉnh Kon Tum cũ)"*, hoặc đổi sang xã không trùng tên trong K92 (ví dụ `xã Ba Xa`, `xã Rờ Kơi`). |
| **`B-0041`** | *"Xã Tân Thành (tỉnh Quảng Trị) có thuộc diện sắp xếp đơn vị hành chính cấp xã năm 2025 không?"* | Quảng Trị mới có **2 xã Tân Thành**: (1) `xã Tân Thành (huyện Minh Hóa, Quảng Bình cũ)` giữ nguyên (`NQ-1680#D1.K78`); (2) `xã Tân Thành (huyện Hướng Hóa, Quảng Trị cũ)` **nhập** thành xã Lao Bảo (`NQ-1680#D1.K56`). Câu hỏi hiện tại dễ bị hiểu là xã Tân Thành của Quảng Trị cũ — vốn **có** bị sắp xếp! | Ghi rõ: *"xã Tân Thành (thuộc huyện Minh Hóa, tỉnh Quảng Bình cũ, nay thuộc tỉnh Quảng Trị)"*. |
| **`B-0043`** | *"Xã Thanh Sơn (tỉnh Đồng Nai) có thuộc diện sắp xếp đơn vị hành chính cấp xã năm 2025 không?"* | Đồng Nai có **2 xã Thanh Sơn**: (1) `xã Thanh Sơn (huyện Định Quán)` giữ nguyên (`NQ-1662#D1.K89`); (2) `xã Thanh Sơn` (huyện Tân Phú cũ) **nhập** thành xã Phú Lâm (`NQ-1662#D1.K35`). | Ghi rõ: *"xã Thanh Sơn (huyện Định Quán cũ, tỉnh Đồng Nai)"*, hoặc đổi sang xã không trùng tên trong K89 (ví dụ `phường Phước Tân`, `xã Đak Lua`, `xã Bù Gia Mập`). |

### 2.2. 2 câu tra cứu xã thiếu chi tiết "phần còn lại" trong đáp án (`A-0091`, `A-0112`)

Tên đơn vị mới đúng, nhưng phần liệt kê các xã/phường ghép cùng trong `gold_answer.text` ghi như thể sáp nhập toàn bộ một đơn vị vốn chỉ ghép **phần còn lại**:

- **`A-0091`** (`NQ-1685-2025-UBTVQH15#D1.K4`): Đáp án hiện ghi *"cùng phường Nguyễn Cư Trinh, phường Cầu Kho và phường Cầu Ông Lãnh"*. Nguyên văn khoản 4: *"và **phần còn lại của phường Cầu Ông Lãnh** sau khi sắp xếp theo quy định tại khoản 3 Điều này"*.
- **`A-0112`** (`NQ-1662-2025-UBTVQH15#D1.K25`): Đáp án hiện ghi *"cùng xã Xuân Hòa và xã Xuân Tâm"*. Nguyên văn khoản 25: *"và **phần còn lại của xã Xuân Tâm** sau khi sắp xếp theo quy định tại khoản 21 Điều này"*.

→ **Đề xuất:** Trong `qgen/build_tv1_v03.py` (hàm `gen_commune_lookup`), nếu phần tử trong `others` có `partial == "True"`, thêm tiền tố `"một phần "` / `"phần còn lại của "` vào câu `gold_answer.text`.

### 2.3. 1 câu hỏi "xã, phường nào?" nhưng đáp án là `đặc khu` (`A-0101`)

- **`A-0101`** (`NQ-1679-2025-UBTVQH15#D1.K52`): Câu hỏi hiện là *"Sau ngày 01/07/2025, xã Bản Sen thuộc huyện Vân Đồn, tỉnh Quảng Ninh trước đây nay là **xã, phường nào**?"*, nhưng đáp án là **`đặc khu Vân Đồn`**.
- **Đề xuất:** Sửa câu hỏi thành *"nay là **đơn vị hành chính cấp xã nào**?"* (hoặc *"xã, phường, đặc khu nào?"*) khi `r["new_type"] == "đặc khu"`.

### 2.4. 1 câu nhóm E thiếu khoản căn cứ cho vế thứ 2 (`E-0012`)

- **`E-0012`**: Đáp án ghi *"Đến hết ngày 28/02/2027 (trừ một số quy định), **và Quốc hội có thể xem xét kéo dài nếu cần**."*
- Hiện `evidence` và `gold_clause_ids` mới chỉ dẫn `NQ-190-2025-QH15#D15.K2` (chỉ chứa vế 28/02/2027); vế gia hạn nằm ở **`NQ-190-2025-QH15#D15.K3`**.
- **Đề xuất:** Bổ sung `NQ-190-2025-QH15#D15.K3` vào `evidence` và `gold_clause_ids` của `E-0012`.

---

## 3. Lỗi trình bày & lưu ý cho pipeline đánh giá (`eval/metrics.py`, `eval/staleness_rules.py`)

1. **Lỗi 2 dấu cách liên tiếp (`B-0029`):** `"Huyện  Vũng Liêm"` xuất hiện ở cả `question`, `gold_answer.text`, `obsolete_answer.text` và `obsolete_entities` (do dữ liệu `dvhcvn.json` có thừa dấu cách). Nên chuẩn hóa `re.sub(r"\s+", " ", d)` trong `qgen/build_tv1_v03.py`.
2. **Thừa cụm `"cũ trước đây"` ở 7 câu `A_direct` cấp xã (`A-0084`, `A-0090`, `A-0095`, `A-0098`, `A-0102`, `A-0107`, `A-0110`):** Ví dụ *"tỉnh Sóc Trăng **cũ trước đây** nay là..."* (do mẫu câu thứ 2 có sẵn `"trước đây"` ghép với biến `prov` đã gắn đuôi `" cũ"`). Không sai sự thật nhưng nên gọt cho tự nhiên.
3. **82/150 câu `trap` đang để `obsolete_entities: []`** (toàn bộ 37 câu `A_direct` cấp tỉnh, 33 câu đếm số xã, và 12 câu `E_procedure`):
   - `eval/staleness_rules.py` dựa vào `obsolete_entities` để nhận diện tự động nhãn `STALE`. Khi để `[]`, bộ luật tự động không bắt được `STALE` và phải đẩy sang LLM judge/chấm tay.
   - Đề xuất bổ sung nhanh trong `qgen/build_tv1_v03.py`: với `A_direct` tỉnh cũ → tỉnh mới (`A-0001`..`A-0018`), có thể đưa `[f"tỉnh {o}", "tỉnh riêng"]` vào `obsolete_entities`; với `E-0004`, `E-0005`, `E-0010` có thể thêm `["UBND huyện"]`.
4. **3 câu `E_procedure` (`E-0007`, `E-0008`, `E-0012`) để trống `obsolete_answer.text`**, và 12 câu `E_procedure` + 19 câu `A_direct` `entity_list` để trống `aliases: []` (riêng `entity_list` đã có `entities` dùng cho set-F1 nên không ảnh hưởng nhiều, nhưng `E-0012` có `answer_type = "date"` nên thêm `aliases: ["28/02/2027", "28 tháng 02 năm 2027"]` để chấm EM/F1 chính xác).
5. **Lưu ý đặc biệt với `E-0008` (`NQ-190-2025-QH15#D12.K2`):** NQ 190 ban hành ngày 19/02/2025 nên khoản 2 Điều 12 vẫn còn cụm *"trên Cổng thông tin điện tử của Ủy ban nhân dân cấp huyện"*. TV1 đã lược phần cấp huyện trong `gold_answer.text` là hợp lý; khi chấm RAG (C2–C4), TV3 sẽ ghi chú để không đánh nhầm `STALE` nếu mô hình trích nguyên văn khoản luật kèm lưu ý cấp huyện đã kết thúc từ 01/07/2025.

---

## 4. Kết luận xác nhận (`verified`)

- **161 câu đạt pháp lý** đã được TV3 đối chiếu đầy đủ với `data/parsed/` và `commune_lineage.csv`; sau khi TV1 cập nhật 7 ca ở mục 2 (và lỗi 2 dấu cách ở `B-0029`) trong `qgen/build_tv1_v03.py` + chạy lại, TV3 xác nhận toàn bộ 168 câu đủ điều kiện đặt `verified = true` và gộp cùng `pilot_80_v0.3.jsonl` (80 câu) + `tv3_v0.3.jsonl` (60 câu) thành `data/benchmark/benchmark_v0.3.jsonl` (308 câu).
