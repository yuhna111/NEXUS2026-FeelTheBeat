# Đặc tả độ đo — VN-Admin2025-QA

> File: `eval/metrics_spec.md` · Phụ trách: Thành viên 3 · Phiên bản: v0.3 (Tuần 2, 22/11/2026)
>
> Mục đích: định nghĩa **chính xác** cách chấm một câu trả lời và cách tính từng con số trong bài báo, để (1) cả nhóm chấm giống nhau, (2) code `eval/metrics.py` ở Tuần 2 làm đúng theo, (3) giám khảo đọc là tái lập được.

---

## 1. Ký hiệu

| Ký hiệu | Ý nghĩa | Lấy từ đâu |
|---|---|---|
| *i* | Một câu hỏi trong benchmark, *i* = 1…N | `id` trong file JSONL |
| *q*ᵢ | Nội dung câu hỏi | `question` |
| ŷᵢ | Câu trả lời của mô hình **sau khi chuẩn hóa** (mục 2) | đầu ra mô hình |
| Ŷᵢ | Tập thực thể hành chính trích ra từ ŷᵢ (mục 3) | `extract_entities(ŷᵢ)` |
| Gᵢ | Tập đáp án đúng (kèm bí danh) | `gold_answer` |
| Oᵢ | Tập thực thể lỗi thời của câu *i* | `obsolete_answer.obsolete_entities` |
| Eᵢ | Tập đoạn văn bản chứa bằng chứng vàng | `evidence` |
| ℓᵢ | Nhãn của câu trả lời (mục 4) | người gán hoặc bộ chấm |
| *k* | Cấu hình chạy: C0 (closed-book) … C5 (oracle) | ma trận thực nghiệm |

---

## 2. Chuẩn hóa văn bản

Mọi so khớp đều làm **sau** chuẩn hóa. Thứ tự các bước:

1. **Unicode NFC.** Tiếng Việt có hai cách mã hóa dấu (dựng sẵn / tổ hợp); không chuẩn hóa thì "Đắk Nông" và "Đắk Nông" bị coi là khác nhau.
2. **Chữ thường.**
3. **Thay ký tự đặc biệt:** gạch nối dài (–, —) → "-"; bỏ dấu câu cuối câu; gộp nhiều khoảng trắng thành một.
4. **Ánh xạ bí danh** theo bảng `eval/aliases.csv` (TV1 và TV3 cùng duy trì). Ví dụ:

| Cách viết gặp trong câu trả lời | Chuẩn hóa thành |
|---|---|
| TP.HCM, TP HCM, HCMC, Sài Gòn, thành phố Hồ Chí Minh | `thành phố hồ chí minh` |
| Đak Nông, Đắc Nông, Dak Nong | `đắk nông` |
| BR-VT, Bà Rịa Vũng Tàu, Bà Rịa – Vũng Tàu | `bà rịa - vũng tàu` |
| Tp. Huế, thành phố Huế | `huế` |

5. **Tiền tố hành chính** ("tỉnh", "thành phố", "tp.", "quận", "huyện", "thị xã", "phường", "xã"): **tách ra thành thuộc tính, không xóa bỏ.** Ví dụ "huyện Gia Lâm" → `{tên: gia lâm, loại: huyện}`.
   - Lý do: chữ "huyện", "thị xã", "thị trấn" chính là **dấu hiệu lỗi thời**. Xóa đi thì mất thông tin để chấm nhóm B.

**Không** bỏ dấu tiếng Việt (bỏ dấu làm "Hà Nam" và "Hà Nậm" trùng nhau, "Bắc Ninh" và "Bạc Liêu" sai khác khó kiểm soát). Cách viết không dấu xử lý bằng bảng bí danh.

> Lưu ý bẫy: "Thừa Thiên Huế" **không** được gộp vào bí danh của "huế". Đây là tên cũ (đổi từ 01/01/2025), nên là một thực thể lỗi thời riêng.

---

## 3. Trích xuất thực thể

Trích Ŷᵢ bằng **so khớp từ điển**, chưa dùng mô hình NER:

- Từ điển gồm: 34 đơn vị cấp tỉnh mới, 63 đơn vị cấp tỉnh cũ, ~696 đơn vị cấp huyện cũ (bảng `entity_map_63_34.csv` và `commune_lineage.csv` của TV1), sau này thêm cấp xã.
- Mỗi thực thể trong từ điển có cờ `status ∈ {current, obsolete, both}`.
  - `both`: tên vẫn dùng nhưng nghĩa đã đổi. Ví dụ "Lâm Đồng" vừa là tỉnh cũ (1 tỉnh) vừa là tỉnh mới (gồm 3 tỉnh). Những tên này **không** tự động coi là lỗi thời; phải xét ngữ cảnh (mục 4).
- So khớp **dài nhất trước** ("bà rịa - vũng tàu" trước "vũng tàu"; "thành phố hồ chí minh" trước "hồ chí minh").

---

## 4. Năm nhãn và quy tắc gán

### 4.1 Định nghĩa

| Nhãn | Định nghĩa | Ví dụ (câu C03: Phố cổ Hội An thuộc tỉnh/thành nào?) |
|---|---|---|
| `CORRECT_CURRENT` | Đúng theo cấu trúc hiện hành; không khẳng định thông tin cũ như hiện tại | "Hội An nay thuộc TP Đà Nẵng." |
| `STALE` | Khẳng định thông tin **trước 01/07/2025** như đang đúng, và không có thông tin mới đúng | "Hội An thuộc tỉnh Quảng Nam." |
| `BLENDED` | Vừa có thông tin mới đúng, vừa khẳng định thông tin cũ như hiện tại | "Hội An thuộc TP Đà Nẵng, tỉnh Quảng Nam." |
| `OTHER_ERROR` | Sai nhưng **không** do lỗi thời: bịa, nhầm tỉnh, nêu thiếu | "Hội An thuộc tỉnh Quảng Ngãi." |
| `ABSTAIN` | Không đưa ra đáp án: từ chối, nói không biết/không chắc | "Tôi không có thông tin chắc chắn về điều này." |

### 4.2 Cây quyết định (đi theo đúng thứ tự)

```text
Bước 1. Câu trả lời có đưa ra đáp án nào không?
        Không, và cũng không mặc nhiên coi đơn vị/cấu trúc cũ là đang tồn tại → ABSTAIN
        Không, nhưng nói về đơn vị đã bị bỏ như đang tồn tại → sang Bước 2 (thường là STALE)

Bước 2. Có thực thể/cấu trúc lỗi thời (thuộc Oᵢ hoặc có status = obsolete)
        được khẳng định là ĐANG đúng không?   (xem 4.3)
        Có  → Bước 3
        Không → Bước 4

Bước 3. Câu trả lời có đồng thời chứa đáp án mới đúng không?
        Có  → BLENDED
        Không → STALE

Bước 4. Đáp án có khớp đáp án đúng (Gᵢ) không?
        Có  → CORRECT_CURRENT
        Không → OTHER_ERROR
```

### 4.3 Thế nào là "khẳng định đang đúng"?

Một thực thể cũ **không** bị tính là lỗi thời nếu đi kèm dấu hiệu quá khứ trong cùng câu/mệnh đề:

- Từ chỉ quá khứ: "trước đây", "trước kia", "cũ", "từng là", "trước ngày 01/07/2025", "trước khi sáp nhập", "đã được sáp nhập", "đã bãi bỏ", "không còn".
- Ví dụ **không** tính lỗi thời: "Hội An *trước đây* thuộc Quảng Nam, nay thuộc Đà Nẵng." → `CORRECT_CURRENT`.
- Ví dụ **có** tính lỗi thời: "Hội An là thành phố thuộc tỉnh Quảng Nam" (thì hiện tại, không dấu hiệu quá khứ) → `STALE`.

### 4.4 Quy tắc riêng theo nhóm câu hỏi

| Nhóm | Quy tắc |
|---|---|
| A — Tra cứu trực tiếp | Đáp án dạng danh sách (ví dụ các tỉnh hợp nhất): đủ và đúng → `CORRECT_CURRENT`; thiếu hoặc thừa nhưng không có tên lỗi thời → `OTHER_ERROR` (mức đúng một phần đo bằng F1, mục 5.2). |
| B — Bẫy huyện cũ | Đúng **chỉ khi** mô hình bác tiền giả định (nói rõ cấp huyện/thị xã/quận không còn). Trả lời như đơn vị vẫn tồn tại → `STALE`, **kể cả khi từ chối nêu đáp án** (ví dụ "tôi không có dữ liệu cập nhật về Chủ tịch UBND huyện Gia Lâm"): việc mặc nhiên chấp nhận đơn vị đã bị bỏ chính là khẳng định cấu trúc cũ. Bác tiền giả định nhưng vẫn nhắc "thị trấn" như còn tồn tại → `BLENDED`. Bác đúng tiền giả định nhưng không nêu thêm thay đổi khác (ví dụ không nhắc Hà Giang đã hợp nhất) → vẫn `CORRECT_CURRENT`. |
| B — Câu đối chứng âm (B07) | Tiền giả định đúng. Mô hình bác bỏ (nói đơn vị không còn/đã sáp nhập) → `OTHER_ERROR`, đồng thời tính vào **Over-rejection** (mục 5.6). |
| C — Nhiều bước | Chấm theo **kết luận cuối**. Dừng ở bước trung gian (ví dụ trả lời "Bình Định" cho câu Quy Nhơn) → `STALE`. |
| D — Trước/sau | Phải đúng **cả hai** vế. Chấm vế "sau" trước, theo bảng con 4.4.1. |
| Đối chứng (A06, C06) | Không có đáp án lỗi thời. Sai → `OTHER_ERROR`. |

#### 4.4.1 Nhóm D (chốt 22/11 từ ca P-V-D01)

| Vế "sau" (từ 01/07/2025) | Vế "trước" | Nhãn | Ghi chú |
|---|---|---|---|
| Đúng | Đúng | `CORRECT_CURRENT` | |
| Đúng | Sai hoặc bỏ trống | `OTHER_ERROR` | |
| Khẳng định cấu trúc cũ vẫn áp dụng ("không thay đổi", "vẫn 3 cấp") | bất kỳ | `STALE` | Có thêm thông tin mới đúng ở chỗ khác → `BLENDED` (Bước 3) |
| Bỏ trống: chỉ mô tả vế "trước", có mốc quá khứ rõ ("Trước ngày 01/07/2025…"), không nói gì về hiện nay | Đúng | `OTHER_ERROR` | Ghi chú `thiếu vế sau`; đếm riêng trong báo cáo nhóm D |
| Bỏ trống, và vế "trước" **không** có mốc quá khứ (mô tả bằng thì hiện tại) | Đúng | `STALE` | Theo 4.3: không có dấu hiệu quá khứ thì coi là khẳng định hiện hành |

Lý do dòng 4: `STALE` đòi hỏi khẳng định thông tin cũ **như đang đúng** (4.1). Câu có mốc "Trước ngày 01/07/2025" là tường thuật quá khứ (4.3), nên chỉ là trả lời thiếu. Để không mất tín hiệu "mô hình không biết vế sau", số câu `thiếu vế sau` được báo cáo riêng cạnh SR của nhóm D.

> Ca gốc: P-V-D01 – DeepSeek chỉ trả lời "Trước ngày 01/07/2025… 3 cấp", không nhắc tình trạng hiện nay. TV1 gán `STALE`, TV3 gán `OTHER_ERROR` (bất đồng duy nhất trong 20 câu đo κ). Theo 4.4.1: `OTHER_ERROR` + `thiếu vế sau`. **TV1 cần xác nhận** trước khi đóng ca.

### 4.5 Ca khó đã thống nhất

| Tình huống | Nhãn | Ghi chú |
|---|---|---|
| Trả lời đúng nhưng kèm "theo thông tin tôi có đến năm 2024…" rồi nêu thông tin cũ | `STALE` | Lời rào đón không cứu được câu trả lời sai |
| Nêu cả hai khả năng: "có thể là Quảng Nam hoặc Đà Nẵng tùy thời điểm" mà không chỉ rõ cái nào hiện hành | `BLENDED` | |
| Trả lời đúng tỉnh mới nhưng gọi sai loại đơn vị (ví dụ "thành phố Phú Quốc, tỉnh An Giang") | `BLENDED` | Loại đơn vị cũng là thông tin hành chính |
| Trả lời bằng tiếng Anh nhưng nội dung đúng | Chấm theo nội dung | Ghi chú "trả lời tiếng Anh"; thống kê riêng |
| Câu trả lời có dùng tìm kiếm web (có link, nguồn) | Vẫn gán nhãn, đánh dấu `web_used = true` | Loại khỏi số liệu closed-book |
| Từ chối nêu đáp án nhưng nói về đơn vị đã bị bỏ như đang tồn tại (nhóm B) | `STALE` | Chốt 14/11 từ pilot B01 – DeepSeek |
| Mô tả **đúng tình trạng ngay trước 01/07/2025**, dù giải thích bằng sự kiện cũ hơn (Lâm Đồng hợp nhất từ năm 1975; TP HCM từ Sài Gòn – Gia Định) | `STALE` | Mốc so sánh là tình trạng ngay trước cải cách, không phải năm của sự kiện được nhắc |
| Mô tả tình trạng **đã không còn đúng từ trước 2025** (Gia Lai = Gia Lai + Kon Tum, vốn tách năm 1991) | `OTHER_ERROR` | Sai kiến thức, không phải lỗi thời của đợt 2025 |
| Rào đón, không biết về đợt sắp xếp nhưng kết luận vẫn đúng ("không có thông tin chính thức nào về việc tỉnh X sẽ hợp nhất") | `CORRECT_CURRENT` | Ghi chú "đúng do may"; không gán `ABSTAIN` vì mô hình có đưa ra kết luận. Thường gặp ở câu đối chứng |
| Tự mâu thuẫn (mở đầu "Không" nhưng giải thích lại cho thấy "Có"), không nêu thông tin cũ như hiện tại | `OTHER_ERROR` | Ghi chú "tự mâu thuẫn"; người dùng không biết tin vế nào |
| Nhóm B: nêu số liệu/tên cũ **trong mệnh đề có mốc quá khứ** ("Trước khi thực hiện sắp xếp…, huyện X, tỉnh Y có…") và bác cấp huyện, nhưng không nhắc tỉnh đã hợp nhất | `CORRECT_CURRENT` | Chốt 22/11 từ pilot B05 – ChatGPT (trước là `BLENDED`). Tên cũ trong mệnh đề quá khứ không tính là khẳng định (4.3); thiếu thay đổi cấp tỉnh xử lý như dòng "không nêu thêm thay đổi khác" ở 4.4 |
| Nhóm D: chỉ trả lời vế "trước" với mốc quá khứ rõ, bỏ trống vế "sau" | `OTHER_ERROR` | Ghi chú `thiếu vế sau` (4.4.1); chờ TV1 xác nhận |
| Đáp án chính đúng nhưng kèm chi tiết phụ chưa có trong đáp án vàng (ví dụ tên các phường mới) | `CORRECT_CURRENT` | TV1 dò chi tiết phụ với nghị quyết; nếu chi tiết phụ sai thì chuyển `OTHER_ERROR` |

---

## 5. Các độ đo

Quy ước chung:
- 𝟙[…] = 1 nếu điều kiện đúng, 0 nếu sai.
- Mẫu số mặc định = **tất cả câu đã có nhãn, kể cả ABSTAIN**. Tỷ lệ từ chối báo cáo riêng (5.7), để mô hình không thể "ăn điểm" bằng cách từ chối nhiều.
- Mọi tỷ lệ báo cáo kèm khoảng tin cậy 95% (mục 6).

### 5.1 Exact Match (EM)

```text
EM = (1/N) · Σᵢ 𝟙[ ŷᵢ khớp Gᵢ ]
```

"Khớp" định nghĩa theo **loại đáp án** (`answer_type`):

| answer_type | Thế nào là khớp | Ví dụ |
|---|---|---|
| `entity` | Thực thể chính trùng một phần tử của Gᵢ | "Đà Nẵng" |
| `set` | Tập thực thể trùng **đúng** Gᵢ (không thừa, không thiếu) | {Lâm Đồng, Đắk Nông, Bình Thuận} |
| `number` | Số trùng (sau khi bỏ dấu chấm/phẩy phân cách nghìn) | 34; 3.321 |
| `yes_no` | Có/Không trùng | "Không" |
| `premise_rejection` | Có cụm bác tiền giả định ("không còn", "đã bãi bỏ"…) | nhóm B |
| `before_after` | Cả hai vế trước/sau đều khớp | nhóm D |

> Ở câu trả lời dài, "khớp" không có nghĩa là cả câu trả lời trùng từng chữ với đáp án. Ta trích đáp án chính ra trước rồi mới so.

### 5.2 F1 (đúng một phần)

Dùng cho đáp án dạng tập hợp (`set`), ví dụ câu "tỉnh X gồm những tỉnh nào":

```text
Pᵢ = |Ŷᵢ ∩ Gᵢ| / |Ŷᵢ|        (độ chính xác: trong những gì nêu ra, bao nhiêu đúng)
Rᵢ = |Ŷᵢ ∩ Gᵢ| / |Gᵢ|        (độ phủ: trong những gì cần nêu, nêu được bao nhiêu)
F1ᵢ = 2 · Pᵢ · Rᵢ / (Pᵢ + Rᵢ)   (bằng 0 nếu Pᵢ + Rᵢ = 0)
F1  = trung bình F1ᵢ trên các câu
```

**Ví dụ tính tay:** câu A02, Gᵢ = {Lâm Đồng, Đắk Nông, Bình Thuận}; mô hình trả lời "Lâm Đồng và Đắk Nông".
P = 2/2 = 1,0 · R = 2/3 ≈ 0,67 · F1 = 2 × 1,0 × 0,67 / 1,67 ≈ **0,80**. EM = 0 (thiếu Bình Thuận).

### 5.3 Staleness Rate (SR) — độ đo chính của đề tài

```text
SR = (số câu có nhãn STALE) / (số câu đã gán nhãn)
```

Báo cáo thêm biến thể rộng, tính cả câu trộn cũ–mới:

```text
SR⁺ = (STALE + BLENDED) / (số câu đã gán nhãn)
```

Luôn báo cáo SR **tách theo**: nhóm câu hỏi (A–D), câu bẫy vs câu đối chứng, tỉnh hợp nhất vs tỉnh giữ nguyên.

**Ví dụ:** ChatGPT trả lời 30 câu, có 12 STALE, 3 BLENDED → SR = 12/30 = 40,0%; SR⁺ = 15/30 = 50,0%.

### 5.4 Knowledge Override Rate (KOR) — dùng từ Tuần 4–5

Trong những câu mô hình **trả lời lỗi thời khi không có tài liệu** (C0), bao nhiêu câu được RAG (cấu hình *k*) **sửa đúng**:

```text
KORₖ = |{ i : ℓᵢ(C0) = STALE  và  ℓᵢ(k) = CORRECT_CURRENT }|  /  |{ i : ℓᵢ(C0) = STALE }|
```

**Ví dụ:** ở C0 có 20 câu STALE; chạy lại 20 câu đó với C4 thì 15 câu thành CORRECT_CURRENT → KOR = 75%.

### 5.5 Prior Bias Error Rate (PBER) — dùng từ Tuần 4–5

Trong những câu mà **tài liệu đúng đã nằm trong ngữ cảnh** (truy xuất thành công, hoặc điều kiện oracle C5), mô hình **vẫn** trả lời lỗi thời bao nhiêu:

```text
PBERₖ = |{ i : Eᵢ có trong ngữ cảnh  và  ℓᵢ(k) ∈ {STALE, BLENDED} }|  /  |{ i : Eᵢ có trong ngữ cảnh }|
```

Đây là con số trả lời RQ3: "có tài liệu đúng rồi mà mô hình vẫn bám trí nhớ cũ". PBER tách bạch hai loại lỗi mà các bài RAG hay gộp chung: **không tìm được tài liệu** (đo bằng Recall@k) và **tìm được nhưng không tin tài liệu** (đo bằng PBER).

### 5.6 Over-rejection Rate

Trên các câu đối chứng âm (tiền giả định đúng):

```text
Over-rejection = (số câu mô hình bác bỏ tiền giả định) / (số câu đối chứng âm)
```

Mô hình có SR thấp nhưng Over-rejection cao nghĩa là nó "đúng" nhờ thấy gì cũng bác, chứ không thật sự biết.

### 5.7 Tỷ lệ từ chối (Abstention Rate)

```text
AbstainRate = (số câu ABSTAIN) / (số câu đã gán nhãn)
```

### 5.8 Độ đo truy xuất

```text
Recall@k = (1/N) · Σᵢ 𝟙[ ít nhất một đoạn đúng nằm trong top-k kết quả truy xuất ]
MRR@k    = (1/N) · Σᵢ 1 / (thứ hạng của đoạn đúng đầu tiên)    (bằng 0 nếu không có trong top-k)
```

- **Nhãn vàng:** khoản trong `gold_clause_ids` (`docs/qa_schema.md` mục 3). Câu có `["TODO_VERIFY_CLAUSE"]` bị loại khỏi N.
- **Đoạn đúng — chia theo Điều–Khoản (C2+):** `chunk_id` trùng một khoản vàng (`<doc_id>#D<điều>.K<khoản>`). Hàm: `recall_at_k`, `mrr`.
- **Đoạn đúng — chia cố định 512/64 (C1), chốt 22/11 (mục mở (3) của `qa_schema.md`):** đoạn `<doc_id>#fixed<i>` là đúng khi
  1. cùng `doc_id` với một khoản vàng, **và**
  2. chứa liên tục ít nhất **50%** số từ của khoản đó (so sau NFC, chữ thường, gộp khoảng trắng). Khoản nằm trọn trong đoạn thì tỷ lệ = 100%.

  Hàm: `clause_coverage`, `fixed_chunk_hit`, `fixed_hit_rank` (`eval/metrics.py`, ngưỡng `FIXED_MIN_COVER = 0.5`).

  Lý do: (a) đoạn chồng lấn 64 từ, nên khoản bị cắt ngang ranh giới đoạn vẫn có một đoạn chứa ≥ 50%; trên 34 khoản vàng của `pilot_80_v0.2` không khoản nào bị loại vì không đoạn nào đạt ngưỡng. (b) Quy tắc tạm "đoạn chứa 80 ký tự đầu của khoản" cho kết quả trúng giả khi văn bản khác trích lại cùng câu mở đầu: ở P-V-D01, đoạn `NQ-203-2025-QH15#fixed1` chứa 80 ký tự đầu của `LUAT-72-2025-QH15#D1.K1` nhưng chỉ chứa 15% khoản này.

  Chấm lại log top-20 của TV2 (`outputs/retrieval_w2/*_fixed.jsonl`, k = 5):

  | Truy xuất | Quy tắc tạm (80 ký tự đầu) | Quy tắc v0.3 |
  |---|---|---|
  | BM25 | 0,455 (25/55) | 0,455 (25/55) |
  | Vector (BGE-M3) | 0,545 (30/55) | 0,545 (30/55) |
  | Kết hợp (RRF) | 0,691 (38/55) | 0,673 (37/55) |

  Khác nhau đúng 1 câu (P-V-D01, trúng giả nêu trên). Trên 33 câu theo cách đếm của TV1 hai quy tắc cho cùng kết quả (0,455 / 0,667 / 0,758). Số liệu pilot, bộ câu chưa kiểm (`verified = false`).

---

## 6. Báo cáo và thống kê

- **Khoảng tin cậy 95%:** bootstrap 1.000 lần lấy mẫu lại theo câu hỏi.
- **So sánh hai cấu hình/mô hình** trên cùng bộ câu: paired bootstrap; với nhãn đúng/sai dùng kiểm định McNemar.
- **Nhiều phép so sánh cùng lúc:** hiệu chỉnh Holm–Bonferroni.
- **Pilot 30 câu:** chỉ báo cáo tỷ lệ và số câu (ví dụ "12/30"), **không** kết luận ý nghĩa thống kê vì mẫu quá nhỏ.

---

## 7. Gán nhãn và độ đồng thuận

- Hai người (TV1, TV3) gán nhãn độc lập trên cùng một mẫu, không xem nhãn của nhau.
- Đo **Cohen's κ** giữa hai người. Mục tiêu κ ≥ 0,75.
  - Cách hiểu nhanh: κ = 1 là trùng hoàn toàn; κ = 0 là trùng không hơn gì đoán ngẫu nhiên.
- Câu bất đồng: hai người thảo luận, chốt nhãn, và **bổ sung quy tắc vào mục 4.5** nếu đó là ca mới.
- **Kết quả đợt 1 (22/11/2026):** TV1 gán độc lập 20 câu trả lời chọn ngẫu nhiên trong 90 câu pilot (ẩn tên mô hình). Khớp 19/20, **κ = 0,912** (bootstrap 95%: 0,72–1,00; `scripts/kappa_tv1_tv3.py`). Bất đồng duy nhất: P-V-D01 – DeepSeek → quy tắc 4.4.1. Mẫu 20 câu còn nhỏ, khoảng tin cậy rộng; cần gán đủ 90 câu.
- Bộ chấm tự động (luật + LLM) ở các tuần sau được kiểm tra bằng κ so với nhãn người trên 300 câu.

---

## 8. Bài học từ pilot 30 câu

Pilot chạy ngày 14/11/2026 trên ChatGPT, DeepSeek (Search tắt) và Gemini Flash. Kết quả: SR = 0% / 40,0% / 80,0%; cả 3 mô hình đúng 3/3 câu đối chứng. Sau khi chốt B05 (22/11): SR không đổi; SR⁺ = 0% (0/30) / 46,7% (14/30) / 83,3% (25/30).

| Mã câu | Mô hình | Câu trả lời (rút gọn) | Vì sao khó gán nhãn | Nhãn đã chọn | Quy tắc rút ra |
|---|---|---|---|---|---|
| B01 | DeepSeek | "Tôi không có dữ liệu cập nhật để xác nhận ai đang giữ chức Chủ tịch UBND huyện Gia Lâm" | Từ chối trả lời nhưng vẫn coi huyện còn tồn tại | `STALE` (trước là `ABSTAIN`) | Bước 1 cây quyết định; bảng 4.4 nhóm B |
| A02 | DeepSeek | Lâm Đồng hiện nay hợp nhất từ Lâm Đồng và Tuyên Đức (năm 1975) | Nhắc sự kiện cũ hơn 2025 | `STALE` | Tình trạng ngay trước 2025 → STALE (4.5) |
| A03 | Gemini Flash | Gia Lai hợp nhất từ Gia Lai và Kon Tum | Sai, nhưng cũng không phải tình trạng trước 2025 | `OTHER_ERROR` | Tình trạng đã hết hiệu lực từ trước 2025 → OTHER_ERROR (4.5) |
| A06 | Gemini Flash | "Không có thông tin chính thức nào về việc Thanh Hóa sẽ hợp nhất" | Rào đón, thì tương lai, có thể xét ABSTAIN | `CORRECT_CURRENT` | Đúng do may (4.5) |
| C04 | DeepSeek | Mở đầu "Không", giải thích lại là có giáp biển qua Bình Thuận cũ | Tự mâu thuẫn | `OTHER_ERROR` | Tự mâu thuẫn (4.5) |
| B05 | ChatGPT | Số xã của huyện Mèo Vạc "trước khi sắp xếp", cấp huyện nay không còn; không nhắc Hà Giang hợp nhất | Có tên cũ nhưng trong ngữ cảnh quá khứ | `CORRECT_CURRENT` (chốt 22/11; trước là `BLENDED`) | 4.3, 4.4 nhóm B, dòng mới ở 4.5 |
| D01 | DeepSeek | "Trước ngày 01/07/2025… 3 cấp: tỉnh, huyện, xã", không nói gì về hiện nay | Thiếu vế sau, không khẳng định cũ là hiện hành | `OTHER_ERROR` + `thiếu vế sau` (TV1 gán `STALE`, chờ xác nhận) | 4.4.1 |
| B03, B04, B06 | ChatGPT | Nêu tên các phường mới cụ thể | Chi tiết cấp xã chưa có trong đáp án vàng | `CORRECT_CURRENT` | TV1 đã dò 23/11 (`docs/tv1_check_subdetails_B03_B04_B06.md`): B03 đúng, B06 đúng phần lớn, B04 sai (thiếu phường Hồng Hà) → đề xuất `OTHER_ERROR`; TV3 chốt |
| C07 | DeepSeek | "Đặc khu hành chính (tương đương cấp huyện)" thuộc An Giang | Đặc khu hiện là ĐVHC cấp xã | `CORRECT_CURRENT` | Đáp án chính (loại đơn vị, tỉnh) đúng; chi tiết phụ sai ghi chú |

---

## 9. Lịch sử thay đổi

| Phiên bản | Ngày | Người sửa | Nội dung |
|---|---|---|---|
| v0.1 | 15/11/2026 | TV3 | Bản đầu: ký hiệu, chuẩn hóa, 5 nhãn, độ đo, quy trình gán nhãn |
| v0.2 | 15/11/2026 | TV3 | Thêm quy tắc từ pilot: từ chối nhưng chấp nhận tiền giả định ở nhóm B → STALE; mốc "ngay trước 01/07/2025"; đúng do may; tự mâu thuẫn; chi tiết phụ chưa kiểm chứng. Điền mục 8 |
| v0.3 | 22/11/2026 | TV3 | Bảng con 4.4.1 cho nhóm D (ca P-V-D01, chờ TV1 xác nhận); chốt B05 – ChatGPT → `CORRECT_CURRENT`; quy tắc Recall@k cho đoạn cố định (cùng văn bản + phủ liên tục ≥ 50% khoản vàng) và số liệu chấm lại; ghi κ đợt 1 = 0,912 (n = 20) vào mục 7 |
