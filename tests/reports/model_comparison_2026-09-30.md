# Model / Index Comparison — 2026-09-30

Measured with `tests/evaluation/evaluate_accuracy.py` against the same backend code, each setup on a fresh backend (`SEOULMATE_RELOAD=0`, port 8003).

## Summary (final, after the rating-filter fix)

| Setup | Accuracy |
|---|---|
| Production (old index, 1,922 dramas) | 79.31% |
| training-new, old index (1,823 dramas) | 79.03% |
| training-new, new index (2,081 dramas) | 78.75% |
| Production models + new index (2,081 dramas) | 78.35% |
| Live system after year-filter, typo-scoring and typo-resolution fixes (2026-10-01) | 84.32% |
| Live system after seed-drama fix + evaluator label fixes (2026-10-01) | **85.95%** |

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

## Follow-up (2026-10-01): typo title fix + timing re-run

- **"Hospitl Playlist" root cause:** not the 95% threshold — it scores 97 and the first resolution step matched "Hospital Playlist". Stage 4.2 of `recommend()` then re-resolved the title with only exact/alias matching, discarding the fuzzy match, so a looser typo resolver (`token_set_ratio` ≥ 74) took over and picked "Love Playlist". (That resolver also skips "Hospital Playlist" because its description contains the word "special", which is in `special_title_terms`.) Fixed in `backend/app.py`: Stage 4.2 now reuses the Stage 4.1 match when it survives filtering. No threshold changed.
- **Timing:** re-run with 6.6 GB free RAM (previous run had 1.7 GB). Average uncached response time 156 ms (min 18, max 302), down from 606 ms.

| Metric | Before (83.76% run) | After |
|---|---|---|
| **Overall accuracy** | 83.76% | **84.32%** |
| Precision@3 | 51.85% | 52.47% |
| Recall@10 | 95.06% | 96.91% |
| MRR | 0.900 | 0.919 |
| NDCG@10 | 0.910 | 0.929 |
| Filter success rate | 100% | 100% |
| Avg response time | 606 ms | 156 ms |

All 5 typo queries now return the intended drama first.

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

## Follow-up (2026-10-01): seed-drama bug, special-title filter, Precision@3 analysis

- **Seed-drama bug (backend):** six boost loops in `recommend()` (genre, theme, actor, keyword, quality) used `drama` as their loop variable, overwriting the searched drama. Whenever a title query also triggered a boost (e.g. "Attorney" → Law genre, "Hospital" → Medical), title-similarity mode removed and scored against the wrong drama. Effects: "Extraordinary Attorney Woo" appeared at rank 8 of its own similar list; "Hospital Playlist" returned *Life* and *A Poem a Day* as similar dramas (now *Dr. Romantic*, *Doctor Cha*). Fixed by renaming the loop variable to `candidate`.
- **Special-title filter (backend):** `is_special_or_meta_title` searched descriptions, flagging 232 of 2,081 dramas (e.g. Hospital Playlist, whose description says "special"), which hid them from typo matching. It now checks only a Documentary genre or whole-word terms in the title (`special`, `making film`, `behind the scenes`, `documentary`, `SP`), flagging 8 — all genuine specials/documentaries. `behind` in `query_intent_priors.json` narrowed to `behind the scenes` so *Terius behind Me* / *Behind Your Touch* aren't flagged.
- **Evaluator fixes:** the resolved title is now always moved to rank 1 (it was only prepended when absent, so a seed leaking into its own list was scored at its leaked rank). "Goblin" expectations now use the dataset's official title, *Guardian: The Lonely and Great God* — the backend already returned it, but the test only accepted the string "Goblin" (affected the Goblin, fantasy romance and Gong Yoo tests).

| Metric | Before (84.32% run) | After |
|---|---|---|
| **Overall accuracy** | 84.32% | **85.95%** |
| Precision@3 | 52.47% | 54.94% |
| Recall@10 | 96.91% | 98.46% |
| MRR | 0.919 | 0.969 |
| NDCG@10 | 0.929 | 0.974 |
| Filter success rate | 100% | 100% |
| Avg response time | 156 ms | 69 ms |

### Why Precision@3 stays near 55%

Precision@3 counts how many of the top 3 results are in a test's expected list, so a test with one expected title can score at most 33%. Across the 54 scored search tests the **best achievable Precision@3 is 61.7%**:

| Category | Tests | Max possible | Before | After |
|---|---|---|---|---|
| specific_title | 15 | 33.3% | 28.9% | 33.3% |
| typo | 5 | 33.3% | 33.3% | 33.3% |
| genre | 13 | 100% | 82.1% | 84.6% |
| theme | 11 | 63.6% | 48.5% | 48.5% |
| actor | 10 | 66.7% | 63.3% | 66.7% |
| **All** | 54 | **61.7%** | 52.5% | 54.9% |

Title and typo tests are now at their ceiling. The remaining gap is genre/theme/actor queries whose top 3 contain good results that aren't in the 2–3-title expected list (e.g. *Dr. Romantic* for "medical drama", *Mouse* for "crime thriller", *Lawless Lawyer* for "law firm corruption"). Raising Precision@3 further means either widening those expected lists or tuning rankings to match them — the first is a test-design choice, the second risks overfitting to the test.
