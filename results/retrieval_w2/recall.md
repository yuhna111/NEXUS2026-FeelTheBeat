# Recall@5 trên bộ pilot (tuần 2, TV2)

## Bộ `v1.0` (55 câu)

| Truy xuất | Chia cố định | Chia theo Điều–Khoản |
|---|---|---|
| bm25 | 0.455 (25/55) · MRR 0.318 | 0.582 (32/55) · MRR 0.459 |
| dense | 0.545 (30/55) · MRR 0.414 | 0.800 (44/55) · MRR 0.731 |
| hybrid | 0.691 (38/55) · MRR 0.511 | 0.764 (42/55) · MRR 0.660 |

## Bộ `tv1-33` (33 câu)

| Truy xuất | Chia cố định | Chia theo Điều–Khoản |
|---|---|---|
| bm25 | 0.455 (15/33) · MRR 0.328 | 0.667 (22/33) · MRR 0.543 |
| dense | 0.667 (22/33) · MRR 0.533 | 0.879 (29/33) · MRR 0.823 |
| hybrid | 0.758 (25/33) · MRR 0.582 | 0.879 (29/33) · MRR 0.783 |

Tham số: k=5, candidates=20, rrf_k=60, prefix_chars=80, bm25_build_s=150.5, retrieval_s=179.1
