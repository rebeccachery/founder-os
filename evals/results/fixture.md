# Funding Scout ranker evaluation

- **labels:** synthetic fixture
- **candidates:** 30 (14 relevant, 47% base rate)
- **as-of date:** 2026-11-20

| system | P@10 | nDCG@10 | P@25 | nDCG@25 | MAP | AUC | MAP 95% CI |
|---|---|---|---|---|---|---|---|
| keyword_v3 (production) | 1.000 | 0.936 | 0.560 | 0.979 | 0.982 | 0.982 | 0.931–1.000 |
| keyword_v2 (word match) | 1.000 | 0.936 | 0.560 | 0.979 | 0.982 | 0.982 | 0.931–1.000 |
| keyword_v1 (substring) | 1.000 | 0.936 | 0.560 | 0.974 | 0.957 | 0.960 | 0.865–1.000 |
| bm25 (profile query) | 1.000 | 0.998 | 0.560 | 0.997 | 0.995 | 0.996 | 0.968–1.000 |
| deadline_only | 0.500 | 0.289 | 0.440 | 0.491 | 0.472 | 0.558 | 0.323–0.804 |
| random | 0.500 | 0.525 | 0.440 | 0.706 | 0.648 | 0.594 | 0.392–0.852 |

## keyword_v3 (production) vs. each alternative (paired bootstrap, MAP)

| compared with | ΔMAP | 95% CI | P(production better) |
|---|---|---|---|
| keyword_v2 (word match) | +0.000 | +0.000 to +0.000 | 0% |
| keyword_v1 (substring) | +0.025 | +0.000 to +0.086 | 86% |
| bm25 (profile query) | -0.014 | -0.053 to +0.000 | 0% |
| deadline_only | +0.510 | +0.176 to +0.656 | 100% |
| random | +0.333 | +0.140 to +0.578 | 100% |
