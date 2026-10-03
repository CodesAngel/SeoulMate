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
| Live system after seed-drama fix + evaluator label fixes (2026-10-01) | 85.95% |
| Live system after curated-title name matching (2026-10-01) | **86.24%** |
| Same system, expanded test set (61 scored searches, 2026-10-01) | 87.92% |
| Same test set, exact title matching (2026-10-03; unchanged by the franchise ordering) | **87.05%** |

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

## Follow-up (2026-10-01): theme searches and curated-title name matching

**Theme misses reviewed.** Of the five theme tests below their ceiling, four already had every expected title in the top 10 with the correct first result (MRR 1.0); the top 3 held other fitting dramas, e.g. *Nine: Nine Times Time Travel* for "time travel" (the test expects *Signal*, which is about linked timelines rather than time travel), and *Late Night Restaurant* / *Pasta* for "restaurant food" (the test expects *Itaewon Class*, which has no food genre or keywords). These were left alone to avoid tuning rankings to the test. The real miss was *Misaeng* not appearing in the top 10 for "workplace startup", nor at all for "office life".

**Root cause: curated priors referenced titles that don't exist in the dataset.** The ranking config files list titles by name, and the backend looked them up by exact (case-insensitive) title. 164 references across 44 names never matched, so those dramas silently got no curated boost — e.g. "Misaeng" (dataset: *Misaeng: Incomplete Life*, 9 references), "Goblin" (27), "Twenty Five Twenty One" (21), "Arthdal Chronicles", "Moon Lovers", "Heartless City" (dataset: *Cruel City*).

**Fix (`backend/app.py`):** a name map built at startup (`build_canonical_title_map` / `canonical_title`) resolves config names to dataset titles using the title aliases, the dataset's own "Also Known As" names, and title variants (punctuation/accents ignored, either side of a colon, with/without a leading "The"). A name is only mapped when it points to exactly one drama, and exact titles always map to themselves. It is applied in `add_prior_title_boosts`, `apply_similar_title_priors` and the similar-title prior keys. Two ambiguous names were added as explicit aliases (`I Am Not a Robot`, `Chief Kim`). Result: 190 config references now resolve; 6 remain unresolved, all films or titles not in the dataset.

| Metric | Before (85.95% run) | After |
|---|---|---|
| **Overall accuracy** | 85.95% | **86.24%** |
| Precision@3 | 54.94% | 55.56% |
| Recall@10 | 98.46% | 99.38% |
| MRR | 0.969 | 0.969 |
| NDCG@10 | 0.974 | 0.979 |
| Theme Precision@3 | 48.5% | 51.5% |
| Avg response time | 69 ms | 77 ms |

Misaeng now ranks #3 for "workplace startup" and #4 for "office life". Still open: "workplace drama" doesn't surface it, because "drama" is detected as a genre and the query never reaches the office/workplace priors.

## Follow-up (2026-10-01): expanded test set + "drama" genre experiment

### Expanded test set (`tests/evaluation/evaluate_accuracy.py`)

- **Wider expected lists:** genre tests now accept 4–5 dramas, theme tests 3–5, actor tests 3. Added titles were chosen as well-known dramas that fit the query and checked against the dataset's genre/keywords (or cast, for actors) — not taken from the system's output. E.g. "medical drama" adds *Dr. Romantic* and *Doctors*; "time travel" adds *Nine: Nine Times Time Travel* and *Rooftop Prince*; Gong Yoo adds *Big*.
- **New dramas covered:** title tests for five 2026 dramas from the new index (*Teach You a Lesson*, *Agent Kim Reactivated*, *Yumi's Cells Season 3*, *The Legend of Kitchen Soldier*, *Phantom Lawyer*) and two typo tests ("Agent Kim Reactivatd", "Phantom Lawer"). All resolve correctly.
- **Self-listing regression check:** every title search verifies that the searched drama doesn't appear in its own similar list (the bug fixed earlier today). Currently 27/27 pass. Reported separately; not part of the overall score.
- Scored searches: 54 → 61. Best achievable Precision@3: 61.7% → 68.3%.

Same backend, both test sets:

| Metric | Old set (54) | New set (61) |
|---|---|---|
| **Overall accuracy** | 86.24% | **87.92%** |
| Precision@3 | 55.56% | 62.30% |
| Recall@10 | 99.38% | 95.63% |
| MRR | 0.969 | 0.992 |
| NDCG@10 | 0.979 | 0.961 |

Scores from the two sets aren't comparable with each other; from here on, figures use the new set.

### "Drama" as a genre — tried and reverted

Queries like "workplace drama" detect the genres Business **and** Drama. The genre filter uses OR logic, and ~1,200 of 2,081 dramas carry the Drama tag, so it barely filters. Experiment: ignore "Drama" for filtering/boosting whenever a more specific genre is detected. Result: **worse** — old set 86.24% → 85.73%, new set 87.92% → 87.31%, genre Precision@3 92.3% → 84.6% (e.g. "doctor hospital drama" lost *Doctor Cha* and *Dr. Romantic* for *Hospital Ship* and *Doctor Prisoner*; "sad emotional drama" lost *My Mister*). The Drama boost works as a rough popularity signal, since well-known series usually carry the tag. Reverted.

### Workplace queries

The actual cause of "workplace drama" missing workplace dramas was that curated setting priors are matched against the raw query, and only the word "office" triggered the Office list. Added a "Workplace" setting prior (same titles as Office) and a `workplace` → office/career synonym in `query_analyzer.py`. "workplace drama" now returns *Business Proposal*, *What's Wrong with Secretary Kim*, *Her Private Life*, *Forecasting Love and Weather*, *Agency*, *Misaeng: Incomplete Life* (previously *The Queen of Office*, *The King of Dramas*, *Top Management*, ...). Test scores unchanged (no test uses that query).

Noted for later: the similar dramas for *Yumi's Cells Season 3* are *Live* and *Jun & Jun* rather than earlier Yumi's Cells seasons. (Fixed 2026-10-03, below.)

## Follow-up (2026-10-03): other seasons first + exact-match metrics

### Franchise ordering

A title search now puts the drama's other seasons/parts first, oldest first (`franchise_siblings()` in `backend/app.py`). Grouping rule, checked against all 2,081 titles:

- Titles differing only by a "Season N", "Part N", "#N" or trailing-number suffix are grouped even with different casts (*Save Me* / *Save Me Season 2*, *Reply 1988/1994/1997*, *Soundtrack #1/#2*).
- Colon subtitles and identical names must also share a cast member or director. This keeps *Kingdom: Ashin of the North*, *Dr. Romantic: APPENDIX* and *Mouse: Restart* in their groups, and leaves out *Family: The Unbreakable Bond*, *Search: WWW*, *Black Knight: The Man Who Guards Me* and *Who Are You?*.

| Query | Before | After (top 3) |
|---|---|---|
| Yumi's Cells Season 3 | Live, Jun & Jun, Run On | Yumi's Cells, Yumi's Cells Season 2, Live |
| Yumi's Cells | It's Okay to Not Be Okay, My Mister, ... | Yumi's Cells Season 2, Yumi's Cells Season 3, It's Okay to Not Be Okay |
| Dr. Romantic Season 3 | Dr. Romantic, Hospital Ship, New Heart | Dr. Romantic, Dr. Romantic: APPENDIX, Dr. Romantic Season 2 |
| Taxi Driver | Military Prosecutor Doberman, Bad Guys: City of Evil, Punch | Taxi Driver Season 2, Military Prosecutor Doberman, Bad Guys: City of Evil |
| Best Mistake Season 2 | Be My Boyfriend, Romance, Talking, ... | Best Mistake, Best Mistake Season 3, Be My Boyfriend |

New evaluator check (10 cases, reported separately, not scored): 2/10 → **10/10**.

### Evaluator fix: exact title matching

Precision, recall, MRR and NDCG matched expected titles by substring, so a sequel counted as a hit (*Hospital Playlist Season 2* for "Hospital Playlist"); with sequels now listed, NDCG@10 came out at 1.011. Switched to exact, case-insensitive matching and re-ran the committed backend (git worktree at `32342e5`) and the new one:

| Metric | Before franchise change | After |
|---|---|---|
| **Overall accuracy** | 87.05% | **87.05%** |
| Precision@3 | 60.66% | 60.66% |
| Recall@10 | 94.48% | 94.48% |
| MRR | 0.992 | 0.992 |
| NDCG@10 | 0.943 | 0.943 |
| Franchise ordering | 2/10 | **10/10** |

The 87.92% figure was inflated by substring hits (genre Precision@3 92.3% → 89.7% under exact matching, e.g. *Kingdom Season 2* had counted for "Kingdom").

## Follow-up (2026-10-03): similar dramas for non-curated titles

Only 21 dramas have curated similar-title lists; all other title searches are ranked by `seed_similarity_score`. New check in `evaluate_accuracy.py` (`SIMILAR_TEST_CASES`): 15 seeds without curated lists (10 from 2026, plus Signal, Hotel del Luna, Vincenzo, Mr. Queen, Kingdom), each with 4–6 widely cited comparable dramas checked to exist in the dataset. The seed's other seasons are skipped. Not part of the overall score.

**Diagnosis.** The old score gave +2.4 per shared hand-written "theme" matched by substring against title/description, which outweighed everything else: *The Legend of Kitchen Soldier* got military dramas because of its Military genre (FAISS alone ranked *Let's Eat*, *Pasta* top), and *Spring Fever* matched "office romance"/"legal". Also, only 30 of the 80 expected dramas were in the top-200 FAISS pool that got reranked, so retrieval capped what rescoring could do.

**Offline sweep** (FAISS pool → rescore; script replicated the backend, results matched the live backend exactly):

| Variant | P@5 | R@10 |
|---|---|---|
| Old scoring, top-200 pool | 9.3% | 12.8% |
| FAISS only | 6.7% | 8.7% |
| IDF genre+keyword, top-200 pool | 12.0% | 17.9% |
| IDF, whole corpus, genre+keyword query | 18.7% | 23.9% |
| + popularity 1.5 (**chosen**) | **22.7%** | **28.8%** |
| + popularity 3 | 32.0% | 39.0% |

Query text: description-only retrieved fewer comparables (15/80 in top 200), genre+keywords the most (35/80); adding cast/director changed nothing (the text is truncated before it). Popularity 3 was rejected: *Because This Is My First Life* appeared in 11 of 55 top-10 lists, and *Crash Landing on You* became a top-2 match for Kitchen Soldier; the expected lists favour well-known dramas, so the test rewards popularity more than users would.

**Live results** (old backend P@5 6.7% / R@10 15.6% → **22.7% / 28.8%**). Examples (top 5): Kitchen Soldier → *Pasta, Bon Appetit, Panda and Hedgehog, I Order You, Wok of Love*; Hotel del Luna → *Bring It On, Ghost, My Demon, Sell Your Haunted House, Spooky in Love, A Korean Odyssey*; Mr. Queen → *Queen and I, Bon Appetit, Your Majesty, Rooftop Prince, ...*. Still missing their expected dramas: Spring Fever, Filing for Love, To My Beloved Thief, Phantom Lawyer.

Overall 87.05% (unchanged), franchise 10/10, `search_regression_suite.py` 33/33. Title searches also skip BM25 (zero weight in that mode): 0.5–1.1 s → 0.15–0.28 s uncached.

## Follow-up (2026-10-03): trope searches

New check `HARD_THEME_TEST_CASES` (8 queries, separate from the overall score): expected dramas are well-known examples, preferring ones with the matching dataset tag (e.g. 14 dramas carry "Found Family", 18 "Body Swap", 106 "Older Woman/Younger Man"; no tag mentions "chaebol" or "second lead").

**Causes found**
- Typed queries never consulted keyword tags; the keyword index was only used for the explicit `keywords=` API parameter. Ranking came from title words and description embeddings ("body swap" → *Switch: Change the World*, *Friends with Benefits Play the Swap Game*).
- "found family" / "chaebol family" detected the Family genre, which hard-filters the corpus, removing every expected drama. The curated "found family" relationship prior was applied but its titles were already filtered out.
- The relationship prior "body swap romance" needs "romance" in the query, so "body swap" matched nothing.

**Fix**: `trope_priors.json` maps aliases → tags; matched tropes boost tagged dramas (most-watched first, boost 1.9, decay 0.03, top 40) and their words are removed from detected genres.

| Query | P@5 before | P@5 after | Top 5 after |
|---|---|---|---|
| chaebol family | 0% | 40% | My Demon, Queen of Tears, When the Phone Rings, Reborn Rich, My Royal Nemesis |
| second lead syndrome | 0% | 40% | Strong Woman Do Bong Soon, True Beauty, Boys over Flowers, The Heirs, Itaewon Class |
| found family | 0% | 60% | The Uncanny Counter, A Shop for Killers, Hospital Playlist, Summer Strike, If You Wish Upon Me |
| enemies to lovers | 20% | 40% | Our Beloved Summer, Cheese in the Trap, Mad for Each Other, A Korean Odyssey, When the Phone Rings |
| noona romance | 80% | 80% | Romance Is a Bonus Book, I Hear Your Voice, Something in the Rain, Search: WWW, Crash Course in Romance |
| body swap | 0% | 100% | Alchemy of Souls, Secret Garden, The Heavenly Idol, High School Return of a Gangster, Big |
| childhood friends to lovers | 40% | 60% | Weightlifting Fairy Kim Bok Joo, Fight for My Way, Romance Is a Bonus Book, Love Next Door, Doctor Slump |
| fake dating | 40% | 60% | Business Proposal, My Demon, Because This Is My First Life, The Beauty Inside, Marriage, Not Dating |
| **Average** | **22.5%** | **60.0%** | Recall@10 22.3% → 69.4% |

Unchanged: overall 87.05%, similar dramas 22.7% / 28.8%, franchise 10/10, regression suite 33/33.

### 10 more tropes (2026-10-03)

Added time slip, amnesia, hidden identity, cohabitation, reincarnation, cross-dressing, second chance romance, Cinderella, secret relationship and arranged marriage to `trope_priors.json`, with 10 matching test queries. Before: 8% average P@5 on those 10.

Two more causes found:
- **Fuzzy title capture.** "reincarnation" → *Reincarnation Love*, "cinderella story" → *Cinderella's Sister*, "secret relationship" → *Secret Relationships*: the query became a similar-to-title search. Now a matched trope blocks fuzzy title resolution unless the query is exactly a dataset title ("hidden identity" is the exact title *Hidden Identity*, so it stays a title search; the test uses the alias "secret identity").
- **Boost too low.** "living together romance" had the trope applied but the Romance genre prior (2.2) outranked it (1.9). Trope boost → 2.4.

| Query | P@5 before | P@5 after |
|---|---|---|
| time slip romance | 40% | 40% |
| amnesia romance | 0% | 60% |
| secret identity | — | 80% |
| living together romance | 0% | 60% |
| reincarnation | 0% | 80% |
| cross dressing | 0% | 80% |
| second chance romance | 40% | 40% |
| cinderella story | 0% | 80% |
| secret relationship | 0% | 80% |
| arranged marriage | 0% | 80% |

Whole 18-query check: **P@5 63.3%, R@10 81.8%**. The original 8 queries: 60.0% → 57.5% ("found family" 60% → 40% under the higher boost, as tag-ordered dramas like *Black Knight* outrank the curated list). Tried putting curated relationship lists ahead of tagged dramas: "found family" back to 60% but the check fell to 55.6% (curated lists for enemies to lovers, fake dating etc. are weaker than the tags). Not kept.

Unchanged: overall 87.05%, "time travel" scored test 100% P@3, franchise 10/10, similar dramas 22.7% / 28.8%, regression suite 33/33.
