# Recall@5 trên bộ pilot (TV2)

## Bộ `pilot_v0.3` (61 câu)

| Truy xuất | Chia cố định | Chia theo Điều–Khoản |
|---|---|---|
| bm25 | 0.443 (27/61) · MRR 0.313 | 0.557 (34/61) · MRR 0.420 |
| dense | 0.557 (34/61) · MRR 0.419 | 0.820 (50/61) · MRR 0.741 |
| hybrid | 0.689 (42/61) · MRR 0.476 | 0.754 (46/61) · MRR 0.626 |
| hybrid_rerank | 0.770 (47/61) · MRR 0.651 | 0.853 (52/61) · MRR 0.836 |

## Bộ `pilot_v0.2` (55 câu)

| Truy xuất | Chia cố định | Chia theo Điều–Khoản |
|---|---|---|
| bm25 | 0.418 (23/55) · MRR 0.284 | 0.582 (32/55) · MRR 0.429 |
| dense | 0.545 (30/55) · MRR 0.392 | 0.800 (44/55) · MRR 0.726 |
| hybrid | 0.673 (37/55) · MRR 0.460 | 0.764 (42/55) · MRR 0.633 |
| hybrid_rerank | 0.764 (42/55) · MRR 0.631 | 0.836 (46/55) · MRR 0.818 |

Tham số: k=5, candidates=20, rrf_k=60, fixed_rule=fixed_hit_rank ≥ 0.5, bm25_build_s=129.7, retrieval_s=3003.9
