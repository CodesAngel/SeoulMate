# SeoulMate

<p align="center">
  <img src="docs/assets/thumbs-up-welcome.gif" alt="K-drama thumbs up welcome" width="300">
</p>

You came here to find your next K-drama, honestly, very good choice.

Welcome to SeoulMate an AI-powered Korean drama recommendation system built to understand natural language searches, rank dramas intelligently, and personalize recommendations from user behavior.

The system combines semantic search, lexical search, calibrated ranking indexes, a cross-encoder reranker, and user preference learning to help users discover relevant K-dramas from queries such as `romantic comedy`, `school bullying`, `contract marriage`, `hospital setting`, or `dramas like Crash Landing on You`.

## Current Performance

Latest live backend reference (2026-10-03; production models with the 2,081-drama index; 61-search test set, exact title matching):

| Metric | Score |
| --- | ---: |
| Overall Accuracy | `87.05%` |
| Precision@3 | `60.66%` |
| Recall@10 | `94.48%` |
| MRR | `0.992` |
| NDCG@10 | `0.943` |
| Filter Success Rate | `100%` |
| Avg Response Time (uncached) | `28 ms` |

Precision@3 can reach at most 68.3% on this test set, because title and typo tests have a single expected answer. The earlier `88.50%` figure predates the 2026-07-24 title-search changes and the evaluator fix, so it is not directly comparable. Scores before 2026-10-03 used substring title matching, which counted sequels (e.g. *Hospital Playlist Season 2*) as hits; the same system scored 87.92% that way. Title searches list the drama's other seasons first (10/10 on the franchise check). Similar dramas for titles without curated lists (incl. 2026 dramas): Precision@5 22.7%, Recall@10 28.8% on a 15-seed check (was 6.7% / 15.6%). Trope searches ("found family", "body swap", "time slip", "cross dressing", ...; 18 tropes in `backend/ranking/config/trope_priors.json`): Precision@5 63.3%, Recall@10 81.8% on an 18-query check. Full comparison: [tests/reports/model_comparison_2026-09-30.md](tests/reports/model_comparison_2026-09-30.md).

The default backend uses curated ranking priors with calibrated generated fallback support. Generated-only replacement is still experimental and is not the production default.

## Key Features

- Natural language K-drama search
- Query intent detection for genre, actor, theme, mood, keyword, and similar-title searches
- Hybrid retrieval using FAISS semantic search and BM25Plus lexical search
- Fine-tuned SBERT embeddings for K-drama metadata
- Cross-encoder reranking for stronger final ordering
- Calibrated actor, genre, theme, and keyword ranking indexes
- Fuzzy title matching for typo-tolerant search
- User profiles with click, rating, and watchlist-based personalization
- Streamlit frontend for interactive search and profile exploration
- Local drama posters served by FastAPI from the scraper output directory
- FastAPI backend with analytics and evaluation support

## Repository Structure

```text
SeoulMate/
+-- backend/
|   +-- app.py
|   +-- analytics.py
|   +-- personalization.py
|   +-- query_analyzer.py
|   +-- user_profile.py
|   +-- ranking/
|   |   +-- generate_indexes.py
|   |   +-- config/
|   |   |   +-- curated_priors.json
|   |   +-- indexes/
|   +-- runtime_data/
+-- frontend/
|   +-- streamlit_app.py
|   +-- requirements.txt
|   +-- TEST_FRONTEND.md
+-- training/
|   +-- README.md
|   +-- train_pipeline.py
|   +-- steps/
|   |   +-- step1_generate_training_data.py
|   |   +-- step2_fine_tune_sbert.py
|   |   +-- step3_build_index.py
|   |   +-- step4_generate_reranker_data.py
|   |   +-- step5_fine_tune_cross_encoder.py
|   |   +-- step6_train_ltr.py
|   |   +-- future_multi_index_builder.py  (not in train_pipeline.py; future multi-index upgrade)
|   |   +-- standalone_fine_tune_sbert.py
|   |   +-- standalone_eval_retrieval.py
|   +-- models/
|   |   +-- sbert-finetuned-full/
|   |   +-- cross-enc-excellent/
|   +-- faiss_index/
|   +-- training_data/
+-- training-new/
|   +-- train_pipeline.py
|   +-- fine_tune_kdrama_sbert.py
|   +-- enhanced_index_builder.py
|   +-- learning_to_rank.py
|   +-- models/
|   |   +-- sbert-kdrama-finetuned/
|   +-- ltr_model/
|   +-- faiss_index/
+-- data/
|   +-- final/
|       +-- kdrama_dataset.csv
+-- scrapers/
|   +-- DramaList_Scrapper/
|   |   +-- run_pipeline.py
|   |   +-- steps/
|   |   |   +-- step0a_download_listing_pages.py
|   |   |   +-- step0b_extract_drama_urls.py
|   |   |   +-- step1_download_html.py
|   |   |   +-- step2_extract_data.py
|   |   |   +-- step3_download_images.py
|   |   +-- output/ (gitignored: html_pages/, dramas_html/, drama_image/, dramalist_all_dramas.csv)
|   |   +-- mydramalist_data.csv
|   +-- kdrama_dataset.csv
+-- tests/
|   +-- evaluate_accuracy.py
|   +-- compare_ranking_modes.py
|   +-- validate_generated_indexes.py
|   +-- debug_generated_query.py
|   +-- reports/
+-- docs/
|   +-- archived/
+-- scripts/
|   +-- run_backend.ps1
|   +-- run_frontend.ps1
|   +-- run_accuracy.ps1
+-- CONTRIBUTING.md
+-- CHANGELOG.md
+-- LICENSE
+-- pyproject.toml
+-- README.md
+-- requirements.txt
```

## Folder Responsibilities

| Folder | Purpose |
| --- | --- |
| `backend/` | FastAPI recommendation API and runtime logic |
| `backend/ranking/` | Curated priors, generated ranking indexes, and index generation |
| `frontend/` | Streamlit user interface |
| `training/` | Production model training, FAISS index building, and active model artifacts |
| `training-new/` | Experimental cloud training pipeline, lightweight MiniLM model, and LTR artifacts |
| `data/final/` | Final dataset used by training and indexing scripts |
| `scrapers/` | Data collection and scraping utilities |
| `scrapers/DramaList_Scrapper/` | MyDramaList scrape pipeline (5 steps, run via `run_pipeline.py`); see its own [README](scrapers/DramaList_Scrapper/README.md) |
| `tests/evaluation/` | Accuracy evaluator and offline generated-index validation |
| `tests/ranking/` | Ranking mode comparisons, prior experiments, weak-query reports, and audits |
| `tests/debug/` | Single-query tracing and metadata inspection helpers |
| `tests/smoke/` | Older API, personalization, filter, and flow checks |
| `tests/docs/` | Test reports and historical improvement notes |
| `docs/` | Project documentation and archived phase notes |
| `scripts/` | Convenience scripts for common project commands |
| `requirements.txt` | Combined dependency list for full local setup |
| `pyproject.toml` | Project metadata and Python tooling configuration |
| `CONTRIBUTING.md` | Development workflow and contribution guidance |
| `LICENSE` | Project license |

## System Pipeline

```text
Data scraping
   |
   v
Final drama dataset
   |
   v
Training data generation
   |
   v
SBERT fine-tuning and cross-encoder training
   |
   v
FAISS index and metadata build
   |
   v
Generated ranking index calibration
   |
   v
FastAPI recommendation backend
   |
   v
Streamlit frontend
   |
   v
User interactions, ratings, watchlist, and analytics
```

## Recommendation Flow

```text
User query
   |
   v
Query analyzer
   |-- intent detection
   |-- genre, actor, theme, and keyword detection
   |-- query expansion
   |
   v
Filtering layer
   |-- genre
   |-- actor
   |-- keyword
   |-- rating
   |-- similar title
   |
   v
Hybrid retrieval
   |-- FAISS semantic search
   |-- BM25Plus lexical search
   |
   v
Ranking layer
   |-- dynamic alpha
   |-- curated priors
   |-- calibrated generated fallbacks
   |-- keyword expansion
   |
   v
Cross-encoder reranking
   |
   v
Personalization layer
   |-- profile preferences
   |-- clicks
   |-- ratings
   |-- watchlist actions
   |
   v
Final recommendations
```

## Technology Stack

| Area | Tools |
| --- | --- |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Frontend | Streamlit, Requests, Pandas |
| Semantic Search | Sentence Transformers, FAISS |
| Lexical Search | BM25Plus |
| Reranking | CrossEncoder |
| Matching | RapidFuzz |
| Training | PyTorch, Sentence Transformers |
| Data Processing | Pandas, NumPy, OpenPyXL |
| Storage | Excel, Pickle, FAISS, JSON, JSONL |

## Installation

Install core dependencies:

```powershell
pip install -r requirements.txt
```

Or install the main groups manually:

```powershell
pip install fastapi uvicorn pydantic
pip install sentence-transformers faiss-cpu rank-bm25 rapidfuzz
pip install pandas numpy torch openpyxl
pip install streamlit requests
```

Install frontend dependencies:

```powershell
pip install -r frontend\requirements.txt
```

Install training dependencies:

```powershell
pip install -r training\requirements.txt
```

## Running The Application

Before starting the application, make sure the downloaded poster files are present in:

```text
scrapers/DramaList_Scrapper/output/drama_image/
```

The backend reads this folder during startup. Restart the backend after adding, removing, or renaming poster files.

Start the backend:

```powershell
.\scripts\run_backend.ps1
```

Start the frontend in a second terminal:

```powershell
.\scripts\run_frontend.ps1
```

Manual backend command:

```powershell
$env:SEOULMATE_RELOAD="0"
python backend\app.py
```

Manual frontend command:

```powershell
streamlit run frontend\streamlit_app.py
```

Local URLs:

```text
Backend:  http://127.0.0.1:8001
Frontend: http://localhost:8501
```

## Example Searches

Use these queries to quickly inspect the system:

```text
romantic comedy
school bullying
contract marriage
hospital setting
time manipulation
thriller
Park Seo Joon
dramas like Crash Landing on You
```

## API Overview

Health check:

```text
GET /
```

Analyze a query:

```text
GET /analyze?query=romantic comedy
```

Get recommendations:

```text
GET /recommend?title=romantic comedy&top_n=5
```

Common recommendation filters:

```text
genre
director
publisher
rating_value
rating_count
keywords
screenwriters
sort_by
sort_order
similar_to
user_id
session_id
```

Analytics endpoints:

```text
POST /analytics/interaction
GET  /analytics/popular
GET  /analytics/trending-searches
GET  /analytics/summary
```

Personalization endpoints:

```text
GET    /profile/{user_id}
POST   /profile/{user_id}/rate
DELETE /profile/{user_id}
```

## Poster Images

Posters are identified by the poster URL in each dataset row, not by the drama's title. The backend serves a local copy when it has one and falls back to the MyDramaList URL otherwise.

- **File names.** `scrapers/DramaList_Scrapper/steps/step3_download_images.py` saves each poster as `<Title> (<Year>) [<ID>].jpg`, where the ID is the file name of the poster URL (`https://i.mydramalist.com/9oX6Gf.jpg` → `9oX6Gf`). The title and year are only a readable label; code reads the `[ID]` part. Same-title dramas get separate files: `Bad Guy (2010) [9oX6Gf].jpg`, `Bad Guy (2024) [73PkAD_4f].jpg`.
- **Lookup.** At startup `attach_dataset_extras()` in `backend/app.py` joins each index record to its dataset row on title + air date (whitespace/case-insensitive), takes the poster URL and ID, and sets `Image` to `/drama-images/<file>` if a file with that ID exists in `scrapers/DramaList_Scrapper/output/drama_image_by_id/`, otherwise to the poster URL. Responses also include `image_id`, `image_url` and `watchers`. The startup log reports `Posters: N local, N via URL, N missing`.
- **Frontend.** Streamlit shows `/drama-images/...` paths and `https://i.mydramalist.com/...` URLs (no other hosts). If a local poster fails to load, it retries the drama's `image_url`, then shows "Poster unavailable".
- **Index rebuilds.** `training/steps/step3_build_index.py` now writes `image_url`, `image_id` and `watchers` into `meta.pkl`; the backend uses those when present and the CSV join otherwise.

Download or top up the posters (skips IDs already in the folder, writes failures to `output/drama_image_by_id_report.csv`):

```bash
python scrapers/DramaList_Scrapper/steps/step3_download_images.py
# options: --csv <dataset.csv> --out <folder> --report <report.csv> --concurrency 10
```

Restart the backend afterwards; it indexes the poster folder at startup. To check one poster while the backend runs: `http://127.0.0.1:8001/drama-images/Bad%20Guy%20%282010%29%20%5B9oX6Gf%5D.jpg`.

Why not titles: 10 titles are shared by two different dramas (*Bad Guy*, *Secret*, *Trap*, *Your Honor*, *While You Were Sleeping*, *Save Me*, *Connect*, *Once Again*, *Temptation*, *The Miracle*). With title-named files the second download overwrote the first, so one drama of each pair showed the other's poster. The old title-named folder `output/drama_image/` is no longer read.

## Ranking Modes

The safest default is the curated system with calibrated generated fallback support.

Default-style configuration:

```powershell
$env:SEOULMATE_GENRE_PRIOR_SOURCE="curated"
$env:SEOULMATE_ACTOR_PRIOR_SOURCE="curated"
$env:SEOULMATE_THEME_PRIOR_SOURCE="curated"
```

Useful experimental configuration:

```powershell
$env:SEOULMATE_GENRE_PRIOR_SOURCE="hybrid_calibrated"
$env:SEOULMATE_THEME_PRIOR_SOURCE="fallback_generated"
```

Generated-only modes are useful for analysis, but they are not the recommended default because they currently reduce accuracy compared with the stable curated baseline.

## Evaluation

Start the backend first, then run:

```powershell
.\scripts\run_accuracy.ps1
```

or:

```powershell
python tests\evaluation\evaluate_accuracy.py
```

Compare ranking modes:

```powershell
python tests\ranking\compare_ranking_modes.py
```

Validate generated indexes offline:

```powershell
python tests\evaluation\validate_generated_indexes.py
```

Debug one query:

```powershell
python tests\debug\debug_generated_query.py "school drama"
```

Report output is organized under:

```text
tests/reports/
+-- audits/
+-- debug/
+-- logs/
```

## Training And Index Generation

Run the full training pipeline:

```powershell
cd training
python train_pipeline.py --mode full
```

Run the quick pipeline:

```powershell
cd training
python train_pipeline.py --mode quick
```

Rebuild the FAISS index:

```powershell
cd training
python steps\step3_build_index.py --mode full
```

Regenerate backend ranking indexes:

```powershell
python backend\ranking\generate_indexes.py
```

Generated ranking indexes are written to:

```text
backend/ranking/indexes/
```

Curated ranking config lives at:

```text
backend/ranking/config/curated_priors.json
```

### Model Variants & Directory Differences (`training/models` vs `training-new/models`)

The repository contains two model training setups representing different optimization goals:

| Feature | `training/models/` (Production Default) | `training-new/models/` (Experimental / Lightweight) |
| :--- | :--- | :--- |
| **Directory Contents** | 1. `sbert-finetuned-full/`<br>2. `cross-enc-excellent/` | 1. `sbert-kdrama-finetuned/` |
| **SBERT Base Architecture** | `paraphrase-multilingual-mpnet-base-v2` (`XLMRobertaModel`) | `paraphrase-multilingual-MiniLM-L12-v2` (`BertModel`) |
| **Embedding Dimension** | **768 dimensions** | **384 dimensions** |
| **SBERT Model Size** | **~1.11 GB** (`model.safetensors`) | **~470 MB** (`model.safetensors`) |
| **Reranker Architecture** | **Neural Cross-Encoder** (`cross-enc-excellent/`, ~90 MB) | **LightGBM LTR Tree Model** (`training-new/ltr_model/`) |
| **Backend Integration** | **Actively loaded** by `backend/app.py` | Experimental / standalone pipeline |

#### Details:

1. **`training/models/` (Current Production Backend)**:
   - **`sbert-finetuned-full`**: Fine-tuned 768-dimensional multilingual MPNet model. Offers superior semantic nuance and multilingual understanding across titles, cast, and plot summaries. Matches the 768-dim FAISS index in `training/faiss_index/`.
   - **`cross-enc-excellent`**: 6-layer sequence-pair classification model (`ms-marco-MiniLM-L-6-v2`) used as the live reranker in `backend/app.py`.

2. **`training-new/models/` (Lightweight Cloud Studio Retraining)**:
   - **`sbert-kdrama-finetuned`**: Fine-tuned 384-dimensional MiniLM-L12 model. Trained for lower CPU inference latency and a ~58% smaller memory footprint.
   - **`ltr_model/`**: Replaces the neural cross-encoder with a tabular LightGBM LambdaMART ranker based on query-item features.

> [!NOTE]
> If you plan to switch the backend from `training/models` to `training-new/models`, you will need to re-encode the FAISS index because the vector dimensions differ (**768** vs **384**).
>
> For a detailed roadmap on upgrading to modern state-of-the-art models (E5-base + BGE-reranker) to reach 93–95% accuracy, see [docs/MODEL_UPGRADE_OVERVIEW.md](docs/MODEL_UPGRADE_OVERVIEW.md).

## Personalization

SeoulMate adapts per user through:

- searches
- clicks
- watchlist additions
- ratings
- learned profile preferences

This improves personalized recommendations for that user. The core SBERT model, FAISS index, curated priors, and generated indexes do not retrain automatically from user behavior. Logged behavior can later be used to recalibrate indexes, tune ranking, or train improved rerankers.

## Known Limitations

- Full generated replacement is not yet strong enough to fully replace curated priors.
- Keyword generated indexes are useful for explicit keyword fallback, but not ready for broad live ranking.
- Some theme queries still need calibration.
- `time manipulation` can still lean toward literal title matches.
- Accuracy scripts require the backend to be running before live evaluation.
- Posters fall back to MyDramaList URLs when no local file exists, so those depend on that site being reachable (see Poster Images).

## Git And Runtime Notes

The project uses one Git repository at the root:

```text
SeoulMate/.git
```

Runtime files are ignored through `.gitignore`, including:

```text
backend/runtime_data/
analytics_data/
backend/analytics_data/
backend/user_profiles/
user_profiles/
__pycache__/
*.pyc
```

Important dated project history is tracked in:

```text
CHANGELOG.md
```

## Project Status

The backend is stable and accuracy-tested. The current focus is improving generated ranking replacement quality over time while keeping the curated baseline reliable.

Made with ❤️ for K-drama lovers.
