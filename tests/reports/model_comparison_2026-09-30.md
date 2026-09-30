# Model / Index Comparison — 2026-09-30

Measured with `tests/evaluation/evaluate_accuracy.py` against the same backend code, each setup on a fresh backend (`SEOULMATE_RELOAD=0`, port 8003).

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

## Decision

A (current production) stays live. C is effectively tied with A, not worse as first reported under the stale evaluator. B (rebuilt index) is not adopted until its rating-filter and typo regressions are understood.
