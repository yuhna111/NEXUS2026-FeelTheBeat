# Đặc tả độ đo (plan §1.4)

Ký hiệu: với câu *i*, ŷᵢ là dự đoán đã chuẩn hóa, Gᵢ là tập đáp án vàng (kèm bí danh), Oᵢ là tập thực thể lỗi thời, N là số câu.

**Chuẩn hóa** (`eval/normalize.py`): chữ thường, Unicode NFC, bỏ tiền tố ("tỉnh", "thành phố", "TP.", "phường", "xã"…), ánh xạ bí danh.

| Độ đo | Công thức | Hàm |
|-------|-----------|-----|
| EM | (1/N) Σ 𝟙[ŷᵢ ∈ Gᵢ] | `exact_match` |
| F1 (token / tập) | 2PR/(P+R) | `token_f1`, `set_f1` |
| Staleness Rate | (1/N) Σ 𝟙[Ent(ŷᵢ) ∩ Oᵢ ≠ ∅ ∧ asserted_current(ŷᵢ)] | `staleness_rate` |
| KORₖ | \|stale_C0 ∧ correctₖ\| / \|stale_C0\| | `knowledge_override_rate` |
| PBERₖ | \|gold_in_ctxₖ ∧ staleₖ\| / \|gold_in_ctxₖ\| | `prior_bias_error_rate` |
| Recall@k | (1/N) Σ 𝟙[Eᵢ ∩ Topₖ(qᵢ) ≠ ∅] | `recall_at_k` |
| MRR | (1/N) Σ 1/rankᵢ | `mrr` |

Báo cáo thêm **Blending Rate** và **Over-rejection Rate** (trên câu đối chứng âm nhóm B).

## LLM-as-a-Judge

Mô hình chấm khác mọi mô hình được đánh giá. 5 nhãn: `CORRECT_CURRENT`, `STALE`, `BLENDED`, `OTHER_ERROR`, `ABSTAIN`.
Luật chạy trước (`eval/staleness_rules.py`), bộ chấm LLM chỉ xử lý ca luật không quyết được.
Kiểm chứng: TV1 + TV3 gán nhãn tay 300 câu phân tầng; Cohen's κ (người–người, bộ chấm–người), mục tiêu κ ≥ 0,75.

## Thống kê

Paired bootstrap 1.000 mẫu, Holm–Bonferroni, CI 95% cho mọi con số. McNemar (H1b), hồi quy logistic SR ~ cutoff + size + family (RQ1), Spearman ρ PBER vs độ phổ biến (RQ3).
