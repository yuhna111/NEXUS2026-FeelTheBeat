# 3. Tổng quan tài liệu — VN-Admin2025-QA

> File: `paper/related_work.md` · Phụ trách: Thành viên 3 · Phiên bản: v0.2 (Tuần 1, 14/11/2026)
>
> **Cách dùng file này**
> - **Phần A** — bảng tổng hợp 9 bài (đúng 5 cột theo yêu cầu tuần 1).
> - **Phần B** — "thẻ đọc" chi tiết từng bài: thông tin trích dẫn, vấn đề, phương pháp, kết quả chính, hạn chế, liên quan tới đề tài, và *việc cần tự kiểm tra khi đọc*.
> - **Phần C** — bảng định vị và 3 khoảng trống nghiên cứu.
> - **Phần D** — bản nháp văn xuôi mục 3 để đưa vào bài.
> - **Phần E** — câu hỏi giám khảo có thể hỏi và cách trả lời.
> - **Phần F** — danh mục tài liệu tham khảo (định dạng ACL) + link BibTeX chính thức.
> - **Phần G** — checklist khi đọc lại.
>
> **Mức độ kiểm chứng:** tác giả, năm, nơi công bố và số trang của cả 9 bài đã được đối chiếu với trang chính thức (ACL Anthology, PMLR, NeurIPS, ICLR, arXiv) ngày 14/11/2026. Nội dung tóm tắt dựa trên abstract và phần giới thiệu/phương pháp. Những chỗ đánh dấu **[kiểm tra]** là chi tiết lấy từ nguồn thứ cấp hoặc cần đọc bài gốc để xác nhận, **chưa được đưa vào bài nộp** trước khi kiểm tra.

---

## A. Bảng tổng hợp

| # | Tên bài | Năm · Nơi công bố | Vấn đề | Phương pháp | Liên quan gì tới đề tài mình |
|---|---|---|---|---|---|
| 1 | **TimeQA** — A Dataset for Answering Time-Sensitive Questions | 2021 · NeurIPS Datasets & Benchmarks | Các bộ QA phổ biến có rất ít câu hỏi phụ thuộc thời gian → không đo được khả năng suy luận thời gian. | Khai thác sự thật biến đổi theo thời gian từ WikiData, gióng với Wikipedia, người kiểm tra lại, sinh cặp hỏi–đáp; hai mức dễ/khó. | Đặt nền khái niệm "câu hỏi nhạy thời gian" (gần nhóm D – trước/sau). Khác: TimeQA hỏi về một mốc trong quá khứ và có cho tài liệu; mình hỏi về **hiện tại**, không cho tài liệu (C0) → đo trí nhớ lỗi thời. |
| 2 | **StreamingQA** — A Benchmark for Adaptation to New Knowledge over Time in QA Models | 2022 · ICML | Kiến thức của mô hình bị "đóng băng"; chưa có cách đo mô hình thích nghi với kiến thức mới theo thời gian. | Câu hỏi gắn ngày đặt câu hỏi, trả lời từ 14 năm tin tức có dấu thời gian; đánh giá theo quý; so sánh cập nhật tham số với cập nhật chỉ mục truy xuất. | Bằng chứng nền cho giả thuyết "trí nhớ tham số lỗi thời, truy xuất giúp cập nhật nhưng chưa đủ" → cơ sở của chuỗi C0→C4 và độ đo KOR. Khác: tin tức rời rạc tiếng Anh; mình có **một thay đổi cấu trúc với mốc hiệu lực duy nhất**. |
| 3 | **FreshLLMs / FreshQA** — Refreshing LLMs with Search Engine Augmentation | 2024 · Findings of ACL (arXiv 2023) | LLM huấn luyện một lần, không cập nhật → sai với kiến thức thay đổi nhanh và dễ chấp nhận tiền giả định sai. | Benchmark 4 loại câu (không đổi / đổi chậm / đổi nhanh / tiền giả định sai); chấm người theo 2 chế độ nghiêm ngặt – nới lỏng; đề xuất FreshPrompt (chèn kết quả tìm kiếm vào prompt). | **Gần đề tài nhất.** Câu tiền giả định sai ↔ nhóm B; chế độ chấm nghiêm ngặt ↔ ý tưởng nhãn `BLENDED`; FreshPrompt ↔ baseline RAG. Khác: tiếng Anh, không có câu đối chứng âm riêng, không tách lỗi truy xuất và lỗi không tin tài liệu. |
| 4 | **Entity-Based Knowledge Conflicts in Question Answering** | 2021 · EMNLP | Khi tài liệu mâu thuẫn với điều mô hình đã học, mô hình dùng nguồn nào? | Thay thực thể đáp án trong đoạn văn bằng thực thể khác để tạo xung đột nhân tạo; đo mức bám trí nhớ; đề xuất huấn luyện với dữ liệu đã thay thế. | Bài khởi đầu khái niệm **bám trí nhớ tham số** — hiện tượng PBER đo. Khác: xung đột do người tạo (tài liệu bị sửa sai); ở mình xung đột **tự nhiên** (tài liệu đúng, trí nhớ lỗi thời). |
| 5 | **Adaptive Chameleon or Stubborn Sloth** | 2024 · ICLR (arXiv 2023) | LLM tiếp nhận bằng chứng ngoài đến mức nào khi bằng chứng trái với trí nhớ của nó? | Gợi ra trí nhớ tham số của từng LLM, sinh "phản-trí nhớ" mạch lạc, thí nghiệm có kiểm soát. | Giải thích vì sao kho tài liệu **trộn văn bản cũ và mới** (C3/C4) có thể kéo mô hình về đáp án cũ → giả thuyết cho Tuần 4–5 và lý do cần nhãn `BLENDED`. |
| 6 | **ClashEval** — Quantifying the Tug-of-War between an LLM's Internal Prior and External Evidence | 2024 · NeurIPS Datasets & Benchmarks | Trong RAG, khi trí nhớ và tài liệu mâu thuẫn, mô hình phân xử ra sao? Có sửa khi trí nhớ sai không? | >1.200 câu hỏi, 6 lĩnh vực, mỗi câu kèm tài liệu có đáp án bị làm nhiễu từ nhẹ tới vô lý; độ đo accuracy, prior bias, context bias; 6 LLM. | **Bắt buộc phân biệt với PBER/KOR.** Prior bias ≈ "có tài liệu đúng mà vẫn bám trí nhớ sai". Mình khác: (1) trí nhớ sai do lỗi thời thật; (2) tách Recall@k và PBER; (3) có nhãn trộn `BLENDED`. |
| 7 | **Knowledge Conflicts for LLMs: A Survey** | 2024 · EMNLP | Thiếu một tổng quan hệ thống về xung đột tri thức của LLM. | Tổng quan, phân 3 loại: context–memory, inter-context, intra-memory; phân tích nguyên nhân, hành vi, giải pháp. | Cung cấp **thuật ngữ chuẩn** để gọi tên hiện tượng mình đo: C4/C5 = context–memory; kho trộn văn bản cũ–mới = inter-context; câu trả lời tự mâu thuẫn (C04) ≈ intra-memory. |
| 8 | **RAGAs** — Automated Evaluation of Retrieval Augmented Generation | 2024 · EACL System Demonstrations (arXiv 2023) | Đánh giá RAG tốn nhãn người và có nhiều chiều. | Bộ độ đo không cần đáp án vàng, dùng LLM chấm: faithfulness, answer relevance, context relevance. | Có thể dùng làm độ đo phụ. **Hạn chế cần nêu:** chỉ đo "bám ngữ cảnh", không đo "đúng với hiện tại" → văn bản cũ được truy xuất vẫn cho điểm cao trong khi mình chấm `STALE`. |
| 9 | **ARES** — An Automated Evaluation Framework for RAG Systems | 2024 · NAACL (arXiv 2023) | Bộ chấm dựa trên prompt viết tay cố định (như RAGAS) khó thích nghi, không đảm bảo chất lượng. | Sinh dữ liệu tổng hợp, fine-tune bộ chấm nhỏ cho 3 chiều; dùng ~150 nhãn người + prediction-powered inference (PPI) để có khoảng tin cậy. | Hậu thuẫn cách mình **kiểm tra bộ chấm tự động bằng tập nhãn người nhỏ** (κ trên 300 câu) và báo cáo khoảng tin cậy. Cùng hạn chế với RAGAS: không xét tính hiện hành. |

---

## B. Thẻ đọc chi tiết từng bài

> Mỗi thẻ có cùng cấu trúc. Mục "Tự kiểm tra khi đọc" là việc bạn làm khi mở bài gốc — đừng bỏ qua.

### B1. TimeQA

- **Trích dẫn:** Wenhu Chen, Xinyi Wang, William Yang Wang. 2021. *A Dataset for Answering Time-Sensitive Questions.* NeurIPS 2021 Datasets and Benchmarks Track.
- **Link:** [arXiv 2108.06314](https://arxiv.org/abs/2108.06314) · [dblp/BibTeX](https://dblp.org/rec/conf/nips/ChenWWW21) · code: github.com/wenhuchen/Time-Sensitive-QA
- **Vấn đề:** Nhiều sự thật thay đổi theo thời gian, nhưng các bộ QA lớn chứa rất ít câu hỏi thật sự phụ thuộc thời gian. Tác giả ghi nhận Natural Questions có dưới 5% câu hỏi chứa mốc thời gian, còn ở SQuAD mốc thời gian thường được chép nguyên từ đoạn văn nên không đòi hỏi suy luận.
- **Định nghĩa đáng chú ý:** một câu là *time-sensitive* khi (a) có cụm chỉ thời gian ("in 2007", "before 2010"), (b) đổi cụm đó thì đáp án đổi, (c) cần suy luận thời gian.
- **Phương pháp:** (1) khai thác các sự thật biến đổi theo thời gian từ WikiData và gióng với trang Wikipedia tương ứng; (2) dùng người gán nhãn kiểm tra và hiệu chỉnh; (3) sinh cặp hỏi–đáp. Có bản *easy* và *hard* (bản hard đòi hỏi suy luận thời gian nhiều hơn, ví dụ quan hệ "trong khoảng", "trước", "sau").
- **Kết quả chính:** mô hình QA văn bản dài tốt nhất (FiD) đạt khoảng 46%, con người đạt 87% → mô hình chưa suy luận thời gian ổn định.
- **Hạn chế (so với nhu cầu của mình):** bối cảnh đọc hiểu có tài liệu; mô hình thế hệ BigBird/FiD, chưa phải LLM hội thoại; câu hỏi về quá khứ chứ không về "bây giờ".
- **Liên quan tới đề tài:**
  - *Giống:* đáp án phụ thuộc mốc thời gian → nhóm D (trước/sau 01/07/2025) chính là câu time-sensitive theo đúng định nghĩa (a)(b).
  - *Khác:* câu nhóm A–C của mình **không có mốc thời gian trong câu** ("Hội An thuộc tỉnh nào?") nhưng đáp án vẫn đổi theo thời điểm hỏi — dạng "thời gian ngầm" mà TimeQA loại ra. Đây là một điểm định vị hay.
  - *Mượn được:* cách định nghĩa hình thức "câu nhạy thời gian" để viết mục Dữ liệu.
- **Tự kiểm tra khi đọc:** xem Bảng thống kê dữ liệu (số câu, số sự thật); xác nhận con số 46%/87% thuộc bản *hard*.

### B2. StreamingQA

- **Trích dẫn:** Adam Liška, Tomáš Kočiský, Elena Gribovskaya, Tayfun Terzi, Eren Sezener, Devang Agrawal, Cyprien de Masson d'Autume, Tim Scholtes, Manzil Zaheer, Susannah Young, Ellen Gilsenan-McMahon, Sophia Austin, Phil Blunsom, Angeliki Lazaridou. 2022. *StreamingQA: A Benchmark for Adaptation to New Knowledge over Time in Question Answering Models.* ICML 2022, PMLR 162:13604–13622.
- **Link:** [PMLR](https://proceedings.mlr.press/v162/liska22a.html) · [arXiv 2205.11388](https://arxiv.org/abs/2205.11388) · [slide](https://icml.cc/media/icml-2022/Slides/17994.pdf) · code: github.com/deepmind/streamingqa
- **Vấn đề:** QA thường được đánh giá trên ảnh chụp tĩnh của tri thức (ví dụ một bản Wikipedia), trong khi thế giới thay đổi và tri thức của mô hình lỗi thời dần.
- **Phương pháp:** bộ câu hỏi (người viết + sinh tự động, đều được người lọc) **gắn ngày đặt câu hỏi**, trả lời từ kho tin tức 14 năm có dấu thời gian. Mỗi quý thêm tin mới và đánh giá trên câu hỏi về sự kiện gần đây và cũ, để đo cả **thích nghi** lẫn **quên**. So sánh: mô hình đóng (closed-book) được fine-tune dần; mô hình mở (open-book) cập nhật chỉ mục tìm kiếm nhưng LM nền cũ; mô hình huấn luyện lại toàn bộ.
- **Kết quả chính:**
  - Mô hình tham số có thể cập nhật mà không cần huấn luyện lại toàn bộ, vẫn tránh được quên thảm họa.
  - Với mô hình bán tham số, thêm bài mới vào chỉ mục giúp thích nghi rất nhanh, **nhưng mô hình có LM nền lỗi thời vẫn kém hơn mô hình có LM được huấn luyện lại**.
  - Với thực thể xuất hiện nhiều, cập nhật tham số đặc biệt có lợi.
- **Hạn chế:** tiếng Anh; sự kiện tin tức độc lập nhau; mô hình thế hệ 2022.
- **Liên quan tới đề tài:**
  - *Giống:* đúng giả thuyết nền của mình — RAG giúp cập nhật nhưng "trí nhớ cũ" của LM vẫn kéo hiệu năng xuống. Kết quả "LM nền cũ vẫn kém" là **động lực trực tiếp cho PBER** (có tài liệu mới vẫn sai).
  - *Khác:* mình không fine-tune mô hình; mình đánh giá LLM thương mại/mở như hộp đen ở nhiều cấu hình ngữ cảnh. Mình có một **mốc thay đổi duy nhất** thay vì luồng tin liên tục.
  - *Mượn được:* ý "câu hỏi gắn ngày hỏi" → ghi rõ ngày chạy thực nghiệm cho mỗi mô hình trong file kết quả; phân tích theo tần suất thực thể (tỉnh lớn vs tỉnh nhỏ) — có thể thêm vào phân tích SR.
- **Tự kiểm tra khi đọc:** Hình về "temporal lag" (độ trễ tính theo quý); mục phân tích theo tần suất thực thể (Section 4.3).

### B3. FreshLLMs / FreshQA

- **Trích dẫn:** Tu Vu, Mohit Iyyer, Xuezhi Wang, Noah Constant, Jerry Wei, Jason Wei, Chris Tar, Yun-Hsuan Sung, Denny Zhou, Quoc Le, Thang Luong. 2024. *FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation.* Findings of ACL 2024, trang 13697–13720. (arXiv 2310.03214, 10/2023)
- **Link:** [ACL Anthology](https://aclanthology.org/2024.findings-acl.813) · [PDF](https://aclanthology.org/2024.findings-acl.813.pdf) · [BibTeX](https://aclanthology.org/2024.findings-acl.813.bib) · dữ liệu: github.com/freshllms/freshqa
- **Vấn đề:** hầu hết LLM được huấn luyện một lần rồi không cập nhật, nên kém với câu hỏi về thế giới hiện tại.
- **Phương pháp:**
  - **FreshQA**: benchmark động, câu hỏi chia theo loại: *never-changing*, *slow-changing*, *fast-changing*, và *false-premise* (tiền giả định sai, cần bác bỏ). Người viết câu được yêu cầu viết câu tự nhiên như gõ vào máy tìm kiếm; câu tiền giả định sai kèm giải thích ngắn. Tác giả cam kết cập nhật đáp án vàng định kỳ.
  - **Đánh giá 2 chế độ**: *relaxed* (chỉ chấm đáp án chính) và *strict* (đáp án chính đúng, rõ ràng **và** mọi thông tin phụ không được sai / không ảo giác). Hơn 50.000 phán đoán của người.
  - **FreshPrompt**: phương pháp few-shot đưa kết quả tìm kiếm (kèm ngày) vào prompt.
- **Kết quả chính:**
  - Mọi mô hình, bất kể kích thước, đều gặp khó với câu đổi nhanh và câu tiền giả định sai.
  - FreshPrompt vượt các phương pháp tìm kiếm-tăng cường khác (Self-Ask) và hệ thống thương mại như Perplexity.AI.
  - Số lượng và **thứ tự** bằng chứng truy xuất ảnh hưởng rõ tới độ đúng; yêu cầu trả lời ngắn gọn giúp giảm ảo giác.
- **Hạn chế:** tiếng Anh; câu hỏi trải rộng nhiều chủ đề, không có cấu trúc liên kết giữa các sự thật; không có câu đối chứng âm riêng cho nhóm tiền giả định sai **[kiểm tra]**; không tách lỗi truy xuất và lỗi không tin tài liệu.
- **Liên quan tới đề tài:**
  - *Giống:* (1) nhóm *false-premise* ↔ **nhóm B** ("Chủ tịch UBND huyện Gia Lâm là ai?"); (2) chế độ *strict* ↔ quy tắc "lời rào đón/thông tin phụ cũ không cứu được câu trả lời" và nhãn `BLENDED`; (3) câu *fast/slow-changing* ↔ toàn bộ benchmark của mình (thay đổi một lần nhưng diện rộng).
  - *Khác:* mình có **câu đối chứng âm** (B07) để đo Over-rejection — mô hình "thấy gì cũng bác". Mình tách lỗi trộn thành nhãn riêng thay vì gộp vào strict=sai.
  - *Mượn được:* FreshPrompt làm **baseline** cho cấu hình RAG; phát hiện "thứ tự bằng chứng ảnh hưởng" → thử đổi thứ tự tài liệu cũ/mới trong C3/C4; quy trình chấm hai chế độ để báo SR và SR⁺.
- **Tự kiểm tra khi đọc:** tỷ lệ từng loại câu trong FreshQA; định nghĩa chính xác strict/relaxed (mục Evaluation); có câu false-premise "đối chứng" hay không.

### B4. Longpre và cs. — Entity-Based Knowledge Conflicts

- **Trích dẫn:** Shayne Longpre, Kartik Perisetla, Anthony Chen, Nikhil Ramesh, Chris DuBois, Sameer Singh. 2021. *Entity-Based Knowledge Conflicts in Question Answering.* EMNLP 2021, trang 7052–7063.
- **Link:** [ACL Anthology](https://aclanthology.org/2021.emnlp-main.565) · [ar5iv HTML](https://ar5iv.labs.arxiv.org/html/2109.05052) · code: github.com/apple/ml-knowledge-conflicts
- **Vấn đề:** các tác vụ cần tri thức dùng hai nguồn — *tham số* (học lúc huấn luyện) và *ngữ cảnh* (đoạn văn lúc suy luận). Tác giả hình thức hóa bài toán **xung đột tri thức**: khi ngữ cảnh mâu thuẫn với điều đã học.
- **Phương pháp:**
  - Giới hạn ở xung đột dựa trên **thay thế thực thể có tên**: tìm câu QA có đáp án là thực thể (5 loại: người, ngày, số, tổ chức, địa điểm — dùng SpaCy NER + entity linking), rồi thay **mọi lần xuất hiện** của đáp án trong đoạn văn bằng thực thể khác → đáp án "đúng theo ngữ cảnh" đổi.
  - Nhiều chính sách thay thế: thay bằng thực thể cùng tập dữ liệu (corpus substitution), thay bằng thực thể vô lý (để thử độ bền), thay theo độ phổ biến (popularity substitution)…
  - Đo **mức phụ thuộc quá mức vào trí nhớ** (nguyên nhân ảo giác) và đề xuất cách giảm: huấn luyện với dữ liệu đã thay thế.
- **Kết quả chính:**
  - Các yếu tố làm tăng việc bám trí nhớ: kích thước mô hình, loại mô hình, chất lượng truy xuất lúc huấn luyện, độ tương đồng miền, đặc điểm đáp án.
  - Cách giảm thiểu giúp cải thiện khả năng tổng quát hóa ngoài phân phối khoảng 4–7%, và giúp mô hình tổng quát hóa tốt hơn với **thông tin thay đổi theo thời gian**.
- **Hạn chế:** mô hình QA thế hệ trước LLM; xung đột nhân tạo, có thể không giống xung đột thực tế.
- **Liên quan tới đề tài:**
  - *Giống:* khái niệm "hallucinate rather than read" (bịa từ trí nhớ thay vì đọc tài liệu) = đúng hiện tượng **PBER** đo; tác giả còn gợi ý chính ứng dụng "câu hỏi phụ thuộc thời gian".
  - *Khác:* xung đột của mình **có sẵn trong thế giới thật** — tài liệu (nghị quyết 2025) đúng, trí nhớ (dữ liệu huấn luyện trước 2025) sai. Không cần tạo thực thể giả.
  - *Mượn được:* phân loại thực thể (địa điểm/số/người) để phân tích lỗi; ý phân tích theo **độ phổ biến thực thể** (tỉnh nổi tiếng như Quảng Nam vs tỉnh ít được nhắc).
- **Tự kiểm tra khi đọc:** Hình 1 (ví dụ "Who did US fight in world war 1?"); bảng các chính sách thay thế; con số "memorization ratio".

### B5. Xie và cs. — Adaptive Chameleon or Stubborn Sloth

- **Trích dẫn:** Jian Xie, Kai Zhang, Jiangjie Chen, Renze Lou, Yu Su. 2024. *Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts.* ICLR 2024 (Spotlight). arXiv 2305.13300 (5/2023).
- **Link:** [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/99261adc8a6356b38bcf999bba9a26dc-Abstract-Conference.html) · [arXiv](https://arxiv.org/abs/2305.13300) · [OpenReview](https://openreview.net/forum?id=auKAUJZMO6) · code/dữ liệu: github.com/OSU-NLP-Group/LLM-Knowledge-Conflict
- **Vấn đề:** tăng cường công cụ/truy xuất được dùng để khắc phục trí nhớ tĩnh của LLM, nhưng LLM tiếp nhận bằng chứng ngoài đến đâu khi nó **trái** với trí nhớ?
- **Phương pháp:**
  - Bước 1: **gợi ra trí nhớ tham số** của từng LLM cho mỗi câu hỏi (câu trả lời + đoạn giải thích mô hình tự viết).
  - Bước 2: xây dựng **phản-trí nhớ** (counter-memory) — bằng chứng mạch lạc ủng hộ đáp án khác — bằng cách cho LLM sinh văn bản, thay vì chỉ thay thực thể như Longpre.
  - Thí nghiệm có kiểm soát: chỉ đưa phản-trí nhớ; đưa cả bằng chứng thuận và ngược; thay đổi độ phổ biến, thứ tự, số lượng bằng chứng. Dữ liệu dựa trên PopQA và StrategyQA (bộ conflictQA).
- **Kết quả chính (hai hành vi "có vẻ mâu thuẫn"):**
  - LLM **có thể rất dễ tiếp nhận** bằng chứng ngoài dù trái trí nhớ, *nếu* bằng chứng mạch lạc, thuyết phục (trái với nhận định trước đó là LLM "cứng đầu"). Phản-trí nhớ sinh bằng LLM thuyết phục hơn hẳn phản-trí nhớ tạo bằng thay thực thể.
  - Nhưng khi bằng chứng ngoài có **một phần khớp với trí nhớ**, LLM thể hiện **thiên kiến xác nhận** mạnh — nghiêng về phía giống trí nhớ dù có bằng chứng ngược đi kèm.
- **Hạn chế:** phản-trí nhớ vẫn là văn bản sinh nhân tạo; tiếng Anh.
- **Liên quan tới đề tài:**
  - *Giống:* phát hiện "thiên kiến xác nhận" dự đoán chính xác rủi ro ở cấu hình **kho tài liệu trộn** (văn bản trước và sau 01/07/2025 cùng nằm trong top-k). Đây là **giả thuyết H** có thể kiểm chứng ở Tuần 4–5: PBER ở cấu hình trộn > PBER ở cấu hình chỉ tài liệu mới.
  - *Khác:* "phản-trí nhớ" của mình là **văn bản pháp lý thật** (nghị quyết), không do LLM sinh; trí nhớ của mô hình là **sai** chứ không phải chỉ "khác".
  - *Mượn được:* quy trình "gợi trí nhớ trước" ↔ cấu hình **C0 closed-book** của mình đóng vai trò đúng bước này; KOR tính trên các câu STALE ở C0 chính là "câu mà trí nhớ đã được xác nhận là lỗi thời".
- **Tự kiểm tra khi đọc:** Hình 1 (khung thí nghiệm); bảng kết quả khi đưa cả hai loại bằng chứng; phân tích theo thứ tự bằng chứng.

### B6. ClashEval ⭐ (bài quan trọng nhất)

- **Trích dẫn:** Kevin Wu, Eric Wu, James Zou. 2024. *ClashEval: Quantifying the Tug-of-War between an LLM's Internal Prior and External Evidence.* NeurIPS 2024 Datasets and Benchmarks Track. arXiv 2404.10198.
- **Link:** [NeurIPS PDF](https://proceedings.nips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf) · [arXiv HTML](https://arxiv.org/html/2404.10198v2) · [trang NeurIPS](https://neurips.cc/virtual/2024/poster/97658) · code: github.com/kevinwu23/StanfordClashEval
- **Vấn đề:** RAG được dùng để giảm ảo giác và cập nhật kiến thức, nhưng truy xuất không hoàn hảo. Hai câu hỏi: (1) khi tài liệu **sai**, mô hình có biết bỏ qua không hay lặp lại lỗi? (2) khi trí nhớ của mô hình **sai**, mô hình có dùng tài liệu đúng để tự sửa không, hay khăng khăng giữ đáp án cũ?
- **Phương pháp:**
  - Hơn 1.200 câu hỏi thuộc 6 lĩnh vực (liều thuốc, kỷ lục thể thao/Olympic, địa điểm, tên, tin tức, …), mỗi câu kèm tài liệu liên quan.
  - **Làm nhiễu chính xác** đáp án trong tài liệu theo nhiều mức, từ sai lệch tinh vi đến lộ liễu.
  - Thử 6 LLM: GPT-4o, GPT-3.5, Llama-3-8b-instruct, Gemini 1.5, Claude Opus, Claude Sonnet; dùng prompt RAG chuẩn (LangChain, LlamaIndex) và biến thể "strict"/"loose".
  - Ký hiệu: r(q) là câu trả lời chỉ dùng trí nhớ (prior); so với câu trả lời khi có ngữ cảnh.
  - **Ba độ đo:** *Accuracy*; *Prior bias* — mô hình giữ trí nhớ sai dù tài liệu đúng; *Context bias* — mô hình bỏ trí nhớ đúng để theo tài liệu sai.
- **Kết quả chính:**
  - LLM dễ chấp nhận nội dung truy xuất sai, bỏ trí nhớ đúng của mình **hơn 60%** số trường hợp.
  - Nội dung càng phi thực tế (lệch xa sự thật) thì mô hình càng ít chấp nhận.
  - Xác suất token của câu trả lời prior liên quan tới xu hướng chọn prior hay context; tác giả đề xuất cách đơn giản dựa trên xác suất token để cải thiện độ đúng.
  - Mô hình mạnh về tổng thể chưa chắc phân xử xung đột tốt **[kiểm tra con số cụ thể theo mô hình trong bảng kết quả — chỉ mới thấy qua bài tóm tắt thứ cấp]**.
- **Hạn chế (quan trọng để định vị):**
  - Xung đột **nhân tạo**: tài liệu bị sửa sai có chủ đích; trí nhớ của mô hình thường đúng.
  - Không có trường hợp "câu trả lời trộn" — chỉ phân loại theo prior hay context.
  - Không tách được lỗi do truy xuất (vì tài liệu luôn được đưa sẵn).
- **Liên quan tới đề tài — so sánh trực tiếp:**

| | ClashEval | VN-Admin2025-QA |
|---|---|---|
| Nguồn xung đột | Tài liệu bị **làm nhiễu** nhân tạo | Trí nhớ **lỗi thời thật** sau cải cách 01/07/2025 |
| Bên nào sai | Thường là tài liệu | Luôn là trí nhớ (với câu bẫy) |
| Độ đo gần nhất | Prior bias | **PBER** (có Eᵢ trong ngữ cảnh mà vẫn STALE/BLENDED) |
| Đo khả năng tự sửa | Gián tiếp | **KOR** (STALE ở C0 → CORRECT_CURRENT ở cấu hình k) |
| Câu trả lời trộn cũ–mới | Không có | Nhãn **`BLENDED`**, SR⁺ |
| Lỗi do truy xuất | Không đo (tài liệu đưa sẵn) | **Recall@k / MRR** tách riêng; C5 oracle tương đương "đưa sẵn" |
| Ngôn ngữ | Tiếng Anh | Tiếng Việt |

  - *Mượn được:* cấu hình **C5 oracle** của mình tương ứng với thiết lập của ClashEval → có thể so sánh định tính PBER(C5) với prior bias; ý tưởng dùng **xác suất token / độ tự tin** với mô hình mở để giải thích PBER (hướng mở rộng).
- **Câu phải có trong bài:** "PBER gần với *prior bias* của ClashEval (Wu và cs., 2024), nhưng khác ở chỗ trí nhớ sai của mô hình xuất phát từ thay đổi thực tế chứ không do làm nhiễu tài liệu, và PBER chỉ được tính trên các câu mà bằng chứng đúng đã có trong ngữ cảnh, tách biệt với lỗi truy xuất."
- **Tự kiểm tra khi đọc:** định nghĩa toán học chính xác của prior bias và context bias (mục Methods) — đặt cạnh công thức PBER mục 5.5 `metrics_spec.md`; Hình về quan hệ giữa mức nhiễu và tỷ lệ theo context.

### B7. Xu và cs. — Knowledge Conflicts for LLMs: A Survey

- **Trích dẫn:** Rongwu Xu, Zehan Qi, Zhijiang Guo, Cunxiang Wang, Hongru Wang, Yue Zhang, Wei Xu. 2024. *Knowledge Conflicts for LLMs: A Survey.* EMNLP 2024, trang 8541–8565.
- **Link:** [ACL Anthology](https://aclanthology.org/2024.emnlp-main.486) · [arXiv HTML](https://arxiv.org/html/2403.08319)
- **Vấn đề:** xung đột tri thức ảnh hưởng tới độ tin cậy và hiệu năng của LLM, nhất là khi ngoài thực tế có nhiều nhiễu và thông tin sai; trước bài này chưa có tổng quan hệ thống riêng cho chủ đề.
- **Nội dung chính:**
  - **3 loại xung đột:**
    - *Context–memory*: ngữ cảnh ↔ trí nhớ tham số.
    - *Inter-context*: giữa các đoạn ngữ cảnh với nhau (ví dụ tài liệu truy xuất mâu thuẫn nhau).
    - *Intra-memory*: mâu thuẫn bên trong trí nhớ của chính mô hình (trả lời không nhất quán khi hỏi khác đi).
  - Với mỗi loại: nguyên nhân → hành vi của mô hình → giải pháp.
  - Giải pháp được nhóm theo mục tiêu: trung thành với ngữ cảnh, phân biệt thông tin sai, tách bạch nguồn, cải thiện tính đúng sự thật.
  - Một nguyên nhân được nhắc cho context–memory: **thông tin lỗi thời theo thời gian (temporal misalignment)** **[kiểm tra mục 2.1]**.
- **Liên quan tới đề tài — ánh xạ thuật ngữ:**

| Hiện tượng trong đề tài | Loại xung đột (Xu và cs.) |
|---|---|
| C4/C5: tài liệu mới ↔ trí nhớ cũ | Context–memory |
| Kho tài liệu chứa cả văn bản trước và sau 01/07/2025 | Inter-context |
| Câu trả lời tự mâu thuẫn (ca C04 – DeepSeek), `BLENDED` ở C0 | Intra-memory |

  - *Mượn được:* dùng đúng 3 thuật ngữ này trong bài để giám khảo thấy nhóm nắm bức tranh chung; một câu trích dẫn là đủ.
- **Tự kiểm tra khi đọc:** chỉ cần Hình 1–2 (sơ đồ phân loại) và mục 2 (context–memory). Không cần đọc hết.

### B8. RAGAs

- **Trích dẫn:** Shahul Es, Jithin James, Luis Espinosa Anke, Steven Schockaert. 2024. *RAGAs: Automated Evaluation of Retrieval Augmented Generation.* EACL 2024 System Demonstrations, trang 150–158. (arXiv 2309.15217, 9/2023)
- **Link:** [ACL Anthology](https://aclanthology.org/2024.eacl-demo.16) · [arXiv PDF](https://arxiv.org/pdf/2309.15217) · code: github.com/explodinggradients/ragas
- **Vấn đề:** đánh giá RAG khó vì có nhiều chiều: hệ truy xuất có tìm được đoạn văn liên quan, tập trung không; LLM có khai thác đoạn văn **trung thực** không; chất lượng câu trả lời ra sao. Các cách cũ (perplexity, QA trích xuất ngắn) không phản ánh cách dùng thực tế; xác suất token không lấy được với mô hình đóng.
- **Phương pháp:** bộ độ đo **không cần nhãn người / đáp án vàng**, dùng LLM để ước lượng:
  - *Faithfulness*: các khẳng định trong câu trả lời có suy ra được từ ngữ cảnh không.
  - *Answer relevance*: câu trả lời có đúng trọng tâm câu hỏi không.
  - *Context relevance*: ngữ cảnh truy xuất có tập trung, ít thông tin thừa không.
  - Tích hợp với LlamaIndex và LangChain.
- **Hạn chế:** dựa trên vài prompt viết tay cố định (ARES chỉ trích điểm này); không có đáp án vàng nên **không biết câu trả lời có đúng sự thật hay không**, chỉ biết có bám ngữ cảnh.
- **Liên quan tới đề tài:**
  - *Ví dụ minh họa hạn chế (đưa vào bài):* câu C03, truy xuất trúng một bài báo năm 2024 ghi "Hội An thuộc tỉnh Quảng Nam"; mô hình trả lời "Hội An thuộc tỉnh Quảng Nam" → **faithfulness cao**, nhưng theo hệ nhãn của mình là `STALE`. Vì vậy cần độ đo **có nhận thức về thời gian**.
  - *Mượn được:* dùng faithfulness làm độ đo phụ ở Tuần 3–5 để phân tích: STALE do *không trung thành với tài liệu mới* (PBER) hay do *trung thành với tài liệu cũ* (lỗi truy xuất/kho).
- **Tự kiểm tra khi đọc:** mục 3 (Evaluation Strategies) — công thức từng độ đo.

### B9. ARES

- **Trích dẫn:** Jon Saad-Falcon, Omar Khattab, Christopher Potts, Matei Zaharia. 2024. *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems.* NAACL 2024 (Long Papers), trang 338–354. (arXiv 2311.09476, 11/2023)
- **Link:** [ACL Anthology](https://aclanthology.org/2024.naacl-long.20) · [arXiv HTML](https://arxiv.org/html/2311.09476v2) · code: github.com/stanford-futuredata/ARES
- **Vấn đề:** đánh giá RAG truyền thống cần nhiều nhãn tay; các bộ chấm dựa trên mô hình (RAGAS) dùng prompt viết tay cố định nên khó thích nghi và không đảm bảo chất lượng.
- **Phương pháp:**
  - Đầu vào: kho đoạn văn trong miền, một **tập kiểm định nhãn người khoảng 150 điểm dữ liệu trở lên**, và vài ví dụ.
  - Sinh dữ liệu huấn luyện tổng hợp (câu hỏi–đoạn văn–câu trả lời), fine-tune **bộ chấm LM nhỏ** cho 3 chiều: context relevance, answer faithfulness, answer relevance.
  - Dùng **prediction-powered inference (PPI)** kết hợp tập nhãn người nhỏ để hiệu chỉnh điểm và đưa ra **khoảng tin cậy thống kê**.
- **Kết quả chính:** trên 6 tác vụ thuộc KILT và SuperGLUE, ARES chấm chính xác hơn RAGAS (cao hơn khoảng 59,3 và 14,4 điểm phần trăm ở context relevance và answer relevance); bộ chấm vẫn hiệu quả khi đổi miền; cần ít nhãn người hơn đáng kể so với đánh giá thuần thủ công.
- **Hạn chế:** vẫn đo bám ngữ cảnh / liên quan, không đo tính hiện hành; cần fine-tune bộ chấm (tốn công với nhóm sinh viên).
- **Liên quan tới đề tài:**
  - *Giống về phương pháp luận:* "bộ chấm tự động + tập nhãn người nhỏ để kiểm định + khoảng tin cậy" ↔ kế hoạch của mình: bộ chấm luật + LLM, kiểm tra κ với 300 câu nhãn người (mục 7 spec), bootstrap 95% (mục 6 spec).
  - *Khác:* mình không fine-tune bộ chấm; bộ chấm của mình gán **5 nhãn có ngữ nghĩa thời gian**, không phải điểm liên quan.
  - *Mượn được:* trích ARES để biện minh cỡ tập kiểm định nhãn người (300 câu của mình > ~150 của ARES); có thể nhắc PPI như hướng cải tiến ước lượng SR từ bộ chấm tự động.
- **Tự kiểm tra khi đọc:** Hình 1 (3 giai đoạn ARES); mục PPI — chỉ cần hiểu ý tưởng, không cần công thức.

---

## C. Định vị đề tài

### C.1 Bảng so sánh

| Tiêu chí | TimeQA | StreamingQA | FreshQA | Longpre / Xie | ClashEval | RAGAS / ARES | **VN-Admin2025-QA** |
|---|---|---|---|---|---|---|---|
| Đối tượng chính | Suy luận thời gian | Thích nghi kiến thức mới | Tính cập nhật của LLM | Xung đột trí nhớ–ngữ cảnh | Xung đột trong RAG | Chất lượng RAG | **Lỗi thời sau cải cách hành chính** |
| Tiếng Việt | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| Thời gian ngầm (câu không chứa mốc thời gian) | ✗ | ✓ | ✓ | — | — | — | **✓** |
| Một mốc thay đổi áp dụng cho cả hệ thống | ✗ | ✗ | ✗ | ✗ | ✗ | — | **✓** (01/07/2025) |
| Xung đột tự nhiên (không do người tạo) | — | ✓ | ✓ | ✗ | ✗ | — | **✓** |
| Câu tiền giả định sai | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | **✓** (nhóm B) |
| Câu đối chứng âm cho tiền giả định | ✗ | ✗ | ✗ [kiểm tra] | ✗ | ✗ | ✗ | **✓** (B07, Over-rejection) |
| Nhãn trộn cũ–mới | ✗ | ✗ | một phần (strict) | ✗ | ✗ | ✗ | **✓** (`BLENDED`) |
| Tách lỗi truy xuất vs lỗi không tin tài liệu | ✗ | một phần | ✗ | — | ✗ | một phần | **✓** (Recall@k vs PBER) |
| Suy luận nhiều bước sau thay đổi | ✓ (thời gian) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** (nhóm C) |

### C.2 Ba khoảng trống

1. **Thiếu benchmark về một thay đổi cấu trúc diện rộng, có mốc hiệu lực rõ ràng.** Các benchmark thời gian hiện có (TimeQA, StreamingQA, FreshQA) gồm những sự thật/sự kiện rời rạc, chủ yếu tiếng Anh. Cải cách hành chính Việt Nam 01/07/2025 (63 → 34 tỉnh, bỏ cấp huyện) làm **hàng trăm sự thật liên kết với nhau đổi cùng lúc**, kéo theo câu tiền giả định sai (đơn vị cấp huyện không còn) và câu suy luận nhiều bước.
2. **Xung đột tri thức chủ yếu được nghiên cứu bằng dữ liệu nhân tạo.** Longpre và cs., Xie và cs., ClashEval đều tạo xung đột bằng cách thay thế thực thể, sinh phản-trí nhớ hoặc làm nhiễu tài liệu. Trong các thiết lập đó, phía sai thường là tài liệu. Trường hợp ngược lại — **tài liệu đúng nhưng trí nhớ lỗi thời thật** — chưa được đo trực tiếp trên dữ liệu tự nhiên.
3. **Các khung đánh giá RAG không đo tính hiện hành.** RAGAS và ARES đo mức bám ngữ cảnh; nếu hệ thống truy xuất trúng văn bản đã hết hiệu lực, câu trả lời vẫn được chấm cao. Đồng thời, các nghiên cứu RAG thường gộp hai nguyên nhân thất bại: **không tìm được** tài liệu đúng và **tìm được nhưng không tin**.

### C.3 Đóng góp tương ứng (để nối sang mục Giới thiệu/Phương pháp)

| Khoảng trống | Đóng góp của đề tài |
|---|---|
| 1 | Bộ VN-Admin2025-QA: 4 nhóm câu (A tra cứu, B bẫy tiền giả định, C nhiều bước, D trước/sau) + câu đối chứng |
| 2 | Đo xung đột tự nhiên bằng **KOR** và **PBER** trên chuỗi cấu hình C0–C5 |
| 3 | Hệ nhãn 5 lớp có ngữ nghĩa thời gian (`STALE`, `BLENDED`…), độ đo **SR/SR⁺**, tách **Recall@k** với **PBER** |

---

## D. Bản nháp văn xuôi mục 3

> Độ dài khoảng 1,5 trang. Văn phong học thuật, ngôi "chúng tôi". Sửa xong thì xóa các ghi chú trong ngoặc vuông.

### 3. Tổng quan tài liệu

Nghiên cứu của chúng tôi liên quan tới ba hướng: hỏi đáp có yếu tố thời gian, xung đột giữa tri thức tham số và ngữ cảnh, và đánh giá hệ thống sinh văn bản tăng cường truy xuất (RAG).

**3.1 Hỏi đáp có yếu tố thời gian.** Tri thức của mô hình ngôn ngữ dừng lại tại thời điểm cắt dữ liệu huấn luyện, trong khi nhiều sự thật thay đổi theo thời gian. Chen và cs. (2021) xây dựng TimeQA từ các sự thật biến đổi trong WikiData và định nghĩa câu hỏi nhạy thời gian là câu chứa cụm chỉ thời gian mà khi thay đổi cụm này thì đáp án thay đổi; mô hình đọc hiểu tốt nhất khi đó chỉ đạt khoảng 46% so với 87% của con người. Liška và cs. (2022) đề xuất StreamingQA, trong đó mỗi câu hỏi gắn với ngày đặt câu hỏi và được trả lời từ kho tin tức có dấu thời gian; kết quả cho thấy cập nhật chỉ mục truy xuất giúp mô hình thích nghi nhanh, nhưng mô hình có mô hình ngôn ngữ nền lỗi thời vẫn kém hơn mô hình được huấn luyện lại. Với các mô hình ngôn ngữ lớn (LLM), Vu và cs. (2024) giới thiệu FreshQA gồm câu hỏi có đáp án không đổi, đổi chậm, đổi nhanh và câu chứa tiền giả định sai, chấm theo hai chế độ nới lỏng và nghiêm ngặt; mọi mô hình, bất kể kích thước, đều gặp khó với câu đổi nhanh và câu có tiền giả định sai. Các bộ dữ liệu này chủ yếu bằng tiếng Anh và gồm các sự kiện độc lập. Khác với chúng, chúng tôi nghiên cứu một *thay đổi cấu trúc diện rộng có mốc hiệu lực xác định* — đợt sắp xếp đơn vị hành chính của Việt Nam có hiệu lực từ ngày 01/07/2025 — khiến hàng trăm sự thật có liên kết với nhau thay đổi đồng thời, và phần lớn câu hỏi không chứa mốc thời gian tường minh.

**3.2 Xung đột giữa tri thức tham số và ngữ cảnh.** Xu và cs. (2024) phân loại xung đột tri thức của LLM thành ba dạng: giữa ngữ cảnh và trí nhớ (context–memory), giữa các ngữ cảnh với nhau (inter-context) và bên trong trí nhớ (intra-memory). Longpre và cs. (2021) tạo xung đột ngữ cảnh–trí nhớ bằng cách thay thực thể đáp án trong đoạn văn và cho thấy các mô hình hỏi đáp có xu hướng dựa quá mức vào thông tin đã ghi nhớ, dẫn tới ảo giác. Xie và cs. (2024) phát hiện LLM có thể tiếp nhận bằng chứng trái với trí nhớ nếu bằng chứng đủ mạch lạc, nhưng lại thể hiện thiên kiến xác nhận rõ rệt khi bằng chứng có một phần trùng với trí nhớ. Gần với chúng tôi nhất, ClashEval (Wu và cs., 2024) làm nhiễu đáp án trong tài liệu ở nhiều mức độ và đo hai xu hướng: thiên về trí nhớ (*prior bias*) và thiên về ngữ cảnh (*context bias*); các LLM được thử nghiệm bỏ trí nhớ đúng để theo tài liệu sai trong hơn 60% trường hợp. Điểm chung của các công trình trên là xung đột được *tạo nhân tạo*, và phía sai thường là tài liệu. Trong nghiên cứu này, xung đột là *tự nhiên*: tài liệu phản ánh đúng quy định hiện hành, còn trí nhớ của mô hình đã lỗi thời. Độ đo PBER của chúng tôi gần với *prior bias* của ClashEval nhưng chỉ được tính trên các câu mà bằng chứng đúng đã có trong ngữ cảnh, nhờ đó tách biệt lỗi "không tìm được tài liệu" (đo bằng Recall@k) với lỗi "tìm được nhưng không tin tài liệu". Theo cách phân loại của Xu và cs. (2024), cấu hình có tài liệu đúng thuộc dạng context–memory, còn kho tài liệu chứa cả văn bản trước và sau cải cách tạo thêm xung đột inter-context — tình huống mà phát hiện của Xie và cs. (2024) dự báo có thể kéo mô hình về đáp án cũ.

**3.3 Đánh giá hệ thống RAG.** RAGAs (Es và cs., 2024) đề xuất bộ độ đo không cần đáp án vàng, dùng LLM để ước lượng mức trung thực của câu trả lời với ngữ cảnh, mức liên quan của câu trả lời và của ngữ cảnh. ARES (Saad-Falcon và cs., 2024) huấn luyện các bộ chấm nhỏ cho từng thành phần và kết hợp một tập nhãn người nhỏ với suy luận có hỗ trợ dự đoán (prediction-powered inference) để đưa ra khoảng tin cậy. Cả hai đo việc câu trả lời có *bám sát ngữ cảnh* hay không, nhưng không đo câu trả lời có *đúng tại thời điểm hiện tại* hay không: nếu hệ thống truy xuất trúng một văn bản trước năm 2025 ghi "Hội An thuộc tỉnh Quảng Nam" và mô hình lặp lại thông tin này, câu trả lời vẫn được đánh giá là trung thực. Vì vậy, chúng tôi xây dựng hệ nhãn năm lớp có ngữ nghĩa thời gian (`CORRECT_CURRENT`, `STALE`, `BLENDED`, `OTHER_ERROR`, `ABSTAIN`) cùng các độ đo Staleness Rate, Knowledge Override Rate và Prior Bias Error Rate. Tương tự ARES, bộ chấm tự động của chúng tôi được kiểm định với nhãn người, ở đây bằng hệ số đồng thuận Cohen's κ trên 300 câu.

**3.4 Vị trí của nghiên cứu.** Bảng 1 so sánh VN-Admin2025-QA với các công trình liên quan. [Chèn bảng C.1, có thể rút gọn còn 5–6 tiêu chí.] Theo hiểu biết của chúng tôi, đây là benchmark đầu tiên đo tính lỗi thời của LLM đối với một thay đổi hành chính diện rộng bằng tiếng Việt, đồng thời tách biệt lỗi truy xuất với lỗi bám trí nhớ trong RAG trên xung đột tri thức tự nhiên. [Trước khi viết câu "đầu tiên", nhóm tìm thêm trên Google Scholar / arXiv với từ khóa "Vietnam administrative 2025 LLM", "Vietnamese temporal QA" để chắc chắn.]

---

## E. Câu hỏi giám khảo có thể hỏi

| Câu hỏi | Gợi ý trả lời |
|---|---|
| "PBER khác gì prior bias của ClashEval?" | Cùng ý tưởng "có tài liệu đúng mà vẫn bám trí nhớ", nhưng (1) trí nhớ sai do lỗi thời thật, không do làm nhiễu; (2) PBER chỉ tính khi bằng chứng vàng có trong ngữ cảnh, nên tách được lỗi truy xuất; (3) PBER tính cả `BLENDED`. |
| "FreshQA đã có câu tiền giả định sai rồi, nhóm B có gì mới?" | Nhóm B gắn với **một thay đổi cấu trúc cụ thể** (bỏ cấp huyện) và có **câu đối chứng âm** để đo Over-rejection — mô hình có thể "đúng" vì bác mọi thứ. Có quy tắc chấm riêng cho trường hợp từ chối nhưng vẫn chấp nhận tiền giả định (→ STALE). |
| "Sao không dùng RAGAS cho nhanh?" | RAGAS không có đáp án vàng nên không phân biệt được "trung thành với văn bản cũ" và "đúng hiện hành"; ví dụ C03. Có thể dùng RAGAS faithfulness làm độ đo phụ để chẩn đoán. |
| "Xung đột tự nhiên thì có gì khác nhân tạo?" | Văn bản nhân tạo có thể lộ dấu hiệu bất thường; Xie và cs. cho thấy mức độ mạch lạc ảnh hưởng mạnh tới việc mô hình tin; ClashEval cho thấy mức lệch càng lớn mô hình càng ít tin. Xung đột tự nhiên (nghị quyết thật, thay đổi hợp lý) có thể cho hành vi khác — đó là câu hỏi thực nghiệm. |
| "Tại sao chỉ 9 bài?" | 9 bài nền theo 3 hướng; bổ sung thêm các bài ở mục F.2 khi viết bản cuối (RAG gốc của Lewis và cs., các bài QA tiếng Việt). |

---

## F. Tài liệu tham khảo

### F.1 Chín bài nền (đã đối chiếu)

> Lấy BibTeX chính thức từ link, không gõ tay.

1. Wenhu Chen, Xinyi Wang, and William Yang Wang. 2021. A Dataset for Answering Time-Sensitive Questions. In *Proceedings of the Neural Information Processing Systems Track on Datasets and Benchmarks*. — BibTeX: https://dblp.org/rec/conf/nips/ChenWWW21
2. Shahul Es, Jithin James, Luis Espinosa Anke, and Steven Schockaert. 2024. RAGAs: Automated Evaluation of Retrieval Augmented Generation. In *Proceedings of the 18th Conference of the European Chapter of the ACL: System Demonstrations*, pages 150–158, St. Julian's, Malta. — https://aclanthology.org/2024.eacl-demo.16
3. Adam Liška, Tomáš Kočiský, Elena Gribovskaya, Tayfun Terzi, Eren Sezener, Devang Agrawal, Cyprien de Masson d'Autume, Tim Scholtes, Manzil Zaheer, Susannah Young, Ellen Gilsenan-McMahon, Sophia Austin, Phil Blunsom, and Angeliki Lazaridou. 2022. StreamingQA: A Benchmark for Adaptation to New Knowledge over Time in Question Answering Models. In *Proceedings of the 39th International Conference on Machine Learning*, PMLR 162:13604–13622. — https://proceedings.mlr.press/v162/liska22a.html
4. Shayne Longpre, Kartik Perisetla, Anthony Chen, Nikhil Ramesh, Chris DuBois, and Sameer Singh. 2021. Entity-Based Knowledge Conflicts in Question Answering. In *Proceedings of EMNLP 2021*, pages 7052–7063, Online and Punta Cana, Dominican Republic. — https://aclanthology.org/2021.emnlp-main.565
5. Jon Saad-Falcon, Omar Khattab, Christopher Potts, and Matei Zaharia. 2024. ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. In *Proceedings of NAACL 2024 (Volume 1: Long Papers)*, pages 338–354, Mexico City, Mexico. — https://aclanthology.org/2024.naacl-long.20
6. Tu Vu, Mohit Iyyer, Xuezhi Wang, Noah Constant, Jerry Wei, Jason Wei, Chris Tar, Yun-Hsuan Sung, Denny Zhou, Quoc Le, and Thang Luong. 2024. FreshLLMs: Refreshing Large Language Models with Search Engine Augmentation. In *Findings of the ACL: ACL 2024*, pages 13697–13720, Bangkok, Thailand. — https://aclanthology.org/2024.findings-acl.813
7. Kevin Wu, Eric Wu, and James Zou. 2024. ClashEval: Quantifying the Tug-of-War between an LLM's Internal Prior and External Evidence. In *Advances in Neural Information Processing Systems 37 (Datasets and Benchmarks Track)*. — https://proceedings.nips.cc/paper_files/paper/2024/file/3aa291abc426d7a29fb08418c1244177-Paper-Datasets_and_Benchmarks_Track.pdf
8. Jian Xie, Kai Zhang, Jiangjie Chen, Renze Lou, and Yu Su. 2024. Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts. In *The Twelfth International Conference on Learning Representations (ICLR)*. — https://openreview.net/forum?id=auKAUJZMO6
9. Rongwu Xu, Zehan Qi, Zhijiang Guo, Cunxiang Wang, Hongru Wang, Yue Zhang, and Wei Xu. 2024. Knowledge Conflicts for LLMs: A Survey. In *Proceedings of EMNLP 2024*, pages 8541–8565, Miami, Florida, USA. — https://aclanthology.org/2024.emnlp-main.486

### F.2 Đọc thêm khi viết bản cuối [kiểm tra toàn bộ thông tin trước khi dùng]

| Bài | Dùng cho |
|---|---|
| Lewis và cs. (2020) — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, NeurIPS | Trích dẫn gốc của RAG (bắt buộc có) |
| Dhingra và cs. (2022) — Time-Aware Language Models as Temporal Knowledge Bases (TempLAMA), TACL | Tri thức tham số gắn thời điểm |
| Zhang & Choi (2021) — SituatedQA, EMNLP | Đáp án phụ thuộc ngữ cảnh thời gian/địa lý |
| Yu và cs. (2023) — CREPE; Kim và cs. (2023) — (QA)² | Câu hỏi tiền giả định sai (nhóm B) |
| Zhong và cs. (2023) — MQuAKE, EMNLP | Cập nhật tri thức nhiều bước (nhóm C) |
| Bui và cs. (2025) — VMLU Benchmarks, ACL (đã thấy trên ACL Anthology) | Benchmark LLM tiếng Việt |
| Cohen (1960); Efron & Tibshirani (1993); McNemar (1947); Holm (1979) | Phương pháp thống kê trong `metrics_spec.md` (đưa vào mục Phương pháp, không phải mục 3) |

---

## G. Checklist khi đọc lại

- [ ] Đọc B6 (ClashEval) đầu tiên; đặt định nghĩa prior bias cạnh công thức PBER và sửa câu phân biệt ở phần D nếu cần.
- [ ] Với mỗi thẻ B1–B9: làm mục "Tự kiểm tra khi đọc", xóa nhãn **[kiểm tra]** khi đã xác nhận.
- [ ] Kiểm tra các ô "✗ [kiểm tra]" trong bảng C.1, đặc biệt FreshQA có câu đối chứng âm hay không.
- [ ] Tìm kiếm xem đã có bài nào về LLM và cải cách hành chính Việt Nam 2025 chưa, trước khi viết "đầu tiên".
- [ ] Tải BibTeX chính thức của 9 bài vào `paper/refs.bib`.
- [ ] Viết lại phần D bằng lời của mình, rút gọn theo giới hạn trang.

---

## Lịch sử thay đổi

| Phiên bản | Ngày | Người sửa | Nội dung |
|---|---|---|---|
| v0.1 | 14/11/2026 | TV3 (Claude hỗ trợ) | Bảng 9 bài, bảng định vị, bản nháp văn xuôi ngắn |
| v0.2 | 14/11/2026 | TV3 (Claude hỗ trợ) | Thêm thẻ đọc chi tiết từng bài, so sánh ClashEval–PBER, ánh xạ thuật ngữ Xu và cs., câu hỏi giám khảo, danh mục tham khảo đã đối chiếu, checklist |
