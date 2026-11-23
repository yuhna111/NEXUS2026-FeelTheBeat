# TV1 dò chi tiết phụ: B03, B04, B06 (ChatGPT, pilot 14/11)

TV1, 23/11/2026. Theo `eval/metrics_spec.md` mục 4.5: nếu đáp án chính đúng nhưng chi tiết phụ (tên các phường mới) chưa có trong đáp án vàng thì gán `CORRECT_CURRENT` và chờ TV1 dò; nếu chi tiết phụ sai thì chuyển sang `OTHER_ERROR`.

**Cách dò.** Lấy danh sách phường, xã cũ của từng đơn vị cấp huyện (trước 01/07/2025), tra trong `data/processed/commune_lineage.csv` (NQ 1656 cho Hà Nội, NQ 1685 cho TP HCM), rồi đọc lại từng khoản trong `data/parsed/`. Bỏ các kết quả trùng tên với phường, xã ở huyện khác (ví dụ xã An Phú của Củ Chi, xã Long Phước của Bà Rịa, phường Quang Trung của Đống Đa và Hà Đông).

**Lưu ý.** Danh sách phường, xã cũ của từng huyện là thông tin bên ngoài nghị quyết (nghị quyết chỉ ghi tên huyện khi tên phường bị trùng). TV3 nên kiểm lại danh sách này khi duyệt.

## B03 – "Thành phố Thủ Đức hiện có bao nhiêu phường?"

ChatGPT: khu vực Thủ Đức cũ "được sắp xếp thành 12 phường".

NQ 1685, Điều 1, khoản 67–78: 34 phường cũ của TP Thủ Đức thành **12 phường mới**: Hiệp Bình (k67), Thủ Đức (k68), Tam Bình (k69), Linh Xuân (k70), Tăng Nhơn Phú (k71), Long Bình (k72), Long Phước (k73), Long Trường (k74), Cát Lái (k75), Bình Trưng (k76), Phước Long (k77), An Khánh (k78). Không có phường cũ nào của Thủ Đức bị chia sang đơn vị ngoài 12 phường này.

**Kết luận: chi tiết phụ đúng.** Giữ `CORRECT_CURRENT`.

## B04 – "Quận Hoàn Kiếm hiện có bao nhiêu phường?"

ChatGPT: địa bàn quận Hoàn Kiếm cũ "được tổ chức lại thành 2 phường mới: Hoàn Kiếm, Cửa Nam".

NQ 1656, Điều 1:
- k1 → phường Hoàn Kiếm: toàn bộ Hàng Bạc, Hàng Bồ, Hàng Buồm, Hàng Đào, Hàng Gai, Hàng Mã, Lý Thái Tổ và một phần Cửa Đông, Cửa Nam, Đồng Xuân, Hàng Bông, Hàng Trống, Tràng Tiền.
- k2 → phường Cửa Nam: toàn bộ Hàng Bài, Phan Chu Trinh, Trần Hưng Đạo, một phần Cửa Nam, phần còn lại của Hàng Bông, Hàng Trống, Tràng Tiền.
- k14 → phường Hồng Hà: **toàn bộ phường Chương Dương và phường Phúc Tân** (2 phường cũ của Hoàn Kiếm), cùng phường Phúc Xá và một phần của nhiều phường khác.
- k3 → phường Ba Đình: phần còn lại của phường Cửa Đông và phường Đồng Xuân, một phần phường Cửa Nam.
- k11 → phường Văn Miếu - Quốc Tử Giám: phần còn lại của phường Cửa Nam.

Tên 2 phường ChatGPT nêu là có thật, nhưng câu "được tổ chức lại thành 2 phường mới" **sai**: 2 phường cũ Chương Dương và Phúc Tân sáp nhập trọn vào phường Hồng Hà, và một phần địa bàn thuộc phường Ba Đình và phường Văn Miếu - Quốc Tử Giám.

**Kết luận: chi tiết phụ sai.** Theo mục 4.5, đề xuất chuyển `CORRECT_CURRENT` → `OTHER_ERROR`, ghi chú `chi tiết phụ sai: thiếu phường Hồng Hà`. TV3 chốt.

## B06 – "Thị xã Sơn Tây hiện có bao nhiêu phường và xã?"

ChatGPT: "2 phường: Sơn Tây, Tùng Thiện; 1 xã: Đoài Phương".

NQ 1656, Điều 1:
- k50 → phường Sơn Tây: toàn bộ Ngô Quyền, Phú Thịnh, Viên Sơn, xã Đường Lâm, một phần Trung Hưng, Sơn Lộc, Thanh Mỹ.
- k51 → phường Tùng Thiện: toàn bộ Xuân Khanh, Trung Sơn Trầm, xã Xuân Sơn, phần còn lại của Trung Hưng, Sơn Lộc, Thanh Mỹ.
- k89 → xã Đoài Phương: toàn bộ xã Kim Sơn, xã Sơn Đông, một phần xã Cổ Đông.
- k96 → xã Hòa Lạc: **phần còn lại của xã Cổ Đông**, cùng phần của các xã thuộc huyện khác.

Ba đơn vị ChatGPT nêu đều đúng và chứa gần hết địa bàn Sơn Tây cũ. Phần còn lại của xã Cổ Đông thuộc xã Hòa Lạc, nên tính chặt thì địa bàn cũ nằm trong 4 đơn vị (2 phường, 2 xã). Ngoài ra, phường Lê Lợi và phường Quang Trung cũ của Sơn Tây không tìm thấy trong NQ 1656 dưới đúng tên đó (có thể đã nhập vào phường khác trước 2025); chưa dò thêm.

**Kết luận: chi tiết phụ đúng phần lớn, thiếu một phần xã Cổ Đông.** Đề xuất giữ `CORRECT_CURRENT`, ghi chú `chi tiết phụ thiếu: phần còn lại xã Cổ Đông → xã Hòa Lạc`. TV3 chốt có coi đây là "sai" theo 4.5 hay không.

## Ảnh hưởng tới số liệu

Chuyển B04 sang `OTHER_ERROR` không đổi SR của ChatGPT (SR chỉ đếm `STALE`), nhưng giảm tỷ lệ `CORRECT_CURRENT` của ChatGPT đi 1/30.
