# Model / Index Comparison — 2026-09-30

Measured with `tests/evaluation/evaluate_accuracy.py` against the same backend code, each setup on a fresh backend (`SEOULMATE_RELOAD=0`, port 8003).

## Summary (final, after the rating-filter fix)

| Setup | Accuracy |
|---|---|
| Production (old index, 1,922 dramas) | 79.31% |
| training-new, old index (1,823 dramas) | 79.03% |
| training-new, new index (2,081 dramas) | 78.75% |
| Production models + new index (2,081 dramas) | 78.35% |

**Decision (2026-10-01):** production now runs the production models (`sbert-finetuned-full` + `cross-enc-excellent`, 88 MB reranker) with the new 2,081-drama index. training-new scored 0.4 points higher, which is within noise for ~80 test queries, but needs a 2.2 GB reranker. The old 1,922-drama index is kept in `training/faiss_index.bak`. Details and the before/after-fix numbers are below.

## Setups

| ID | Bi-encoder | Reranker | FAISS index | Dramas indexed |
|---|---|---|---|---|
| A | `training/models/sbert-finetuned-full` | `cross-enc-excellent` | `training/faiss_index` (Nov 2025, current production) | 1,922 |
| B | `training/models/sbert-finetuned-full` | `cross-enc-excellent` | `training/faiss_index.new` (rebuilt from `data/final/kdrama_dataset.csv`) | 2,081 |
| C | `training-new/output/models/e5-kdrama-finetuned` | `cross-encoder-finetuned` (bge-reranker-v2-m3) | `training-new/output/faiss_index` | 1,823 |

## Results

| Metric | A — production | B — rebuilt index | C — training-new |
|---|---|---|---|
| **Overall accuracy** | **79.31%** | 74.60% | 79.03% |
| Precision@3 | 50.62% | 50.00% | 50.62% |
| Recall@10 | 90.43% | 89.51% | 91.36% |
| MRR | 0.828 | 0.845 | 0.841 |
| NDCG@10 | 0.894 | 0.855 | 0.880 |
| Filter success rate | 75% | 50% | 75% |
| Genre detection | 100% | 100% | 100% |
| Personalization | 100% | 100% | 100% |
| Avg response time | 59 ms | 72 ms | 51 ms |

Precision@3 by category:

| Category | A | B | C |
|---|---|---|---|
| Specific title (max 33.3%) | 26.67% | 28.89% | 31.11% |
| Genre | 82.05% | 82.05% | 82.05% |
| Theme | 48.48% | 48.48% | 48.48% |
| Actor | 63.33% | 63.33% | 63.33% |
| Typo | 20.00% | 6.67% | 6.67% |

## Notes

- **The old 88.5% baseline is no longer reproducible.** Since the 2026-07-24 title-search changes (`78812a0`, `9b3c290`), an exact title query runs in `title_similarity` mode and returns dramas *similar* to the title, excluding the title itself. The evaluator expected the title in the top 3, so all title tests scored 0 and every setup capped at ~67–73%.
- **Evaluator fix:** for `specific_title` queries the evaluator now requests `debug=true` and, if the backend resolved the title (`debug.resolved_title`), counts it as the top hit ahead of the similar dramas. Precision@3 for a single expected title is capped at 33.3%.
- Genre/theme/actor scores are identical across all three setups, so those categories are driven by the curated priors and generated indexes, not by the embedding model or FAISS index.
- **B's filter drop:** B failed the `rating_value >= 8.5` filter test (returned at least one drama below 8.5); A and C pass it. Likely a rating value in the new dataset that the filter handles differently — not yet investigated.
- **B's typo drop:** typo queries fell from 20% to 6.67% with the larger index.
- The `year=2020` filter test fails in all three setups.

## Decision (first pass)

A (current production) stays live. C is effectively tied with A, not worse as first reported under the stale evaluator. B (rebuilt index) is not adopted until its rating-filter and typo regressions are understood.

## Follow-up (2026-10-01): year filter + typo scoring

Run on the live setup (production models + 2,081-drama index):

- **Year filter added:** `/recommend` had no `year` parameter, so `year=2020` was silently ignored, and the evaluator checked a `Year` field that doesn't exist. The backend now accepts `year` and keeps dramas whose aired range (`Release Years`, e.g. "Dec 10, 2019 - Jan 11, 2020") includes it; the evaluator checks the same field.
- **Typo scoring:** misspelled titles run in the same `title_similarity` mode as exact titles, so typo queries now use the same `resolved_title` scoring.

| Metric | Before | After |
|---|---|---|
| **Overall accuracy** | 78.35% | **83.76%** |
| Precision@3 | 50.00% | 51.85% |
| Recall@10 | 89.51% | 95.06% |
| MRR | 0.845 | 0.900 |
| NDCG@10 | 0.855 | 0.910 |
| Filter success rate | 75% | 100% |

Still open: "Hospitl Playlist" fails because the backend's fuzzy title match needs 95% similarity and resolves to "Love Playlist" instead. Average response time now reads ~600 ms because title tests use `debug=true` (which skips the cache), so the performance test measures uncached searches; the earlier ~60 ms figures were cache hits.

## Follow-up: training-new index rebuilt on 2,081 dramas + rating-filter fix

- Rebuilt training-new's four indexes (main, genre, actor, theme) from `data/final/kdrama_dataset.csv` with the existing fine-tuned E5 model — no retraining. `training-new/steps/enhanced_index_builder.py` now reads CSV and defaults to the `output/` paths. Old index kept in `training-new/output/faiss_index.bak`.
- **Root cause of the filter drop in B:** 111 dramas in the new dataset have an empty `rating_value`/`rating_count` (mostly upcoming shows). The backend's rating filter did `float("")`, which raised inside a `try/except` that silently skipped the whole filter. Fixed in `backend/app.py` (rating-value filter, rating-count filter and the `top_rated` sort) by treating an empty value as 0.

| Setup | Before fix | After fix |
|---|---|---|
| A — production (old index, 1,922) | 79.31% | 79.31% (unaffected — no empty ratings) |
| B — production models + rebuilt index (2,081) | 74.60% | **78.35%** |
| C — training-new, old index (1,823) | 79.03% | 79.03% (unaffected) |
| D — training-new, rebuilt index (2,081) | 75.00% | **78.75%** |

D after the fix: Precision@3 50.62%, Recall@10 89.51%, MRR 0.823, NDCG@10 0.866, filter success 75%, avg response 97 ms.

The remaining ~0.5-point gap between old and rebuilt indexes comes from NDCG/typo queries: the ~160–260 extra dramas add more candidates that compete with the expected results.
