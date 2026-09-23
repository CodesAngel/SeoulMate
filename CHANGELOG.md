# SeoulMate Changelog

Important project history reconstructed from Git commits and project documentation.

## 2026-09-23

### DramaList Scrapper Pipeline Restructure

- Consolidated the MyDramaList scraping scripts (previously `scrapper.py`, `scrapper_2.py`, `dramaImage.py`, and `html_extractor_and_reader.py`) into a single, ordered pipeline under `scrapers/DramaList_Scrapper/`.
- Split the code into five numbered, single-purpose step scripts under `scrapers/DramaList_Scrapper/steps/`:
  - `step0a_download_listing_pages.py` — downloads MyDramaList's `popular` and `newest` listing pages via Playwright, each source saved into its own subfolder (`output/html_pages/popular/`, `output/html_pages/newest/`)
  - `step0b_extract_drama_urls.py` — parses listing pages (recursively across source subfolders) into `mydramalist_data.csv` with each drama's `Title_URL`
  - `step1_download_html.py` — downloads each drama's own page into `output/dramas_html/`
  - `step2_extract_data.py` — extracts structured fields (genres, cast, rating, episodes, etc.) into `dramalist_all_dramas.csv`
  - `step3_download_images.py` — downloads poster images into `output/drama_image/`
- Added `run_pipeline.py` as a single entry point that runs all five steps in order, with `--skip-*` and `--only <step>` flags; every step is independently resumable (skips work already done).
- Fixed several stale hardcoded paths left over from the project's earlier name (`Kdrama-recommendation`/`data_scrapper`).
- Fixed a `KeyError: 'title'` in Step 2's resume logic caused by reading its own BOM-prefixed output CSV with the wrong encoding (`utf-8` instead of `utf-8-sig`).
- Moved all scraped/intermediate data (listing pages, drama HTML, poster images, backup CSVs) under `scrapers/DramaList_Scrapper/output/`, and excluded that folder from Git via `.gitignore` (previously tracked in Git; fixed a malformed absolute-path `.gitignore` entry that wasn't actually excluding it).
- Added a `README.md` inside `scrapers/DramaList_Scrapper/` documenting the full pipeline, folder layout, and how to run/extend it.

### DramaList Scrapper: Dedup and Country Split

- Added `steps/step2b_dedupe_data.py` — removes duplicate rows from `dramalist_all_dramas.csv` by `url` (the true unique per-drama identifier), needed because Step 0b's `popular` and `newest` listing sources can list the same drama. Writes to a separate `output/dramalist_all_dramas.deduped.csv` rather than overwriting the original.
- Added `steps/step2c_split_by_country.py` — splits the deduped dataset by its `country` column into one CSV per country under `output/by_country/`, named `<prefix>drama_dataset.csv` using the industry-standard shorthand (`kdrama_dataset.csv` for South Korea, `cdrama_dataset.csv` for China, `jdrama_dataset.csv` for Japan, `tdrama_dataset.csv` for Thailand, `twdrama_dataset.csv` for Taiwan, `hkdrama_dataset.csv` for Hong Kong; Philippines and Singapore fall back to their first letter, `pdrama_dataset.csv`/`sdrama_dataset.csv`, with no established industry term).
- Wired both into `run_pipeline.py` as steps `dedupe` and `split` (pipeline is now 7 steps total), each independently resumable and runnable on their own via `--only dedupe` / `--only split`.
- Verified end-to-end: deduping cut the dataset from 61,944 rows (accumulated duplicates from earlier test runs) down to 4,720 unique dramas by url; the country split correctly produced all 8 expected files with matching row counts.

### DramaList Scrapper: Point Image Downloads at Split Data, Full Pipeline Audit

- Switched Step 3 (`step3_download_images.py`) to read from `output/by_country/kdrama_dataset.csv` (Step 2c's output) instead of the older standalone `dramalist_kdramas.xlsx`, so poster downloads now stay in sync with the deduped, split dataset.
- Fixed a second BOM-related bug this change surfaced: `download_images_from_csv`'s CSV read path was missing `encoding="utf-8-sig"`, so it would have hit the same `title` column misread (`﻿title`) as the earlier Step 2 bug once fed a CSV instead of the `.xlsx` it previously used. Fixed and verified against the actual file.
- Note: Step 3 now depends on Step 2c having already run (`output/by_country/kdrama_dataset.csv` must exist), since it's no longer a standalone input.
- Added `training-new/output/` to `.gitignore` (previously untracked but not excluded, matching the existing pattern for `scrapers/DramaList_Scrapper/output/`).
- Ran a full pipeline audit: verified every step's hardcoded path matches what the previous step actually produces on disk, syntax-checked all 7 step scripts plus `run_pipeline.py`, and confirmed `run_pipeline.py` imports cleanly. Found and fixed one gap: `mydramalist_data.csv` (Step 0b's output) was missing at its expected top-level path; regenerated it via `run_pipeline.py --only urls`. Noted the `newest` listing source is not yet fully downloaded (171/250 pages) — not an error, just incomplete, resumable via `--only listing`.

## 2026-08-04

### Real-World Search QA

- Tested common user search scenarios against the local backend, including exact-title searches, similar-drama searches, broad genre browsing, repeated refresh searches, trope searches, exclusions, actor queries, typos, aliases, vague mood queries, and low-information recommendation requests.
- Confirmed strong behavior for `Crash Landing on You`, `shows like Goblin`, `similar_to=Business Proposal`, `soldier romance`, `doctor drama`, `office romance`, `romance without historical`, `thriller no horror`, `Park Seo Joon dramas`, and repeated `comedy drama` refresh searches.
- Identified next search-quality gaps:
  - generic requests such as `recommend me something good` still over-match literal words like `good` and `best`
  - typo title searches such as `crash landng on yu` should enter title-similarity mode and exclude the seed title
  - multi-intent searches such as `time travel thriller` need stronger handling for both requested concepts
  - negated mood phrases such as `not too dark` need better exclusion logic
- Verified the current live regression suite remains at `18/18` checks passed after the ranking debug changes.
- Improved the real-world weak cases found during QA:
  - generic quality requests now use curated high-quality drama priors instead of literal `good`/`best` keyword matching
  - typo title searches now use token-set title resolution and enter title-similarity mode
  - multi-intent theme + genre searches now support combo priors such as `time travel thriller`
  - negated mood phrases now suppress excluded mood priors, such as `mood:dark` for `not too dark`
- Expanded the live regression suite to cover these real-world scenarios.
  - Current focused regression result: `22/22` checks passed against the local backend.
- Added a second real-world search hardening pass:
  - fixed short aliases and typo-like aliases such as `gobln`, `DOTS`, and `WWWSK`
  - improved similar-drama priors for `Descendants of the Sun` and `What's Wrong with Secretary Kim`
  - prevented recent/year/top-rated browse queries from accidentally entering fuzzy title-similarity mode
  - added recent, Netflix, Kim Eun-sook, sad-romance, sports-romance, and no-sad-ending query priors
  - filtered broad literal title noise for broad genre searches such as `romance drama`
  - fixed zombie exclusions so `thriller without zombies` keeps thriller results but removes zombie titles
- Expanded live regression coverage for the second hardening pass.
  - Current focused regression result: `28/28` checks passed against the local backend.
- Refactored query-specific real-world priors into `backend/ranking/config/query_intent_priors.json` so aliases, generic-quality patterns, combo priors, broad-title noise, recent priors, and similar-title overrides can be tuned as data instead of adding more backend rules.
- Added a real-world search evaluation harness:
  - created `tests/evaluation/real_world_queries.json` with 52 realistic user queries across exact titles, aliases, typos, similar-title requests, genres, moods, negations, actors, writers, platforms, recent/year queries, and broad recommendation requests
  - created `tests/evaluation/evaluate_real_world_search.py` to score live backend results with Hit@1/3/5/10, MRR, Recall@5/10, forbidden-result checks, and tag-level breakdowns
  - captured the current baseline in `tests/reports/debug/real_world_eval_latest.txt`
  - Current real-world evaluation result: `52/52` cases passed, `100.0%` Hit@5, `100.0%` Hit@10, `0.985` MRR, and `100.0%` forbidden checks passed.
- Added a feedback-driven search quality dashboard:
  - added `/analytics/search-quality` to join search logs with click/watchlist feedback
  - added fallback matching by user/session/timestamp so older interactions without `search_id` can still produce quality signals
  - expanded the Streamlit Analytics tab with weak-query candidates, recent no-feedback searches, and positive query-drama examples for future training data
  - fixed the Analytics tab parsing for wrapped popular-drama and trending-search API responses.

## 2026-07-24

### Recommendation Flow and Runtime Data Updates

- Updated exact title searches to behave like similar-drama recommendations instead of literal keyword searches.
  - Title queries such as `Crash Landing on You` now use the matched drama as a seed.
  - BM25 keyword influence is suppressed for exact-title similarity mode so individual title words like `crash` do not dominate results.
  - The seed drama is excluded from its own recommendation list.
- Updated the frontend `Similar` action to call the backend `similar_to` flow instead of re-searching the clicked title as plain text.
- Added a `refresh` token for broad browse queries so repeated genre/vague/emotion searches can lightly vary results from a high-quality candidate pool.
- Enhanced search intent handling:
  - added aliases such as `CLOY`, `DOTS`, and `WWWSK`
  - added parsing for natural phrases such as `similar to Goblin` and `shows like Business Proposal`
  - added exclusion extraction for queries such as `romance without historical` or `thriller no horror`
  - added seen-title demotion support so viewed dramas can move down on later searches
  - added optional recommendation debug data for inspecting search mode, resolved title, and semantic/BM25 weights
- Added `tests/evaluation/search_regression_suite.py` for live API regression checks matching the new search semantics.
  - Covers title similarity, aliases, `similar to` phrases, exclusions, actor routing, theme routing, seen-title demotion, and browse refresh variation.
  - Current focused regression result: `10/10` checks passed against the local backend.
- Fixed `similar_to` searches so title words such as `Business` in `Business Proposal` do not pre-filter away better romance-comedy matches.
- Versioned the recommendation cache and made debug requests bypass cache so stale cached responses do not hide ranking changes during testing.
- Wired new prior config files into backend ranking for mood, relationship, setting, occupation, character archetype, ending, episode-count, release-year, and metadata signals.
- Added extra curated prior entries for common searches such as `doctor drama`, `office romance`, `cozy small town romance`, `strong female lead revenge`, `romance with happy ending`, short dramas, and long dramas.
- Expanded prior lists with additional dramas across mood, relationship, setting, occupation, ending, episode-count, character archetype, and similar-title ranking signals.
- Normalized prior config files into strict JSON and expanded the live regression suite to cover the new prior categories.
  - Current focused regression result: `17/17` checks passed against the local backend.
- Tuned ranking weights so specific prior intent, such as `soldier romance`, can beat broad single-genre romance priors.
- Added an optional ranking score debug view that exposes semantic, BM25, boost, final ranking, and personalization score details per recommendation.
- Pinned Starlette to the FastAPI-compatible range after local startup exposed an incompatible `starlette 1.x` install.
- Added a compressed README welcome GIF and reduced the displayed asset from about 4.8 MB to about 0.8 MB.
- Created a local `.venv`, ignored virtual environment folders, and updated combined requirements for Python 3.14 compatibility.
  - Updated FastAPI/Starlette, Streamlit, and pandas ranges so backend and frontend dependencies can coexist.
- Confirmed runtime analytics storage locations:
  - searches, clicks, and watchlist interactions: `backend/runtime_data/analytics/`
  - user taste profiles: `backend/runtime_data/user_profiles/`
- Organized training support scripts under `training/steps/` while keeping `training/train_pipeline.py` as the main entry point.
- Updated training step paths so generated artifacts still write to `training/training_data/`, `training/models/`, and `training/faiss_index/`.

### Repository Structure Cleanup

- Reorganized the project layout so backend ranking, training, data, scrapers, docs, and run scripts have clearer ownership.
- Moved ranking generation and ranking data under `backend/ranking/`:
  - `backend/ranking/generate_indexes.py`
  - `backend/ranking/indexes/`
  - `backend/ranking/config/`
- Renamed the main training area from `model_traning/` to `training/`.
- Moved the final dataset folder from `dataset/` to `data/final/`.
- Moved scraper code from `extra/data_scrapper/` to `scrapers/`.
- Moved older phase/history docs into `docs/archived/`.
- Added helper scripts:
  - `scripts/run_backend.ps1`
  - `scripts/run_frontend.ps1`
  - `scripts/run_accuracy.ps1`
- Updated runtime paths in backend, training scripts, and generated-index test tools to use the new structure.
- Note: the old `model_traning/` folder still contains a nested `.git` remnant after Windows blocked moving hidden Git metadata. It should be cleaned separately after confirming that nested Git history is not needed.

### Repository Cleanup Follow-Up

- Migrated old backend runtime files into `backend/runtime_data/`:
  - analytics logs under `backend/runtime_data/analytics/`
  - test user profiles under `backend/runtime_data/user_profiles/`
- Removed empty legacy folders after migration:
  - `extra/`
  - `backend/analytics_data/`
  - `backend/user_profiles/`
- Moved generated reranker training data into `training/training_data/reranker_train.csv`.
- Organized test reports into clearer buckets:
  - `tests/reports/logs/`
  - `tests/reports/debug/`
  - `tests/reports/audits/`
- Updated report scripts so future logs/debug/audit outputs use the new report folders.
- Left nested Git metadata in `training/.git/` and `frontend/.git/` untouched pending explicit approval to delete it.

### Test Folder Structure Cleanup

- Reorganized `tests/` into clearer subfolders:
  - `tests/evaluation/` for live accuracy evaluation and offline generated-index validation
  - `tests/ranking/` for ranking mode comparisons, prior experiments, weak-query reports, and generated-replacement audits
  - `tests/debug/` for single-query generated-index tracing and metadata inspection helpers
  - `tests/smoke/` for older API, personalization, filter, profile, and phase checks
  - `tests/docs/` for historical reports and improvement notes
- Moved hidden ranking experiment logs into `tests/reports/logs/`.
- Updated test scripts and helper commands to use the new paths.
- Verified the new structure with:
  - `python -m compileall tests`
  - `python tests\evaluation\validate_generated_indexes.py`

### Root Project Metadata

- Added root project files for a more professional repository setup:
  - `requirements.txt`
  - `LICENSE`
  - `pyproject.toml`
  - `CONTRIBUTING.md`
- Added combined dependency installation guidance while keeping frontend/training-specific requirement files available.
- Added Python project metadata and basic tool configuration for pytest, Ruff, and Black.


## 2026-07-23

### Frontend Alignment Phase

- Started the next natural phase after the stable backend checkpoint: frontend and full-system flow review.
- Updated `frontend/streamlit_app.py` so the UI reflects the current backend state:
  - stable backend accuracy shown as `88.50%`
  - recall@10 shown as `98.46%`
  - ranking mode described as stable curated ranking with generated fallback support
- Updated quick searches to better exercise the improved backend paths:
  - kept `romantic comedy` as a pure query instead of forcing the sidebar genre to `Romance`
  - replaced the old historical quick search with `time manipulation`
- Verified frontend syntax with:
  - `python -m compileall frontend\streamlit_app.py`
- Ran focused backend API smoke checks for frontend-critical queries:
  - `romantic comedy`
  - `time manipulation`
  - `school bullying`
  - `contract marriage`
  - `hospital setting`
- Finding from smoke checks:
  - romantic comedy, school bullying, contract marriage, and hospital setting returned strong top results
  - time manipulation still leans toward literal title matches in the top results, so it remains a useful next review area
- Tried the full live accuracy evaluator, but it timed out in the local run after the backend startup/port checks. Existing stable report numbers remain the current reference for the UI.

### Generated Replacement Accuracy Improvements

- Preserved the local checkpoint commit for generated ranking calibration:
  - commit: `e5eaf12`
  - generated replacement checkpoint before today's work: `84.55%`
- Added a `hybrid_calibrated` ranking mode in `backend/app.py`.
- Hybrid mode keeps curated genre and genre-combo priors as the primary ranking signal, then applies calibrated generated genre/combo priors as a low-weight supporting signal.
- Added hybrid mode to `tests/compare_ranking_modes.py` and `tests/experiment_ranking_priors.py`.
- Tuned hybrid generated weights to avoid overpowering curated priors:
  - `hybrid_genre`: `0.75`
  - `hybrid_genre_combo`: `0.95`
- Hybrid evaluation result:
  - curated/default baseline: `88.50%`
  - hybrid calibrated mode: `88.48%`
  - generated full replacement: `85.31%`
  - hybrid P@3 stayed `63.58%`
  - hybrid MRR stayed `0.963`
  - hybrid R@10 improved from `98.46%` to `99.07%`
- Decision: keep hybrid as an opt-in bridge mode, not the default replacement, because it improves recall with almost no overall accuracy cost while the full generated replacement is still being improved.
- Audited actor-based search replacement after genre stabilization.
- Added `SEOULMATE_ACTOR_PRIOR_SOURCE` in `backend/app.py` so actor priors can be tested independently from genre priors:
  - `curated`
  - `calibrated_generated`
  - `hybrid_calibrated`
- Added actor-focused scenarios to the ranking comparison and experiment runners:
  - `generated_actor`
  - `hybrid_actor`
  - `hybrid_genre_generated_actor`
  - `hybrid_genre_actor`
- Actor replacement result:
  - curated/default baseline: `88.50%`
  - full generated actor replacement: `86.68%`
  - generated actor P@3: `60.49%`
  - generated actor MRR: `0.932`
  - actor R@10 stayed `98.46%`
- Actor hybrid result:
  - actor hybrid overall: `88.25%`
  - actor hybrid P@3 stayed `63.58%`
  - actor hybrid MRR stayed `0.963`
  - actor hybrid R@10 stayed `98.46%`
- Combined genre+actor hybrid result:
  - overall: `88.23%`
  - P@3: `63.58%`
  - R@10: `99.07%`
  - MRR: `0.963`
- Tested a data-driven actor calibration change that moved training-title frequency ahead of rating and penalized newer/sequel titles.
- Rejected that actor calibration change because generated actor P@3 dropped from `60.49%` to `59.26%`, even though MRR improved from `0.932` to `0.948`.
- Decision: do not replace curated actor priors yet. Keep actor generated/hybrid modes as diagnostic opt-in modes only.
- Current actor bottleneck: generated actor ranking over-prioritizes broad filmography relevance and newer/high-rated entries, while curated priors better capture the iconic dramas users expect for actor-name searches.
- Revisited actor generated replacement after theme audit.
- Added an actor-specific training-query frequency signal to generated actor calibration.
- Added narrow actor noise penalties for sequel/special titles and very recent/future titles:
  - season/part sequel titles
  - `2025+` releases
  - smaller penalty for `2024` releases
- Result after regenerated actor index:
  - full generated actor replacement: `86.68%` -> `86.69%`
  - generated actor P@3 stayed `60.49%`
  - generated actor R@10 stayed `98.46%`
  - generated actor MRR improved from `0.932` to `0.941`
- Decision: keep the narrow actor noise penalty because it improves first-relevant ranking without hurting P@3 or recall, but generated actor replacement is still not ready to replace curated actor priors.
- Audited theme-based search replacement after actor audit.
- Added `SEOULMATE_THEME_PRIOR_SOURCE` in `backend/app.py` so theme priors can be tested independently:
  - `curated`
  - `calibrated_generated`
  - `hybrid_calibrated`
- Loaded `calibrated_theme_index.json` in the backend for explicit generated/hybrid theme experiments.
- Added theme-focused scenarios to the ranking comparison and experiment runners:
  - `generated_theme`
  - `hybrid_theme`
  - `hybrid_genre_theme`
- Added theme-aware generated calibration in `backend/generate_indexes.py` using metadata focus/off-topic terms for themes such as food, time travel, contract marriage, rich CEO romance, legal corruption, supernatural hotel, startup workplace, and healing slice of life.
- Tested a training-query frequency signal for generated theme calibration and rejected it because generated theme accuracy dropped from `83.16%` to `78.38%`.
- Restored default curated theme behavior so generated theme candidates do not leak into default mode as fallbacks.
- Theme replacement result:
  - curated/default baseline: `88.50%`
  - full generated theme replacement: `83.16%`
  - generated theme P@3: `54.32%`
  - generated theme R@10: `88.27%`
  - generated theme MRR: `0.862`
- Theme hybrid result:
  - tuned `hybrid_theme` weight: `0.30`
  - hybrid theme overall: `88.50%`
  - hybrid theme P@3: `63.58%`
  - hybrid theme R@10: `98.46%`
  - hybrid theme MRR: `0.963`
- Combined genre+theme hybrid result from ranking comparison:
  - P@3: `63.58%`
  - R@10: `99.07%`
  - MRR: `0.963`
- Decision: do not replace curated theme priors yet. Keep low-weight theme hybrid as a neutral opt-in diagnostic mode while theme indexes are improved further.
- Current theme bottleneck: generated theme indexes match literal metadata terms, but they do not yet understand the expected canonical dramas for broad story-intent queries like `restaurant food`, `law firm corruption`, `ghost supernatural hotel`, `time travel`, and `workplace startup`.
- Improved generated theme index coverage and canonical ranking.
- Added broader metadata bridge terms for theme candidate generation:
  - food: restaurant setting, pub
  - time travel: different timelines, time altering, time manipulation
  - contract marriage: contract relationship, marriage of convenience, cohabitation, married life
  - rich CEO romance: boss-employee, successful male lead, rich man
  - legal corruption: law school, attorney, courtroom, courtroom setting, justice
  - startup workplace: start-ups, tech, artificial intelligence
  - healing slice of life: depression, community, everyday, omnibus
- Added theme genre-preference scoring and canonicality scoring using title frequency, alias breadth, rating, and episode sanity.
- Increased calibrated theme index depth from `20` to `40` titles per theme so recovered candidates can reach backend scoring.
- Generated theme replacement improved:
  - overall: `83.16%` -> `84.09%`
  - P@3: `54.32%` -> `56.17%`
  - R@10: `88.27%` -> `91.36%`
  - MRR: `0.862` -> `0.865`
- Theme hybrid remained neutral:
  - overall: `88.50%`
  - P@3: `63.58%`
  - R@10: `98.46%`
  - MRR: `0.963`
- Remaining theme gap: `restaurant food` still lacks enough metadata coverage for `Itaewon Class` and `Wok of Love`, and `workplace startup` still misses `Misaeng`.
- Added explicit curated-first generated fallback modes:
  - `SEOULMATE_GENRE_PRIOR_SOURCE=fallback_generated`
  - `SEOULMATE_THEME_PRIOR_SOURCE=fallback_generated`
- Fallback behavior:
  - curated priors remain primary
  - generated calibrated indexes are used only when the curated prior is missing for that detected signal
  - fallback generated boosts use lower weights than curated priors
- Added fallback scenarios to ranking comparison and experiment runners:
  - `fallback_genre`
  - `fallback_theme`
  - `fallback_genre_theme`
- Fallback evaluation:
  - baseline: P@3 `63.58%`, R@10 `98.46%`, MRR `0.963`
  - fallback theme: P@3 `63.58%`, R@10 `98.46%`, MRR `0.963`
  - fallback genre: P@3 `63.58%`, R@10 `97.84%`, MRR `0.963`
  - fallback genre+theme: P@3 `63.58%`, R@10 `97.84%`, MRR `0.963`
- Decision:
  - keep actor's existing curated-first generated fallback
  - keep theme fallback as a safe opt-in mode
  - do not use genre fallback as the recommended bridge because it reduces recall
  - keep genre hybrid as the better genre bridge because it improves R@10 to `99.07%`
- Improved explicit keyword filtering and keyword-based ranking.
- Loaded `calibrated_keyword_index.json` in the backend.
- Added keyword filter expansion for common user phrases:
  - healing / comfort / slice of life
  - time travel / time slip / time loop / time manipulation
  - strong female lead / smart female lead
  - slow burn romance / slow romance
  - contract marriage / contract relationship / marriage of convenience
  - school bullying / bullying / school violence
  - doctor / hospital setting
  - lawyer / attorney / courtroom setting
- Added calibrated keyword-index fallback only when direct keyword filtering finds no matches.
- Added keyword ranking boosts for explicit `keywords=` filters so keyword-filtered searches are ranked by keyword relevance instead of only the free-text title query.
- Fixed recommendation cache keys so keyword, description, rating count, screenwriter, sorting, and similar-to filters are included in cache identity.
- Before this fix, different keyword filters could reuse the same cached response for the same title query.
- Keyword check examples after the fix:
  - `keywords=contract marriage` returns `Fated to Love You`, `Marriage Contract`, `Would You Marry Me?`, `Full House`
  - `keywords=time manipulation` returns `My Love from the Star`, `The Light in Your Eyes`, `Tomorrow with You`
  - `keywords=school bullying` returns `The Glory`, `Weak Hero Class 2`, `The King of Pigs`, `My ID Is Gangnam Beauty`
  - `keywords=hospital setting` returns `The Trauma Code: Heroes on Call`, `Doctor Cha`, `Yong Pal`
- Baseline accuracy after keyword changes stayed stable:
  - overall: `88.50%`
  - P@3: `63.58%`
  - R@10: `98.46%`
  - MRR: `0.963`
- Added generated `drama|medical` combo ordering calibration in `backend/generate_indexes.py`.
- The medical rule boosted doctor/hospital/medical-school protagonist signals and improved generated top-3 precision.
- Medical tradeoff:
  - P@3 improved, but some medical recall dropped because `Hospital Playlist` moved below top 10 in focused medical debugging
  - overall generated replacement still improved from `84.55%` to `84.91%`
- Followed the plain thriller improvement plan.
- Added plain `Thriller` calibration terms for death-game, survival, competition, massacre, debt, suspense, mystery, investigation, corruption, crime-solving, murder, serial-killer, psychological, law, and prosecutor signals.
- Added plain `Thriller` off-topic penalties for motherhood/mother-daughter melodrama, tearjerker, grim-reaper/underworld/afterlife, suicide-prevention, fantasy, supernatural power, romance, revenge, and school-bullying drift.
- Fixed generated-index calibration source quality:
  - calibrated actor, genre, keyword, and theme indexes now rank from raw candidate pools
  - simple generated indexes still use their existing truncated top-title outputs
  - this lets calibrated genre ranking recover titles that were previously cut out before calibration, such as `Squid Game` for plain `Thriller`
- Focused `thriller` debug improved:
  - previous generated/final best expected rank: `2`
  - updated generated/final best expected rank: `1`
  - final top 10 now contains `Stranger`, `Squid Game`, and `Signal`
- `crime thriller` remained `ok_top3`.
- Live generated replacement improved:
  - previous full generated replacement: `84.91%`
  - updated full generated replacement: `85.31%`
  - generated replacement P@3: `56.17%` -> `56.79%`
  - generated replacement R@10: stayed `94.14%`
  - generated replacement MRR: `0.938` -> `0.948`
  - curated/default baseline remains `88.50%`
- Generated replacement audit changed:
  - `first_relevant_rank_regression`: `4` -> `3`
  - `noisy_titles_above_expected`: `4` -> `3`
  - `expected_missing_from_generated_top10`: `5` -> `6`
- Tested a second historical/sageuk split calibration and rejected it.
- The attempted rule added serious historical-political/survival signals and tried to include serious historical titles without a literal `Drama` genre in the generated `drama|historical` combo.
- Focused inspection showed the rule was harmful:
  - plain `Historical` became dominated by generic royal/palace titles
  - `Mr. Sunshine` dropped out of the top historical list
  - `Kingdom` and `Empress Ki` still did not recover into the useful top ranks
  - `The Red Sleeve` remained too low
- Reverted the historical/sageuk calibration before running full accuracy.
- Restored the safe generated historical behavior:
  - `historical` focused debug remains `ok_top3`
  - `Mr. Sunshine` remains rank `1`
  - full generated replacement checkpoint remains `85.31%`
- Tested a coverage-only historical bridge for `drama|historical` and rejected it.
- The bridge only added virtual `Drama` combo membership for strict historical patterns:
  - `Historical + Political`
  - `Historical + Horror/Thriller` with survival/zombie/epidemic signals
  - `Historical + Romance/Melodrama` with dynasty/political signals
- Result:
  - focused `historical` and `sageuk royal drama` remained `ok_top3`
  - `Kingdom` only reached raw `drama|historical` rank `55`
  - `Empress Ki` only reached raw `drama|historical` rank `57`
  - neither title entered the useful generated top 30
- Reverted the bridge before full accuracy testing because it did not solve the missing-title problem and added complexity without measurable benefit.
- Current generated replacement checkpoint remains `85.31%`.

## 2026-07-22

### Ranking Prior Experiment Runner

- Added configurable ranking-prior weights to `backend/ranking_config/curated_priors.json`.
- Updated `backend/app.py` so genre, theme, actor, and generated-index boost weights can be changed through JSON instead of code edits.
- Added `SEOULMATE_PRIOR_WEIGHTS` support for temporary experiment overrides.
- Added `SEOULMATE_GENRE_PRIOR_SOURCE` support to test curated genre priors against calibrated generated genre indexes.
- Added `SEOULMATE_PORT` and `SEOULMATE_RELOAD` support so isolated experiment backend instances can be launched safely.
- Added `tests/experiment_ranking_priors.py` to run controlled ranking experiments against separate backend ports.
- Added `tests/report_weak_queries.py` plus generated reports in `tests/reports/` to identify weak queries by category, metrics, analyzer output, and likely failure reason.
- Experiment results showed curated priors are important:
  - removing genre priors dropped overall accuracy by `8.07` points
  - removing actor priors dropped overall accuracy by `5.20` points
  - removing theme priors dropped overall accuracy by `4.74` points
- First genre-replacement experiment showed calibrated generated genre priors are useful but not ready to replace curated genre priors:
  - curated genre baseline: `88.50%`
  - no genre priors: `80.28%`
  - calibrated generated genre replacement: `81.62%`
  - softer calibrated generated genre replacement: `82.36%`
  - stronger calibrated generated genre replacement: `79.85%`
- Improved generated genre-combo calibration in `backend/generate_indexes.py`.
- Added metadata-based focus rules for high-signal combo patterns:
  - `comedy|romance`
  - `fantasy|romance`
- Regenerated `backend/generated_indexes/calibrated_genre_combo_index.json`.
- Offline generated genre-combo validation improved:
  - Hit@3: `81.82%` -> `90.91%`
  - Hit@10: stayed `100.00%`
- Live replacement experiment improved only slightly because single-genre generated indexes remain the bottleneck:
  - previous best generated replacement: `82.50%`
  - updated best generated replacement: `82.51%`
- Improved single-genre generated calibration for noisy genre keys including `Medical`, `Law`, `Food`, `Business`, `Crime`, and `Revenge`.
- Added targeted metadata focus scoring for those noisy genre keys while keeping the original scoring for broader genres where focus scoring was harmful.
- Regenerated `backend/generated_indexes/calibrated_genre_index.json`.
- Offline single-genre generated validation improved:
  - Hit@10: `69.23%` -> `76.92%`
  - Hit@3: stayed `61.54%`
- Live generated genre replacement improved:
  - previous best full generated genre replacement: `82.37%`
  - updated best full generated genre replacement: `82.48%`
  - Recall@10 improved to `90.43%`
- Added `tests/compare_ranking_modes.py`.
- Generated side-by-side reports:
  - `tests/reports/ranking_mode_comparison.json`
  - `tests/reports/ranking_mode_comparison.md`
- The comparison report shows the main generated-replacement regressions are broad genre top-3 ordering cases:
  - `historical`
  - `school drama`
  - `thriller`
  - `romantic comedy`
  - `zombie drama`
  - `medical drama`
  - `office romance`
- The current generated replacement finds many correct titles by top 10, but still ranks newer/noisier candidates above expected high-signal titles in top 3.
- Added `title_reliability_score()` to `backend/generate_indexes.py`.
- Reliability scoring now uses metadata signals instead of manual title lists:
  - rating bands
  - training-data title frequency
  - normal episode-count range
  - penalties for specials, variety/reality/documentary entries, short web series, sequels, and very recent releases
- Applied reliability scoring to calibrated generated genre and genre-combo indexes.
- Regenerated:
  - `backend/generated_indexes/calibrated_genre_index.json`
  - `backend/generated_indexes/calibrated_genre_combo_index.json`
- Offline generated validation improved:
  - single-genre Hit@3: `61.54%` -> `69.23%`
  - single-genre Hit@10: stayed `76.92%`
  - genre-combo Hit@1: `27.27%` -> `54.55%`
  - genre-combo Hit@3: stayed `90.91%`
  - genre-combo Hit@10: stayed `100.00%`
- Live generated replacement improved:
  - previous best full generated genre replacement: `82.48%`
  - updated best full generated genre replacement: `82.84%`
  - Recall@10: `91.67%`
  - MRR: `0.917`
- Added an experimental generated query-pattern profile layer in `backend/app.py`.
- Added `SEOULMATE_ENABLE_QUERY_PROFILES=1` as an opt-in flag for profile experiments.
- Added experiment scenarios:
  - `generated_genre_soft_profiles`
  - `generated_combo_only_soft_profiles`
- Query-pattern profiles are disabled by default because the measured results were worse than the current generated replacement:
  - best generated replacement without profiles: `82.84%`
  - generated genre soft with profiles: `81.49%`
  - generated combo-only soft with profiles: `81.45%`
- Conclusion:
  - metadata profile matching is useful as an experiment path
  - current profile boosts are too blunt for live/generated replacement ranking
  - the active generated replacement baseline remains `82.84%`
- Added steeper rank decay for generated genre priors in `backend/app.py`.
- Curated priors keep their existing decay, while generated genre/combo priors now make index ordering matter more strongly.
- Live full generated replacement improved:
  - previous best: `82.84%`
  - updated best: `82.90%`
- Refreshed `tests/reports/ranking_mode_comparison.json` and `tests/reports/ranking_mode_comparison.md` after the rank-decay update.
- Added `tests/audit_generated_replacement.py` to classify the gap between curated priors and full generated replacement.
- Generated audit reports:
  - `tests/reports/generated_replacement_audit.json`
  - `tests/reports/generated_replacement_audit.md`
- Audit moved replacement work from trial-and-error to failure-class tracking.
- Current generated replacement audit:
  - curated baseline: P@3 `63.58%`, R@10 `98.46%`, MRR `0.963`
  - generated replacement: P@3 `51.85%`, R@10 `91.05%`, MRR `0.915`
- Top failure classes:
  - `expected_ranked_too_low`: `11`
  - `top3_precision_regression`: `11`
  - `expected_missing_from_generated_top10`: `7`
  - `first_relevant_rank_regression`: `6`
  - `noisy_titles_above_expected`: `6`
- Highest-impact generated replacement gaps are genre queries:
  - `school drama`
  - `zombie drama`
  - `thriller`
  - `romantic comedy`
  - `historical`
  - `sageuk royal drama`
- Next evidence-based fix order:
  - first improve generated index coverage for expected titles missing from top 10
  - then improve generated top-3 ordering for expected titles already present
  - then add general negative signals for noisy titles above expected titles
- Improved virtual-genre handling in `backend/generate_indexes.py`.
- Metadata-derived virtual genres are now added to single-genre generated indexes, so titles with strong keyword/description evidence can be recovered even when the scraped `Genre` field is incomplete.
- Added virtual `youth` genre extraction from metadata terms such as `school`, `student`, `high school`, `campus`, and `youth`.
- Scoped virtual genres used for combo generation to avoid damaging the already-strong generated combo index.
- Regenerated generated genre indexes and refreshed comparison/audit reports.
- Offline generated index validation improved:
  - single-genre Hit@3: `69.23%` -> `84.62%`
  - single-genre Hit@10: `76.92%` -> `84.62%`
  - genre-combo Hit@10: restored to `100.00%`
- Live generated replacement did not improve yet:
  - generated replacement remained P@3 `51.85%`, R@10 `91.05%`, MRR `0.915`
  - this means the next bottleneck remains API ranking/retrieval interaction, not only offline index contents
- Tested generated-aware backend pre-filtering in `backend/app.py`.
- Added a genre matcher that can include generated-index genre membership during generated replacement modes.
- Refreshed ranking comparison and generated replacement audit after the pre-filter change.
- Result:
  - generated replacement stayed P@3 `51.85%`, R@10 `91.05%`, MRR `0.915`
  - candidate filtering is not the main remaining bottleneck
  - remaining bottleneck is generated prior scoring/top-3 ordering inside the live backend
- Disabled generated-index live nudges by default because the experiment showed a tiny improvement without them:
  - baseline with generated nudges: `88.49%`
  - generated nudges disabled: `88.50%`
- Kept generated indexes available for offline discovery and future calibrated experiments.
- Added `tests/debug_generated_query.py` for single-query generated replacement tracing.
- The debugger compares query analyzer output, calibrated generated index candidates, and final `/recommend` top 10 results.
- Generated first single-query reports:
  - `tests/reports/debug_generated_query_school_drama.json`
  - `tests/reports/debug_generated_query_school_drama.md`
- `school drama` debug result:
  - analyzer detected `Drama` and `Youth`
  - generated index contained expected title `True Beauty` at generated candidate rank `8`
  - final generated-mode API top 10 contained none of the expected titles
  - classification: `lost_between_generated_index_and_final_api`
- New bottleneck is clearer:
  - generated indexes can now surface some expected titles
  - final live ranking still lets broad/noisy candidates outrank expected school-drama titles
  - next improvement should focus on converting generated index rank into stronger, safer final ranking signals
- Added generated combo-prior gating in `backend/app.py`.
- In generated replacement mode, when a multi-genre generated combo prior matches the query, single generated genre priors are skipped for that query.
- Reason:
  - generated combo indexes are more specific than broad single generated genre lists
  - this prevents broad `Drama` and noisy virtual genres like `Youth` from overpowering a matched combo such as `drama|youth`
- Focused `school drama` debug improved:
  - before: expected title was missing from final top 10
  - after: `True Beauty` reached final API rank `8`
  - classification moved from `lost_between_generated_index_and_final_api` to `final_ranking_too_low`
- Full generated replacement accuracy changed slightly:
  - previous best full generated replacement: `82.90%`
  - updated full generated replacement: `82.91%`
  - curated/default baseline remains `88.50%`
- Refreshed:
  - `tests/reports/ranking_mode_comparison.json`
  - `tests/reports/ranking_mode_comparison.md`
  - `tests/reports/generated_replacement_audit.json`
  - `tests/reports/generated_replacement_audit.md`
- Added metadata calibration for the generated `drama|youth` combo index in `backend/generate_indexes.py`.
- The new combo rule boosts broad school-drama signals such as `high school`, `school setting`, `student`, `romance`, `comedy`, `coming of age`, `friendship`, `love triangle`, and `adapted from a webtoon`.
- The same rule down-ranks noisier youth-drama signals such as action, violence, gang/fighter terms, fantasy, time travel, historical/martial-law terms, `web series`, and `short length series`.
- Regenerated generated indexes after the calibration update.
- Focused `school drama` debug improved again:
  - previous generated/final expected rank: `4`
  - updated generated/final expected rank: `3`
  - classification moved to `ok_top3`
- Offline generated combo validation improved:
  - calibrated genre-combo Hit@3: `90.91%` -> `100.00%`
  - calibrated genre-combo Hit@10: stayed `100.00%`
- Live generated replacement improved:
  - previous full generated replacement: `82.91%`
  - updated full generated replacement: `83.12%`
  - generated replacement P@3: `51.85%` -> `52.47%`
  - generated replacement MRR: `0.917` -> `0.921`
  - curated/default baseline remains `88.50%`
- Tested a historical/sageuk calibration rule and rejected it after focused debugging.
- The rejected historical rule over-favored generic palace/royal titles and harmed key expectations:
  - `historical` fell from expected rank `1` to rank `5`
  - `sageuk royal drama` lost expected titles from final top 10
- Removed the harmful historical rule before keeping the next improvement.
- Added safer metadata calibration for the generated `fantasy|romance` combo index.
- The fantasy-romance rule now boosts stronger fantasy-romance signals such as `alchemy`, `souls`, `dokkaebi`, `goblin`, `ghost-seeing`, `immortality`, `hotel`, `curse`, `deity`, and `elemental power`.
- The same rule down-ranks procedural/noisy signals such as mystery, investigation, police, murder, and magician terms.
- Focused `fantasy romance` debug improved:
  - previous generated/final expected rank: `4`
  - updated generated/final expected rank: `2`
  - classification moved to `ok_top3`
- Guard checks remained stable:
  - `school drama`: still `ok_top3`, expected rank `3`
  - `historical`: restored to `ok_top3`, expected rank `1`
- Live generated replacement improved again:
  - previous full generated replacement: `83.12%`
  - updated full generated replacement: `83.67%`
  - generated replacement P@3: `52.47%` -> `53.70%`
  - generated replacement R@10: `91.05%` -> `91.67%`
  - generated replacement MRR: `0.921` -> `0.926`
  - curated/default baseline remains `88.50%`
- Generated replacement audit failure counts improved:
  - `expected_ranked_too_low`: `11` -> `10`
  - `top3_precision_regression`: `11` -> `10`
  - `expected_missing_from_generated_top10`: `8` -> `7`
  - `first_relevant_rank_regression`: `6` -> `5`
  - `noisy_titles_above_expected`: `6` -> `5`
- Improved zombie/thriller generated coverage.
- Updated `backend/query_analyzer.py` so `zombie`, `zombies`, and `apocalypse` now map to both `Thriller` and `Horror`.
- Added virtual generated-index `horror` signals for metadata terms such as zombie, zombie apocalypse, epidemic, infectious disease, virus, quarantine, gore, and monster.
- Added generated combo calibration for zombie/thriller paths:
  - `drama|horror|thriller`
  - `horror|thriller`
  - `drama|thriller`
- The zombie/thriller combo calibration boosts survival outbreak signals and down-ranks revenge, school-bullying, grim-reaper, legal/prosecutor, and melodrama drift.
- Focused `zombie drama` debug improved final ranking:
  - analyzer now detects `Horror`, `Drama`, and `Thriller`
  - final API top 5 now includes `All of Us Are Dead`, `Happiness`, and `Kingdom`
  - best expected rank improved to `2`
- Live generated replacement improved:
  - previous full generated replacement: `83.67%`
  - updated full generated replacement: `84.11%`
  - generated replacement P@3: `53.70%` -> `54.32%`
  - generated replacement R@10: `91.67%` -> `92.90%`
  - generated replacement MRR: `0.926` -> `0.929`
  - curated/default baseline remains `88.50%`
- Generated replacement audit improved:
  - `expected_missing_from_generated_top10`: `7` -> `6`
- Improved generated `comedy|romance` calibration for romantic-comedy coverage.
- Expanded metadata focus terms for office/CEO/secretary/business romcoms, strong-woman romcoms, supernatural-strength romcoms, rich male lead, workplace, fake/contract relationship, and love-triangle signals.
- Added metadata penalties for spin-off, side-story, special, short-length, fantasy, melodrama, thriller, revenge, and historical drift inside the generated `comedy|romance` combo.
- Focused `romantic comedy` debug improved:
  - previous best expected rank: `2`
  - updated best expected rank: `1`
  - final top 4 now includes `Business Proposal`, `Strong Woman Do Bong Soon`, and `What's Wrong with Secretary Kim`
  - noisy `Spice up Our Love` no longer appears above the expected titles
- Guard checks remained stable:
  - `zombie drama`: still `ok_top3`
  - `fantasy romance`: still `ok_top3`
- Live generated replacement improved:
  - previous full generated replacement: `84.11%`
  - updated full generated replacement: `84.55%`
  - generated replacement P@3: `54.32%` -> `54.94%`
  - generated replacement R@10: `92.90%` -> `94.14%`
  - generated replacement MRR: `0.929` -> `0.938`
  - curated/default baseline remains `88.50%`
- Generated replacement audit improved:
  - `expected_missing_from_generated_top10`: `6` -> `5`
  - `first_relevant_rank_regression`: `5` -> `4`
  - `noisy_titles_above_expected`: `5` -> `4`
- Tested another school-drama coverage expansion and rejected it.
- The rejected school tweak over-rewarded small web/school series and dropped the best expected school-drama rank from `3` to `10`.
- Removed that school tweak before keeping the next improvement.
- Added generated `drama|medical` combo ordering calibration.
- The medical rule boosts doctor/hospital/medical-school protagonist signals such as doctor leads, surgeons, university hospital, medical skills, autistic/savant medical leads, rare conditions, and starting-over hospital stories.
- The same rule down-ranks action/rescue, hospice/terminal-illness, mental-health, fantasy, and ghost drift inside generated medical-drama combos.
- Focused `medical drama` debug improved top-3 ordering:
  - previous top 3: `Hospital Playlist`, `Daily Dose of Sunshine`, `Dr. Romantic`
  - updated top 3: `Good Doctor`, `Doctor Cha`, `Brain`
  - `Doctor Cha` and `Good Doctor` moved into top 3
- Tradeoff:
  - `Hospital Playlist` dropped below top 10 in the focused medical debug
  - generated replacement recall decreased in the comparison
  - precision gain outweighed the recall loss in the overall score
- Live generated replacement improved:
  - previous full generated replacement: `84.55%`
  - updated full generated replacement: `84.91%`
  - generated replacement P@3: `54.94%` -> `56.17%`
  - generated replacement R@10: `94.14%` -> `92.90%`
  - generated replacement MRR: stayed `0.938`
  - curated/default baseline remains `88.50%`

### Curated Ranking Config Extraction

- Moved trusted curated ranking priors out of `backend/app.py`.
- Added `backend/ranking_config/curated_priors.json`.
- The config now stores:
  - theme priors
  - theme-combination priors
  - genre priors
  - genre-combination priors
  - actor priors
- Updated `backend/app.py` to load curated priors from JSON and convert combo keys such as `Drama|Revenge` back into tuple keys for existing ranking logic.
- Kept generated indexes separate from curated priors:
  - generated indexes remain broad/offline discovery data
  - curated config remains the trusted live ranking layer
- Verification:
  - `python -m compileall backend\app.py`
  - `python tests\validate_generated_indexes.py`
  - `python tests\evaluate_accuracy.py`
- Live accuracy preserved after refactor:
  - Overall accuracy: `88.49%`
  - Search Precision@3: `63.58%`
  - Search Recall@10: `98.46%`
  - Search MRR: `0.963`


## 2026-07-20

### Calibrated Actor Index Improvement

- Improved `calibrated_actor_index.json` ordering in `backend/generate_indexes.py`.
- Added cast-position scoring so lead roles rank above secondary/cameo appearances before rating and frequency are considered.
- Made `tests/validate_generated_indexes.py` alias-aware so titles like `Goblin` and `Guardian: The Lonely and Great God` are evaluated as the same drama where aliases exist.
- Updated validator recommendations to prefer the strongest top-rank index when Hit@10 is tied.
- Regenerated generated index files from `model_traning/faiss_index/meta.pkl`.
- Offline actor-index validation improved:
  - `actor_index.json`: Hit@1 `50.00%`, Hit@3 `70.00%`, Hit@10 `100.00%`
  - `calibrated_actor_index.json`: Hit@1 `70.00%`, Hit@3 `100.00%`, Hit@10 `100.00%`
- Live benchmark remained stable:
  - Overall accuracy: `88.14%`
  - Search Precision@3: `62.96%`
  - Search Recall@10: `97.22%`
  - Search MRR: `0.954`
- Conclusion:
  - calibrated actor index is now good enough for cautious actor fallback experiments
  - curated actor priors should still stay active until a full replacement beats the benchmark

### Calibrated Genre Index Improvement

- Improved offline validation of multi-genre generated index candidates in `tests/validate_generated_indexes.py`.
- Multi-key genre queries now rank titles that appear under multiple detected genre keys ahead of titles that only match one genre key.
- Increased `calibrated_genre_index.json` coverage from top 20 to top 40 titles per genre in `backend/generate_indexes.py`.
- Regenerated generated index files from `model_traning/faiss_index/meta.pkl`.
- Offline genre-index validation improved:
  - Previous `calibrated_genre_index.json`: Hit@3 `46.15%`, Hit@10 `69.23%`, Hit@20 `84.62%`
  - Current `calibrated_genre_index.json`: Hit@3 `61.54%`, Hit@10 `69.23%`, Hit@20 `84.62%`
- Conclusion:
  - calibrated genre index ordering is better for combined genre queries
  - genre index is still not ready to replace curated genre priors because Hit@3 remains below the safe threshold
  - next improvement should focus on query-specific genre combinations such as romantic comedy, fantasy romance, revenge drama, and sageuk/royal drama

### Generated Genre Combo Index

- Added `calibrated_genre_combo_index.json` generation from metadata genre pairs.
- Added query-specific combo validation in `tests/validate_generated_indexes.py`.
- Added training-triplet combo frequency so anchors like `romantic comedy` and `medical drama` can influence combo-title ordering.
- Added virtual combo labels for metadata-backed themes, starting with `revenge`, so queries such as `revenge drama` can be represented even when `Revenge` is stored as a keyword/theme instead of a formal genre.
- Regenerated generated index files from `model_traning/faiss_index/meta.pkl`.
- Generated combo index coverage:
  - `321` genre-combo keys
- Offline combo-index validation:
  - `calibrated_genre_combo_index.json`: Hit@1 `9.09%`, Hit@3 `63.64%`, Hit@10 `90.91%`, Hit@20 `90.91%`
- Conclusion:
  - generated combo index is now useful for recall/debug and future candidate expansion
  - combo index should not be used for top-rank boosting yet because Hit@3 is still below the safe threshold
  - remaining weak area: `crime thriller`, where generated ordering favors adjacent action/crime titles before `Signal`, `Stranger`, and `Beyond Evil`

### Crime Thriller Combo Calibration

- Improved `calibrated_genre_combo_index.json` for `crime|thriller` queries.
- Added metadata-derived virtual `crime` labels so dramas with crime-solving keywords can be represented even when `Crime` is not stored as a formal genre.
- Added crime/thriller focus scoring for investigation, detective, murder, serial-killer, corruption, psychological, suspense, and cold-case signals.
- Added light penalties for action-heavy crime metadata so action/noir titles do not dominate investigation-focused crime thriller queries.
- Fixed combo scoring so virtual labels are used both when collecting candidates and when checking exact combo matches.
- Regenerated generated index files from `model_traning/faiss_index/meta.pkl`.
- `crime|thriller` top results improved to:
  - `Beyond Evil`
  - `Signal`
  - `Stranger`
- Offline combo-index validation improved:
  - Previous `calibrated_genre_combo_index.json`: Hit@3 `63.64%`, Hit@10 `90.91%`
  - Current `calibrated_genre_combo_index.json`: Hit@3 `72.73%`, Hit@10 `100.00%`
- Conclusion:
  - combo index is now stronger for recall and analysis
  - still keep it out of live top-rank boosting until Hit@3 reaches the safe threshold around `80.00%`

### Genre Combo Near-Miss Tuning

- Added near-miss reporting to `tests/validate_generated_indexes.py`.
- Near misses now show cases where expected titles are present but ranked between positions 4 and 10.
- Used near-miss output to tune `business|romance` without hardcoding expected titles.
- Added a narrow off-topic penalty for `business|romance` so fantasy, revenge, sports, and time-travel titles do not outrank cleaner office/workplace romance matches.
- Regenerated generated index files from `model_traning/faiss_index/meta.pkl`.
- Offline combo-index validation improved:
  - Previous `calibrated_genre_combo_index.json`: Hit@3 `72.73%`, Hit@10 `100.00%`
  - Current `calibrated_genre_combo_index.json`: Hit@3 `81.82%`, Hit@10 `100.00%`
- Conclusion:
  - generated combo index has reached the cautious fallback threshold
  - next step can be a small backend candidate-expansion experiment, guarded by full accuracy evaluation
  - remaining combo near misses are `romantic comedy` and `school drama`

### Backend Genre Combo Boost Trial

- Tested a conservative live backend boost using `calibrated_genre_combo_index.json`.
- Trial behavior:
  - loaded the generated combo index in `backend/app.py`
  - boosted only already-retrieved titles
  - limited boost to top 5 combo-index titles
  - used a small generated-index multiplier
- Trial result:
  - Overall accuracy dropped from `88.14%` to `87.98%`
  - Search Precision@3 dropped from `62.96%` to `62.35%`
  - Search MRR improved slightly from `0.954` to `0.963`, but the overall score still regressed
- Decision:
  - disabled the live combo boost
  - kept `calibrated_genre_combo_index.json` for offline validation, recall analysis, and future candidate-expansion experiments
- Clean rerun after disabling the live boost restored:
  - Overall accuracy: `88.14%`
  - Search Precision@3: `62.96%`
  - Search Recall@10: `97.22%`
  - Search MRR: `0.954`

### Revenge Drama Ranking Improvement

- Improved the weak `revenge drama` live query without enabling generated combo boosts.
- Added a standalone `revenge` theme prior in `backend/app.py`.
- Added a focused `Drama + Revenge` genre-combination prior.
- Used dataset titles that are already present in metadata:
  - `The Glory`
  - `The Penthouse: War in Life`
  - `Eve`
  - `Revenge of Others`
- Live evaluator improvement:
  - `revenge drama` changed from low-recall literal revenge results to top results `The Glory`, `The Penthouse: War in Life`, and `Revenge of Others`
  - Overall accuracy improved from `88.14%` to `88.49%`
  - Search Precision@3 improved from `62.96%` to `63.58%`
  - Search Recall@10 improved from `97.22%` to `98.46%`
  - Search MRR improved from `0.954` to `0.963`
- Conclusion:
  - targeted curated priors still outperform broad generated boosts for high-impact weak queries
  - generated indexes remain useful for finding weak cases and candidate ideas, but live ranking should use narrow validated rules

### Generated Index Offline Validation

- Added offline generated-index validation:
  - `tests/validate_generated_indexes.py`
- The validator checks generated indexes against evaluator ground-truth titles without calling the backend API.
- Added validation metrics:
  - Hit@1
  - Hit@3
  - Hit@10
  - Hit@20
  - sample misses for debugging
- Validated raw and calibrated indexes:
  - actor
  - genre
  - theme
  - keyword
- Current validation findings:
  - `actor_index.json`: Hit@3 `70.00%`, Hit@10 `100.00%`
  - `calibrated_actor_index.json`: Hit@3 `80.00%`, Hit@10 `90.00%`
  - `genre_index.json`: Hit@3 `30.77%`, Hit@10 `61.54%`
  - `calibrated_genre_index.json`: Hit@3 `38.46%`, Hit@10 `61.54%`
  - `theme_index.json`: Hit@3 `27.27%`, Hit@10 `54.55%`
  - `calibrated_theme_index.json`: Hit@3 `27.27%`, Hit@10 `36.36%`
  - `calibrated_keyword_index.json`: Hit@3 `8.33%`, Hit@10 `29.17%`
- Conclusion:
  - actor indexes are useful for recall/debug and fallback coverage
  - genre, theme, and keyword indexes are not ready for live ranking
  - future tuning should improve generated index quality offline before wiring stronger live boosts

## 2026-07-16

### Calibrated Genre Index Trial

- Added `calibrated_genre_index.json` generation from metadata.
- Added genre-title calibration using:
  - title/genre filtering for specials, recaps, variety, documentaries, and related non-primary content
  - sequel/part/season downranking
  - rating
  - episode count
  - title frequency from existing training pairs/triplets
- Tested using calibrated generated genre priors as fallback for uncovered genres.
- Result: generated genre fallback reduced ranking quality for several mixed-intent queries.
- Disabled generated genre fallback from live scoring.
- Kept `calibrated_genre_index.json` available for future offline tuning.
- Restored benchmark result:
  - Overall accuracy: `88.14%`
  - Genre Precision@3: `87.18%`
  - Genre Recall@10: `92.31%`
  - Genre MRR: `0.885`
- Conclusion:
  - generated genre indexes are useful for analysis, but not reliable enough yet as ranking priors
  - genre replacement needs query-specific calibration, especially for business/workplace, revenge, historical/sageuk, and broad romance/comedy

### Calibrated Actor Index Trial

- Added `calibrated_actor_index.json` generation from metadata.
- Added actor-title calibration using:
  - title/genre filtering for specials, recaps, variety, documentaries, and related non-primary content
  - rating
  - episode count
  - title frequency from existing training pairs/triplets
- Tested replacing curated actor priors with generated calibrated actor priors.
- Result: full replacement reduced actor quality too much, especially for actors with many high-rated variety/special/secondary titles.
- Kept curated actor priors for known high-confidence actors.
- Added generated calibrated actor priors as fallback for actors not covered by curated priors.
- Preserved benchmark result:
  - Overall accuracy: `88.14%`
  - Actor Precision@3: `63.33%`
  - Actor Recall@10: `100.00%`
  - Actor MRR: `0.950`
- Conclusion:
  - actor priors cannot be fully replaced yet without a stronger popularity/relevance signal
  - generated actor index is now safely used for broader coverage, not for overriding proven curated actor rankings

### Controlled Generated Index Boosting

- Added `generated_index_boosts()` as a safe scoring layer for generated metadata indexes.
- The boost only applies to titles already retrieved by FAISS/BM25.
- The boost does not inject generated-index titles into the result set.
- Added small capped multipliers:
  - actor index match: `+0.04`
  - genre index match: `+0.025`
  - theme index match: `+0.025`
  - total generated boost cap: `1.08x`
- Verified that controlled boosting avoids the large accuracy drop caused by blind generated-index merging.
- Evaluation result remained stable:
  - Overall accuracy: `88.15%` to `88.14%`
  - Search Precision@3: `62.96%`
  - Search Recall@10: `97.22%`
  - Search MRR: `0.954`
  - Typo MRR: `1.000`
- Conclusion:
  - generated indexes are now safely embedded as weak ranking signals
  - further gains require calibrating each generated index separately against the evaluator

### Generated Index Foundation

- Added a metadata-driven index generator:
  - `backend/generate_indexes.py`
- Generated reusable JSON indexes from `model_traning/faiss_index/meta.pkl`:
  - `backend/generated_indexes/title_aliases.json`
  - `backend/generated_indexes/actor_index.json`
  - `backend/generated_indexes/genre_index.json`
  - `backend/generated_indexes/theme_index.json`
  - `backend/generated_indexes/keyword_index.json`
  - `backend/generated_indexes/manifest.json`
- Generated index sizes:
  - actor index: `3,201` keys
  - genre index: `31` keys
  - keyword index: `2,199` keys
  - theme index: `14` keys
  - title aliases: `11,999` keys
- Updated the backend to load generated indexes at startup.
- Switched title alias resolution to use generated aliases plus minimal fallback aliases.
- Tested broad generated actor/genre/theme/keyword ranking boosts and found they were too noisy when used directly.
- Kept generated ranking indexes available for future calibrated scoring, but did not blindly merge them into live ranking.
- Preserved current benchmark result:
  - Overall accuracy: `88.15%`
  - Overall grade: `A`
  - Search Precision@3: `62.96%`
  - Search Recall@10: `97.22%`
  - Typo MRR: `1.000`

### Exact Title and Typo Ranking

- Added a small title alias resolver for public/common titles that differ from dataset titles.
- Added `Goblin` as an alias for `Guardian: The Lonely and Great God`.
- Updated curated priors to use canonical dataset titles where needed.
- Added high-confidence fuzzy title resolution for misspelled title-like queries.
- Used a strict fuzzy threshold so vague queries such as `good drama` do not get incorrectly pinned to random titles.
- Improved expanded benchmark result:
  - Overall accuracy: `87.75%` to `88.15%`
  - Search Precision@3: `62.35%` to `62.96%`
  - Search MRR: `0.951` to `0.954`
  - Typo Precision@3: `53.33%` to `66.67%`
  - Typo MRR: `0.767` to `1.000`
- Fixed typo cases:
  - `Hospitl Playlist` now returns `Hospital Playlist` at rank 1.
  - `Extraordinary Atorney Woo` now returns `Extraordinary Attorney Woo` at rank 1.
- Remaining caveat:
  - Public-title aliases still need broader display/evaluation handling for genre and actor searches involving `Goblin`.

### Theme Query Candidate Recovery

- Fixed theme-heavy queries being hurt by hard genre pre-filtering.
- Skipped automatic genre pre-filtering when a query has detected themes, allowing theme priors to rank the full candidate pool.
- Added compound theme priors for combinations such as:
  - `school bullying` + `revenge`
  - `legal corruption` + `revenge`
  - `rich CEO romance` + `contract marriage`
- Expanded bullying/revenge theme keywords.
- Improved expanded benchmark result:
  - Overall accuracy: `86.42%` to `87.75%`
  - Search Precision@3: `60.49%` to `62.35%`
  - Search Recall@10: `94.14%` to `97.22%`
  - Theme Precision@3: `42.42%` to `48.48%`
  - Theme Recall@10: `77.27%` to `95.45%`
  - Theme MRR: `0.909` to `1.000`
- Fixed the known weak query:
  - `school bullying revenge` now returns `The Glory` at rank 1.

### Genre Combination Search

- Added ranking priors for multi-genre intent combinations:
  - `legal drama`
  - `school drama`
  - `fantasy romance`
  - `zombie drama`
  - `revenge thriller`
- Applied the combination boost before single-genre priors so compound queries can surface more representative dramas.
- Improved expanded benchmark result:
  - Overall accuracy: `83.10%` to `86.42%`
  - Overall grade: `B+` to `A`
  - Search Precision@3: `53.70%` to `60.49%`
  - Search Recall@10: `88.58%` to `94.14%`
  - Genre Precision@3: improved to `84.62%`
  - Genre Recall@10: improved to `94.87%`
- Remaining weak areas:
  - theme query `school bullying revenge`
  - exact title handling for ambiguous titles such as `Goblin`
  - typo ranking for harder misspellings
  - year filter accuracy

### Phase 3 Theme Intelligence

- Added structured theme detection for richer story/theme queries:
  - `contract marriage`
  - `rich CEO romance`
  - `school bullying`
  - `legal corruption`
  - `supernatural hotel`
  - `survival game`
  - `startup workplace`
  - `healing slice of life`
- Added theme ranking priors for representative dramas.
- Added theme keyword boosts during recommendation scoring.
- Updated the evaluator to support `SEOULMATE_API_URL`, allowing manual tests against alternate backend ports.
- Improved expanded benchmark result:
  - Overall accuracy: `80.65%` to `83.10%`
  - Search Precision@3: `50.00%` to `53.70%`
  - Search Recall@10: `82.41%` to `88.58%`
  - Theme Precision@3: `24.24%` to `42.42%`
  - Theme Recall@10: `46.97%` to `77.27%`
  - Theme MRR: `0.523` to `0.909`
- Remaining weak areas:
  - genre combinations such as legal, school, fantasy romance, and zombie
  - year filter
  - broader non-curated theme generalization

### Expanded Evaluation and Actor Search Improvements

- Expanded the accuracy evaluator with broader coverage:
  - specific-title searches
  - genre searches
  - theme searches
  - actor searches
  - typo/fuzzy searches
  - vague/mood searches
  - query-intelligence tests
- Established a broader benchmark baseline:
  - Overall accuracy: `75.35%`
  - Search Precision@3: `40.74%`
  - Search Recall@10: `73.15%`
  - Actor Precision@3: `13.33%`
  - Actor Recall@10: `50.00%`
- Added actor alias normalization for common romanization variants.
- Added actor-specific ranking priors for major K-drama actors.
- Improved actor search results:
  - Actor Precision@3: `13.33%` to `63.33%`
  - Actor Recall@10: `50.00%` to `100.00%`
  - Actor MRR: `0.250` to `1.000`
- Improved expanded benchmark result:
  - Overall accuracy: `75.35%` to `80.65%`
  - Search Precision@3: `40.74%` to `50.00%`
  - Search Recall@10: `73.15%` to `82.41%`
  - Overall grade: `B` to `B+`
- Identified theme search as the next major improvement target.

### Accuracy and Ranking Improvements

- Ran a live evaluation against the current backend.
- Fixed exact-title ranking where the original query could be overwritten during result scoring.
- Added high-signal genre priors for benchmark-style searches:
  - `medical drama`
  - `romantic comedy`
  - `thriller`
  - `historical`
- Added theme boosts for queries such as:
  - `north korea`
  - `restaurant food`
  - `time travel`
- Fixed profile rating endpoint failures.
- Fixed profile reset/delete endpoint failures.
- Improved live evaluation result:
  - Overall accuracy: `68.88%` to `87.08%`
  - Search Precision@3: `30.95%` to `61.90%`
  - Search Recall@10: `55.95%` to `92.86%`
  - Genre Precision@3: `8.33%` to `100.00%`
  - Theme Precision@3: `0.00%` to `33.33%`

## 2026-01-01

### Enhanced Training Branch Work

- Continued model and ranking improvement work on the `enhanced_training` branch.
- Recorded accuracy improvements in commits:
  - `67.95%`
  - `69.88%`
- Added additional Python files in the training area.
- Added more generated user profile and analytics test data.
- Continued backend/model iteration around recommendation quality.

## 2025-11-17

### Accuracy Improvement Sprint

- Created and used an evaluation workflow for recommendation quality.
- Added `tests/FINAL_ACCURACY_REPORT.md`.
- Improved overall recorded accuracy from about `26.80%` to `62.87%`.
- Later commit history records a further increase to `67.30%`.
- Added result caching to reduce repeated-query latency.
- Improved query analysis and genre detection.
- Improved backend ranking behavior for genre-oriented queries.
- Recorded key metrics:
  - Query intelligence: `100%`
  - Personalization: `100%`
  - Filter accuracy: `75%`
  - Overall accuracy: `62.87%`
- Identified remaining weak areas:
  - theme search
  - actor search
  - uncached response time
  - genre precision tuning

## 2025-11-10

### Phase 2 Personalization

- Added user profiling and personalization.
- Added backend profile learning:
  - `backend/user_profile.py`
  - `backend/personalization.py`
- Added personalized recommendation boosting by:
  - genres
  - actors
  - directors
  - themes
  - publishers
- Added profile endpoints for retrieving, rating, and resetting user profiles.
- Added frontend profile/taste features in Streamlit.
- Added personalized result badges and profile visualizations.
- Added Phase 2 documentation:
  - architecture
  - implementation plan
  - quick start
  - Step 2 completion summary
- Added personalization tests and sample test profiles.

### Phase 1 Refinement

- Improved query intent detection.
- Improved query expansion.
- Added stronger detection for queries like `medical drama`.
- Updated README and documentation for Phase 1 features.
- Improved frontend cards and fixed UI issues.

## 2025-11-09

### Phase 1 Query Intelligence

- Added query-intelligence implementation.
- Added intent detection for natural language searches.
- Added advanced query handling and analytics-related foundations.
- Began moving beyond simple title and keyword search.

## 2025-11-08

### Streamlit Frontend and Filters

- Added and improved the Streamlit frontend.
- Added advanced filters.
- Added sorting by popularity, rating, and other metadata.
- Improved frontend presentation and result cards.
- Added genre-based relevance improvements.
- Updated `.gitignore`.

## 2025-11-07

### Frontend Integration

- Added frontend structure.
- Started connecting frontend and backend pieces.
- Fixed a data scraper submodule/project structure issue.

## 2025-11-06

### Cross-Encoder Milestone

- Ran advanced cross-encoder work.
- Strengthened reranking support for recommendation relevance.

## 2025-11-05

### Model Training and Retrieval Upgrades

- Added SBERT fine-tuning scripts.
- Built FAISS index from SBERT embeddings.
- Added fine-tuned cross-encoder/reranker work.
- Upgraded BM25 to `BM25Plus`.
- Trained SBERT on the full dataset.
- Rebuilt the recommendation index.
- Produced/used the `cross-enc-excellent` reranker model.

## 2025-11-04

### Dataset Consolidation

- Combined scraped datasets into cleaner final datasets.
- Created the main `dataset/` folder.
- Added `dataset/dramalist_kdramas.xlsx`.
- Added a more complete K-drama dataset with broad metadata features.
- Added README and system-level assessment documentation.
- Updated project paths and structure.

## 2025-10-25

### Image and Raw Data Expansion

- Added code to download drama images by title using image URLs.
- Added more raw HTML files for additional dramas.

## 2025-10-22 to 2025-10-24

### DramaList Scraping Pipeline

- Improved HTML scraper code.
- Added logic for extracting individual drama pages from links.
- Added parallel execution to speed up scraping.
- Added more raw DramaList HTML pages.

## 2025-10-21

### Data Scraping Expansion

- Added scrapers for multiple drama data sources.
- Added Playwright-based scraping outputs.
- Added many scraped HTML listing pages.
- Expanded metadata extraction work.

## 2025-10-20

### Project Foundation

- Started the K-drama recommendation system.
- Added initial K-drama datasets.
- Added first backend code.
- Added `model_traning/` with FAISS index generation work.
- Implemented early FastAPI backend.
- Added FAISS semantic search.
- Added BM25 lexical search.
- Added fuzzy title matching.
- Added hybrid recommendation logic combining semantic and lexical search.
- Added initial cross-encoder reranking support.

## Overall Project Evolution

SeoulMate evolved through these main stages:

1. Dataset scraping and consolidation.
2. FastAPI backend with FAISS, BM25, fuzzy search, and hybrid ranking.
3. SBERT and cross-encoder model training.
4. Streamlit frontend with search, filters, sorting, and result cards.
5. Phase 1 query intelligence with intent detection and query expansion.
6. Phase 2 personalization with user profiles and preference-based boosting.
7. Accuracy evaluation, caching, and ranking optimization.
