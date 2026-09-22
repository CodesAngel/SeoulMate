# SeoulMate

<p align="center">
  <img src="docs/assets/thumbs-up-welcome.gif" alt="K-drama thumbs up welcome" width="300">
</p>

You came here to find your next K-drama, honestly, very good choice.

Welcome to SeoulMate an AI-powered Korean drama recommendation system built to understand natural language searches, rank dramas intelligently, and personalize recommendations from user behavior.

The system combines semantic search, lexical search, calibrated ranking indexes, a cross-encoder reranker, and user preference learning to help users discover relevant K-dramas from queries such as `romantic comedy`, `school bullying`, `contract marriage`, `hospital setting`, or `dramas like Crash Landing on You`.

## Current Performance

Latest stable backend reference:

| Metric | Score |
| --- | ---: |
| Overall Accuracy | `88.50%` |
| Precision@3 | `63.58%` |
| Recall@10 | `98.46%` |
| MRR | `0.963` |

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
|   +-- train_pipeline.py
|   +-- steps/
|   |   +-- build_index.py
|   |   +-- enhanced_index_builder.py
|   |   +-- generate_training_data.py
|   |   +-- fine_tune_kdrama_sbert.py
|   |   +-- fine_tune_cross_encoder.py
|   |   +-- learning_to_rank.py
|   +-- models/
|   +-- faiss_index/
|   +-- training_data/
+-- data/
|   +-- final/
|       +-- dramalist_kdramas.xlsx
+-- scrapers/
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
| `training/` | Model training, FAISS index building, and training artifacts |
| `data/final/` | Final dataset used by training and indexing scripts |
| `scrapers/` | Data collection and scraping utilities |
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
python training\steps\enhanced_index_builder.py --mode full
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
