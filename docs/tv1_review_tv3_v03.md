# TV1 kiểm chéo 60 câu `tv3_v0.3.jsonl` (nhóm C, D, F)

- **Ngày:** 28/11/2026 · **Người kiểm:** TV1 (có dùng AI hỗ trợ đối chiếu, sẽ khai báo) · **Bản kiểm:** nhánh `vini`, commit `b336a84` (PR #15)
- **Cách kiểm:** đọc từng câu, đối chiếu đáp án với nguyên văn khoản trong `data/parsed/`; kiểm tự động số liệu (diện tích, dân số) trong đáp án với khoản căn cứ; chạy `auto_label` trên đáp án vàng và đáp án lỗi thời; dò các phường, xã cũ của thành phố trực thuộc tỉnh cũ qua `commune_lineage.csv` và danh mục 01/03/2025; tra web cho văn bản ngoài kho.

## 1. Kết luận

- **55/60 câu đạt về nội dung pháp lý.** 58/58 khoản vàng có trong kho; mọi số diện tích, dân số trong đáp án khớp NQ 202; nhóm D (thể chế) khớp nguyên văn Luật 72, NQ 76, NQ 203.
- **5 câu cần sửa nội dung:** F-0002, F-0001, C-0012, C-0001, C-0004 (mục 2).
- **Lỗi chấm điểm ảnh hưởng số liệu nhóm F** (mục 3): cả 12 đáp án vàng nhóm F bị `auto_label` chấm `OTHER_ERROR`. Cần sửa trước khi dùng số liệu nhóm F trong báo cáo 05/12.
- **6 câu cần sửa `aliases`** (mục 4).

## 2. Câu cần sửa nội dung

| ID | Vấn đề | Đề xuất |
|---|---|---|
| F-0002 | Đáp án nói Bộ Nội vụ khẳng định "không có chủ trương tiếp tục sắp xếp ... đơn vị hành chính cấp xã" (CV 10988, 21/11/2025). Sau đó Công văn 6218/BNV-CQĐP ngày 18/6/2026 giao Vụ Chính quyền địa phương xây dựng báo cáo đánh giá việc tiếp tục nhập **một số** xã, phường ([luatvietnam](https://luatvietnam.vn/tin-van-ban-moi/bo-noi-vu-nghien-cuu-tiep-tuc-nhap-mot-so-xa-phuong-sau-khi-sap-xep-don-vi-hanh-chinh-186-109708-article.html)). Với `reference_date` 11/2026, vế cấp xã của đáp án vàng đã lỗi thời. | Đổi tin đồn sang "sáp nhập 34 tỉnh còn 16 tỉnh" (CV 10988 bác trực tiếp; bài về CV 6218 không nói đến cấp tỉnh), hoặc viết lại đáp án: chưa có chủ trương sáp nhập đại trà, nhưng CV 6218 đang nghiên cứu nhập một số xã, phường. Cần kiểm lại tình trạng mới nhất trước khi chốt. |
| F-0001 | Nghị định 185/2026/NĐ-CP (26/5/2026, quy định tổ chức thôn, tổ dân phố) có thật. **Không tìm thấy** "Thông tư 31/2026/TT-BNV ngày 20/11/2026": tra web chỉ ra Thông tư 31/2026 của Bộ GDĐT và Bộ Y tế; Thông tư BNV gần nhất tìm được là 29/2026/TT-BNV (30/10/2026). | Bỏ Thông tư 31/2026/TT-BNV khỏi đáp án và `evidence`, hoặc ghi nguồn (link văn bản). Giữ NĐ 185/2026. |
| C-0012 | Hồ thủy điện Hòa Bình trải sang cả tỉnh Sơn La (lòng hồ dọc sông Đà), nên "cùng thuộc tỉnh Phú Thọ" không đúng hoàn toàn với hồ (kiến thức nền, TV3 xác nhận lại). | Đổi thành "Nhà máy thủy điện Hòa Bình" (đặt ở TP Hòa Bình cũ). |
| C-0001 | Đáp án: "khu vực Vũng Tàu cũ nay gồm các phường". TP Vũng Tàu cũ (17 đơn vị) nay thuộc phường Vũng Tàu, Tam Thắng, Rạch Dừa, Phước Thắng **và xã Long Sơn** (NQ 1685). | "... nay gồm các phường Vũng Tàu, Tam Thắng, Rạch Dừa, Phước Thắng và xã Long Sơn" hoặc "các phường và xã Long Sơn". |
| C-0004 | Đáp án: "khu vực Rạch Giá cũ nay là phường Rạch Giá". TP Rạch Giá cũ (11 đơn vị) nay thuộc phường Rạch Giá (9 đơn vị cũ) **và phường Vĩnh Thông** (2 đơn vị cũ) (NQ 1654). | "... nay gồm phường Rạch Giá và phường Vĩnh Thông". |

Ý chính (tỉnh, thành phố hiện nay) của C-0001 và C-0004 vẫn đúng; sửa để chi tiết phụ không sai (spec 4.5). C-0002, C-0003, C-0005, C-0006, C-0007 đã viết "trong đó có phường X" nên đạt.

## 3. Lỗi chấm điểm nhóm F (`answer_type = premise_rejection`)

- `auto_label` chấm `premise_rejection` bằng `rejects_premise()`, dựa trên `PREMISE_REJECTION_MARKERS` ("không còn", "đã bãi bỏ", "đã sáp nhập"...). Các cụm này hợp với câu bẫy cấp huyện nhưng **không nhận ra câu bác tin đồn** ("Không đúng", "không chính xác").
- Hệ quả: 12/12 đáp án vàng nhóm F bị chấm `OTHER_ERROR`; đáp án xác nhận tin đồn của F-0004, F-0007, F-0008, F-0009 lại được chấm `CORRECT_CURRENT`. Trên đầu ra C0, các câu mô hình bác đúng tin đồn (ví dụ Qwen F-0007: "Không đúng. Thành phố Huế chưa bao giờ được sáp nhập vào thành phố Đà Nẵng...") bị chấm `OTHER_ERROR`.
- Thử đổi `answer_type` của 12 câu F sang `yes_no` (không sửa code): 12/12 đáp án vàng → `CORRECT_CURRENT`; đầu ra C0 Qwen: `OTHER_ERROR` 8 → 0, `CORRECT_CURRENT` 0 → 7; Gemini C0: `OTHER_ERROR` 8 → 0, `CORRECT_CURRENT` 0 → 4 (còn lại chờ giám khảo).
- **Đề xuất:** đổi 12 câu F sang `answer_type = "yes_no"` (đáp án "Không đúng"), hoặc thêm cụm bác tin đồn vào bộ nhận diện riêng cho F (không thêm vào `PREMISE_REJECTION_MARKERS` chung để khỏi ảnh hưởng nhóm B). Sau đó chạy lại `results/w3_eval/` cho `tv3_v0.3` và `benchmark_v0.3`.

## 4. `aliases` có thể làm chấm nhầm câu lỗi thời là đúng

| ID | Alias cần bỏ | Lý do |
|---|---|---|
| C-0013, C-0014, C-0015, C-0016, C-0017 | "Bình Định", "Phú Yên", "Thái Bình", "Sóc Trăng", "Kiên Giang" | Tên tỉnh cũ đặt làm alias cho câu có/không; câu trả lời lỗi thời kiểu "Gia Lai không giáp biển, Bình Định mới giáp biển" có thể khớp alias |
| D-0001 | "63" | Câu trả lời lỗi thời "Việt Nam có 63 tỉnh, thành phố" khớp alias |

## 5. Ghi chú nhỏ (không bắt buộc sửa)

- D-0015, D-0017, D-0018: vế "trước 01/07/2025" dựa vào Luật Tổ chức chính quyền địa phương 2015 (sửa 2019), văn bản này không có trong kho. Nội dung đúng; nên ghi rõ trong `verification_note`.
- D-0001: mốc Huế lên thành phố trực thuộc trung ương (01/01/2025) cũng ngoài kho; đúng.
- C-0021 (`obsolete_entities` "Bình Thuận"), C-0022 ("Tiền Giang"): tên này cũng xuất hiện trong đáp án vàng ở mệnh đề quá khứ; đã chạy `auto_label` trên đáp án vàng, không bị chấm `STALE`.

Sau khi TV3 sửa mục 2–4, TV1 kiểm lại các câu đã sửa và đồng ý đặt `verified = true` cho 60 câu.

## 6. Đã sửa (TV1, 28/11/2026, Vinh bận nên TV1 sửa thay)

Sửa trong `qgen/build_tv3_v03.py` rồi chạy lại, gộp bằng `scripts/merge_benchmark_v03.py`, chấm lại bằng `eval/run_w3_eval.py`.

| Mục | Đã làm |
|---|---|
| F-0002 | Đổi tin đồn sang "34 tỉnh còn 16 tỉnh"; đáp án theo CV 10988/BNV-CQĐP; ghi lý do (CV 6218/BNV-CQĐP) trong `verification_note` |
| F-0001 | Bỏ Thông tư 31/2026/TT-BNV; giữ NĐ 185/2026/NĐ-CP ngày 26/5/2026, thêm `source_url` |
| C-0012 | "Hồ thủy điện Hòa Bình" → "Nhà máy thủy điện Hòa Bình" (câu hỏi và đáp án lỗi thời) |
| C-0001, C-0004 | Ghi đủ đơn vị mới của TP Vũng Tàu cũ (thêm xã Long Sơn) và TP Rạch Giá cũ (thêm phường Vĩnh Thông) |
| Nhóm F (12 câu) | `answer_type`: `premise_rejection` → `yes_no`; 12/12 đáp án vàng chấm `CORRECT_CURRENT` |
| Alias | Bỏ tên tỉnh cũ ở C-0013..C-0017 và "63" ở D-0001 |
| `verified` | 55/60 câu `true` (TV1 kiểm chéo); 5 câu TV1 đổi nội dung (C-0001, C-0004, C-0012, F-0001, F-0002) chờ TV3 xem lại. Bộ v0.3: 223/308 câu `verified` |
| Chấm lại | `eval/run_w3_eval.py` bỏ đầu ra cũ của C-0012, F-0002 (16 đầu ra) vì câu hỏi đã đổi nghĩa, chờ TV2 chạy lại. Trên 308 câu, SR gần như không đổi (lệch dưới 1,5 điểm %); EM trên 60 câu tăng mạnh vì nhóm F được chấm đúng (ví dụ Qwen C3: 54,8% → 88,0%) |
| Test | `tests/test_benchmark_v03.py`: thay kiểm "60 câu chưa verified" bằng kiểm 5 câu chờ và nhóm F dùng `yes_no`; 147 test đạt |
