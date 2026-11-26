# Bất đồng nhãn TV1 – TV3 trên 90 câu trả lời pilot

TV1 gán độc lập (đợt 1: 20 câu, 22/11; đợt 2: 70 câu, 26/11), ẩn tên mô hình. TV3 gán 14/11 và chỉnh theo spec v0.3.1.

**Kết quả:** n = 90, khớp 73/90, Cohen's κ = 0,675 (bootstrap 95%: 0,56–0,79), dưới mục tiêu 0,75 (metrics_spec mục 9). Riêng đợt 2: κ = 0,606 (54/70). Nếu chỉ xét "có phải STALE hay không" (cái quyết định SR): khớp 79/90, κ = 0,737.

7/17 ca là TV1 `OTHER_ERROR` – TV3 `STALE`: ranh giới giữa "tình trạng ngay trước 01/07/2025" (STALE) và "sai theo cách khác" (OTHER_ERROR) chưa đủ rõ trong hướng dẫn. 3 ca (#6, #10, #11) đã có quy tắc trong spec, TV1 gán độc lập nên chưa áp dụng. Đề xuất: TV1 và TV3 thống nhất 14 ca còn lại dưới đây, ghi nhãn chốt và quy tắc rút ra vào spec; **không sửa nhãn độc lập ban đầu** (giữ để báo κ).

| # | Câu | Mô hình | TV1 | TV3 | Nhãn chốt | Quy tắc rút ra |
|---|---|---|---|---|---|---|
| 1 | P-V-A02 | deepseek | OTHER_ERROR | STALE | | |
| 2 | P-V-A02 | gemini-flash | OTHER_ERROR | STALE | | |
| 3 | P-V-A04 | gemini-flash | OTHER_ERROR | STALE | | |
| 4 | P-V-B01 | gemini-flash | OTHER_ERROR | STALE | | |
| 5 | P-V-C05 | deepseek | OTHER_ERROR | STALE | | |
| 6 | P-V-D01 | deepseek | STALE | OTHER_ERROR | OTHER_ERROR (đã chốt 23/11) | 4.4.1: thiếu vế sau |
| 7 | P-V-D03 | gemini-flash | OTHER_ERROR | STALE | | |
| 8 | P-V-D07 | gemini-flash | OTHER_ERROR | STALE | | |
| 9 | P-V-A05 | chatgpt | OTHER_ERROR | CORRECT_CURRENT | | |
| 10 | P-V-B01 | deepseek | ABSTAIN | STALE | STALE (đã có trong spec) | 4.5: từ chối nhưng vẫn chấp nhận tiền giả định ở nhóm B → STALE |
| 11 | P-V-B04 | chatgpt | CORRECT_CURRENT | OTHER_ERROR | OTHER_ERROR (đã chốt 23/11) | 4.5: chi tiết phụ sai (docs/tv1_check_subdetails_B03_B04_B06.md) |
| 12 | P-V-B08 | deepseek | STALE | BLENDED | | |
| 13 | P-V-C04 | deepseek | CORRECT_CURRENT | OTHER_ERROR | | |
| 14 | P-V-D01 | gemini-flash | BLENDED | STALE | | |
| 15 | P-V-D04 | deepseek | CORRECT_CURRENT | BLENDED | | |
| 16 | P-V-D04 | chatgpt | OTHER_ERROR | CORRECT_CURRENT | | |
| 17 | P-V-D06 | gemini-flash | CORRECT_CURRENT | BLENDED | | |

## Chi tiết từng ca

### 1. P-V-A02 [deepseek]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Tỉnh Lâm Đồng hiện nay được hình thành từ những tỉnh nào?
- **Đáp án chuẩn:** Tỉnh Lâm Đồng mới được hợp nhất từ 3 tỉnh: Lâm Đồng, Đắk Nông và Bình Thuận.
- **Đáp án lỗi thời điển hình:** Lâm Đồng là một tỉnh riêng ở Tây Nguyên, thủ phủ là Đà Lạt, không sáp nhập với tỉnh nào.
- **Câu trả lời:** Tỉnh Lâm Đồng hiện nay được hình thành trên cơ sở hợp nhất hai tỉnh Lâm Đồng và Tuyên Đức (cùng với một phần đất của tỉnh Ninh Thuận và Bình Thuận cũ) theo Nghị quyết của Quốc hội khóa VI ngày 11/12/1975, có hiệu lực từ năm 1976.

### 2. P-V-A02 [gemini-flash]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Tỉnh Lâm Đồng hiện nay được hình thành từ những tỉnh nào?
- **Đáp án chuẩn:** Tỉnh Lâm Đồng mới được hợp nhất từ 3 tỉnh: Lâm Đồng, Đắk Nông và Bình Thuận.
- **Đáp án lỗi thời điển hình:** Lâm Đồng là một tỉnh riêng ở Tây Nguyên, thủ phủ là Đà Lạt, không sáp nhập với tỉnh nào.
- **Câu trả lời:** Câu hỏi của bạn có một chút nhầm lẫn về tên gọi địa danh. Hiện nay ở Việt Nam không có tỉnh nào tên là "Lâm Đồng" được hình thành từ việc sáp nhập các tỉnh khác theo cách bạn nghĩ. Có khả năng bạn đang muốn hỏi về tỉnh Lâm Đồng (tỉnh hiện tại) hoặc một địa danh khác có tên tương tự. Dưới đây là thông tin làm rõ: Về tỉnh Lâm Đồng (hiện nay): Tỉnh Lâm Đồng hiện nay không phải là kết quả của việc sáp nhập các tỉnh cũ theo kiểu đặt tên ghép (như Hà Tĩnh hay Thừa Thiên Huế). Về lịch sử, tỉnh Lâm Đồng được thành lập vào năm 1958 trên cơ sở sáp nhập tỉnh Lang Biang và tỉnh Đồng Tuyên. Đến năm 1976, tỉnh Lâm Đồng được hợp nhất với tỉnh Tuyên Đức và thành phố Đà Lạt để tạo thành tỉnh Lâm Đồng như ngày nay. Có thể bạn đang nhầm lẫn với các tỉnh có tên ghép: Nếu bạn đang hỏi về các tỉnh được ghép tên từ hai tỉnh cũ, một số ví dụ nổi tiếng ở Việt Nam là: Hà Tĩnh: Được tách ra từ tỉnh Nghệ Tĩnh (trướ…

### 3. P-V-A04 [gemini-flash]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Thành phố Hồ Chí Minh hiện nay được hợp nhất từ những đơn vị hành chính cấp tỉnh nào?
- **Đáp án chuẩn:** TP Hồ Chí Minh mới được hợp nhất từ TP Hồ Chí Minh, tỉnh Bình Dương và tỉnh Bà Rịa – Vũng Tàu.
- **Đáp án lỗi thời điển hình:** TP Hồ Chí Minh không hợp nhất với tỉnh nào, gồm 16 quận, 5 huyện và TP Thủ Đức.
- **Câu trả lời:** Thành phố Hồ Chí Minh hiện nay được hợp nhất từ hai đơn vị hành chính cấp tỉnh cũ là: Thành phố Sài Gòn và tỉnh Gia Định (cùng với một số phần diện tích nhỏ thuộc các tỉnh lân cận như Hậu Nghĩa, Long An).

### 4. P-V-B01 [gemini-flash]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Chủ tịch UBND huyện Gia Lâm (Hà Nội) hiện nay là ai?
- **Đáp án chuẩn:** Câu hỏi có tiền giả định sai: từ ngày 01/07/2025 cấp huyện đã bị bãi bỏ nên không còn UBND huyện Gia Lâm. Địa bàn huyện cũ nay thuộc các xã, phường mới trực thuộc TP Hà Nội.
- **Đáp án lỗi thời điển hình:** Nêu tên một người cụ thể là Chủ tịch UBND huyện Gia Lâm.
- **Câu trả lời:** Theo thông tin cập nhật mới nhất, Chủ tịch UBND huyện Gia Lâm (Hà Nội) hiện nay là ông Đặng Thị Huyền.

### 5. P-V-C05 [deepseek]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Tỉnh Quảng Ngãi hiện có chung đường biên giới với những nước nào?
- **Đáp án chuẩn:** Lào và Campuchia, vì tỉnh Kon Tum (giáp Lào và Campuchia) đã hợp nhất vào tỉnh Quảng Ngãi.
- **Đáp án lỗi thời điển hình:** Không có. Quảng Ngãi là tỉnh duyên hải Nam Trung Bộ, không có biên giới quốc tế.
- **Câu trả lời:** Tỉnh Quảng Ngãi là tỉnh ven biển thuộc vùng Duyên hải Nam Trung Bộ Việt Nam, không có đường biên giới trên bộ với bất kỳ quốc gia nào. Toàn bộ ranh giới của tỉnh chỉ tiếp giáp với các tỉnh trong nước (Quảng Nam, Kon Tum, Gia Lai, Bình Định) và Biển Đông ở phía đông.

### 6. P-V-D01 [deepseek]: TV1 STALE · TV3 OTHER_ERROR

- **Câu hỏi:** Trước và sau ngày 01/07/2025, chính quyền địa phương ở Việt Nam được tổ chức thành mấy cấp?
- **Đáp án chuẩn:** Trước: 3 cấp (tỉnh – huyện – xã). Sau: 2 cấp (tỉnh – xã/phường/đặc khu); cấp huyện bị bãi bỏ.
- **Đáp án lỗi thời điển hình:** Chính quyền địa phương gồm 3 cấp: tỉnh, huyện, xã (không nêu thay đổi).
- **Câu trả lời:** Trước ngày 01/07/2025, chính quyền địa phương ở Việt Nam được tổ chức thành 3 cấp: cấp tỉnh (tỉnh, thành phố trực thuộc trung ương), cấp huyện (huyện, quận, thị xã, thành phố thuộc tỉnh, thành phố thuộc thành phố trực thuộc trung ương) và cấp xã (xã, phường, thị trấn).

### 7. P-V-D03 [gemini-flash]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Trước và sau ngày 01/07/2025, tỉnh Quảng Bình thay đổi như thế nào?
- **Đáp án chuẩn:** Trước: là tỉnh riêng, tỉnh lỵ Đồng Hới. Sau: hợp nhất vào tỉnh Quảng Trị; trung tâm hành chính của tỉnh Quảng Trị mới đặt tại khu vực Đồng Hới cũ.
- **Đáp án lỗi thời điển hình:** Quảng Bình vẫn là tỉnh riêng, tỉnh lỵ Đồng Hới.
- **Câu trả lời:** Trước ngày 01/01/2025: Quảng Bình vận hành với bộ máy hành chính cũ (151 xã, phường, thị trấn). Sau ngày 01/01/2025 (và đến thời điểm hiện tại): Tỉnh đã chính thức tinh gọn bộ máy, giảm số lượng đơn vị hành chính cấp xã xuống còn 136 đơn vị nhằm tập trung nguồn lực, tinh giản bộ máy và nâng cao hiệu quả quản lý nhà nước.

### 8. P-V-D07 [gemini-flash]: TV1 OTHER_ERROR · TV3 STALE

- **Câu hỏi:** Trước và sau ngày 01/07/2025, tỉnh Nam Định thay đổi như thế nào?
- **Đáp án chuẩn:** Trước: là tỉnh riêng, tỉnh lỵ TP Nam Định. Sau: hợp nhất vào tỉnh Ninh Bình (cùng tỉnh Hà Nam), không còn là đơn vị hành chính cấp tỉnh.
- **Đáp án lỗi thời điển hình:** Nam Định vẫn là tỉnh riêng, tỉnh lỵ TP Nam Định.
- **Câu trả lời:** Ngày 01/07/2025 là thời điểm Nghị quyết số 1213/NQ-UBTVQH15 của Ủy ban Thường vụ Quốc hội về việc sắp xếp đơn vị hành chính cấp huyện, cấp xã của tỉnh Nam Định giai đoạn 2023 – 2025 có hiệu lực thi hành. Dưới đây là những thay đổi chính về đơn vị hành chính cấp huyện của tỉnh Nam Định trước và sau thời điểm này: 1. Tình trạng trước ngày 01/07/2025: Tỉnh Nam Định có 10 đơn vị hành chính cấp huyện, bao gồm: 01 Thành phố: Nam Định. 09 Huyện: Giao Thủy, Hải Hậu, Mỹ Lộc, Nam Trực, Nghĩa Hưng, Trực Ninh, Vụ Bản, Xuân Trường, Ý Yên. 2. Tình trạng từ ngày 01/07/2025: Sau khi sắp xếp, tỉnh Nam Định sẽ giảm xuống còn 08 đơn vị hành chính cấp huyện (giảm 2 đơn vị), cụ thể: Thành phố Nam Định: Được mở rộng bằng cách nhập toàn bộ diện tích tự nhiên và quy mô dân số của huyện Mỹ Lộc vào thành phố Nam Định hiện tại. Huyện mới Bình Yên: Được thành lập trên cơ sở nhập toàn bộ diện tích tự nhiên và quy mô…

### 9. P-V-A05 [chatgpt]: TV1 OTHER_ERROR · TV3 CORRECT_CURRENT

- **Câu hỏi:** Bình Dương hiện nay còn là một tỉnh riêng không?
- **Đáp án chuẩn:** Không. Từ ngày 01/07/2025, tỉnh Bình Dương đã hợp nhất vào TP Hồ Chí Minh và không còn là đơn vị hành chính cấp tỉnh.
- **Đáp án lỗi thời điển hình:** Có, Bình Dương là một tỉnh thuộc vùng Đông Nam Bộ, tỉnh lỵ là TP Thủ Dầu Một.
- **Câu trả lời:** Không. Từ ngày 1/7/2025, Bình Dương không còn là tỉnh riêng biệt. Tỉnh Bình Dương đã được sáp nhập với: - Tỉnh Bình Dương (cũ). - Tỉnh Bà Rịa – Vũng Tàu (cũ). - Thành phố Hồ Chí Minh (cũ).

### 10. P-V-B01 [deepseek]: TV1 ABSTAIN · TV3 STALE

- **Câu hỏi:** Chủ tịch UBND huyện Gia Lâm (Hà Nội) hiện nay là ai?
- **Đáp án chuẩn:** Câu hỏi có tiền giả định sai: từ ngày 01/07/2025 cấp huyện đã bị bãi bỏ nên không còn UBND huyện Gia Lâm. Địa bàn huyện cũ nay thuộc các xã, phường mới trực thuộc TP Hà Nội.
- **Đáp án lỗi thời điển hình:** Nêu tên một người cụ thể là Chủ tịch UBND huyện Gia Lâm.
- **Câu trả lời:** Tính đến tháng 11/2026, thông tin công khai về nhân sự lãnh đạo UBND huyện Gia Lâm (Hà Nội) có thể đã thay đổi. Tôi không có dữ liệu cập nhật theo thời gian thực để xác nhận chính xác ai đang giữ chức Chủ tịch UBND huyện Gia Lâm hiện nay.

### 11. P-V-B04 [chatgpt]: TV1 CORRECT_CURRENT · TV3 OTHER_ERROR

- **Câu hỏi:** Quận Hoàn Kiếm hiện có bao nhiêu phường?
- **Đáp án chuẩn:** Câu hỏi có tiền giả định sai: không còn quận Hoàn Kiếm (cấp huyện, gồm cả quận, bị bãi bỏ từ 01/07/2025). Khu vực Hoàn Kiếm cũ nay là một số phường mới trực thuộc TP Hà Nội.
- **Đáp án lỗi thời điển hình:** Quận Hoàn Kiếm có 18 phường.
- **Câu trả lời:** Hiện nay (tháng 11/2026), quận Hoàn Kiếm không còn là đơn vị hành chính cấp quận sau đợt sắp xếp hành chính năm 2025. Địa bàn quận Hoàn Kiếm cũ được tổ chức lại thành 2 phường mới: 1. Phường Hoàn Kiếm. 2. Phường Cửa Nam.

### 12. P-V-B08 [deepseek]: TV1 STALE · TV3 BLENDED

- **Câu hỏi:** Đặc khu Côn Đảo hiện thuộc tỉnh/thành phố nào?
- **Đáp án chuẩn:** TP Hồ Chí Minh. Côn Đảo trước đây là huyện thuộc tỉnh Bà Rịa – Vũng Tàu; từ 01/07/2025 là đặc khu Côn Đảo thuộc TP Hồ Chí Minh.
- **Đáp án lỗi thời điển hình:** Côn Đảo là huyện thuộc tỉnh Bà Rịa – Vũng Tàu.
- **Câu trả lời:** Tính đến năm 2025, Đặc khu Côn Đảo thuộc tỉnh Bà Rịa – Vũng Tàu (sau khi sắp xếp đơn vị hành chính, tỉnh Bà Rịa – Vũng Tàu được giữ nguyên và không sáp nhập với tỉnh nào khác).

### 13. P-V-C04 [deepseek]: TV1 CORRECT_CURRENT · TV3 OTHER_ERROR

- **Câu hỏi:** Tỉnh có thành phố Đà Lạt cũ hiện nay có giáp biển không?
- **Đáp án chuẩn:** Có. Tỉnh Lâm Đồng mới bao gồm cả tỉnh Bình Thuận cũ nên có bờ biển (khu vực Phan Thiết, Mũi Né) và cả đặc khu Phú Quý ngoài khơi.
- **Đáp án lỗi thời điển hình:** Không. Lâm Đồng là tỉnh Tây Nguyên, không giáp biển.
- **Câu trả lời:** Không. Tỉnh có thành phố Đà Lạt (hiện nay là tỉnh Lâm Đồng sau khi sáp nhập với Đắk Nông và Bình Thuận theo Nghị quyết 202/2025/QH15) có giáp biển — cụ thể là giáp Biển Đông qua địa phận tỉnh Bình Thuận cũ (các huyện Tuy Phong, Bắc Bình, Hàm Thuận Bắc, Hàm Thuận Nam, Hàm Tân, La Gi, Phan Thiết).

### 14. P-V-D01 [gemini-flash]: TV1 BLENDED · TV3 STALE

- **Câu hỏi:** Trước và sau ngày 01/07/2025, chính quyền địa phương ở Việt Nam được tổ chức thành mấy cấp?
- **Đáp án chuẩn:** Trước: 3 cấp (tỉnh – huyện – xã). Sau: 2 cấp (tỉnh – xã/phường/đặc khu); cấp huyện bị bãi bỏ.
- **Đáp án lỗi thời điển hình:** Chính quyền địa phương gồm 3 cấp: tỉnh, huyện, xã (không nêu thay đổi).
- **Câu trả lời:** 1. Trước ngày 01/07/2025: Theo Luật Tổ chức chính quyền địa phương 2015 (sửa đổi, bổ sung năm 2019), chính quyền địa phương ở Việt Nam được tổ chức thành 03 cấp: Cấp tỉnh (tỉnh, thành phố trực thuộc trung ương). Cấp huyện (huyện, quận, thị xã, thành phố thuộc tỉnh, thành phố thuộc thành phố trực thuộc trung ương). Cấp xã (xã, phường, thị trấn). 2. Từ ngày 01/07/2025 trở đi: Về mặt pháp lý căn bản, hệ thống tổ chức chính quyền địa phương vẫn được duy trì ở 03 cấp theo quy định của Hiến pháp 2013 và Luật Tổ chức chính quyền địa phương.

### 15. P-V-D04 [deepseek]: TV1 CORRECT_CURRENT · TV3 BLENDED

- **Câu hỏi:** Trung tâm hành chính của tỉnh Lào Cai trước và sau ngày 01/07/2025 đặt ở đâu?
- **Đáp án chuẩn:** Trước: TP Lào Cai. Sau: tỉnh Lào Cai mới (hợp nhất Lào Cai và Yên Bái) đặt trung tâm hành chính tại khu vực TP Yên Bái cũ.
- **Đáp án lỗi thời điển hình:** Trung tâm hành chính tỉnh Lào Cai đặt tại TP Lào Cai.
- **Câu trả lời:** Trước ngày 01/07/2025, trung tâm hành chính của tỉnh Lào Cai đặt tại thành phố Lào Cai. Từ ngày 01/07/2025, thực hiện chủ trương sắp xếp đơn vị hành chính cấp tỉnh, tỉnh Lào Cai và tỉnh Yên Bái hợp nhất thành tỉnh Lào Cai mới. Trung tâm hành chính của tỉnh Lào Cai mới đặt tại thành phố Lào Cai (trên cơ sở thành phố Lào Cai cũ).

### 16. P-V-D04 [chatgpt]: TV1 OTHER_ERROR · TV3 CORRECT_CURRENT

- **Câu hỏi:** Trung tâm hành chính của tỉnh Lào Cai trước và sau ngày 01/07/2025 đặt ở đâu?
- **Đáp án chuẩn:** Trước: TP Lào Cai. Sau: tỉnh Lào Cai mới (hợp nhất Lào Cai và Yên Bái) đặt trung tâm hành chính tại khu vực TP Yên Bái cũ.
- **Đáp án lỗi thời điển hình:** Trung tâm hành chính tỉnh Lào Cai đặt tại TP Lào Cai.
- **Câu trả lời:** Trước ngày 01/07/2025: Trung tâm hành chính tỉnh Lào Cai đặt tại thành phố Lào Cai, tỉnh Lào Cai (cũ). Từ ngày 01/07/2025: Sau khi sáp nhập tỉnh Lào Cai và tỉnh Yên Bái, trung tâm hành chính của tỉnh Lào Cai mới đặt tại thành phố Yên Bái, tỉnh Yên Bái (cũ).

### 17. P-V-D06 [gemini-flash]: TV1 CORRECT_CURRENT · TV3 BLENDED

- **Câu hỏi:** Trong đợt sắp xếp ngày 01/07/2025, thành phố Huế có hợp nhất với tỉnh nào không?
- **Đáp án chuẩn:** Không. Huế giữ nguyên ở cấp tỉnh (đã là thành phố trực thuộc trung ương từ 01/01/2025); chỉ cấp huyện bị bỏ và cấp xã được sắp xếp lại.
- **Đáp án lỗi thời điển hình:** Huế là thành phố thuộc tỉnh Thừa Thiên Huế.
- **Câu trả lời:** Câu trả lời ngắn gọn là: Không. Thành phố Huế và tỉnh Thừa Thiên Huế không hợp nhất với bất kỳ tỉnh nào khác.

