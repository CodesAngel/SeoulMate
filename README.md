<p align="center">
  <img src="docs/assets/thumbs-up-welcome.gif" alt="K-drama thumbs up welcome" width="300">
</p>

You came here to find your next K-drama, honestly, very good choice.

Welcome to SeoulMate an AI-powered Korean drama recommendation system built to understand natural language searches, rank dramas intelligently, and personalize recommendations from user behavior.

The system combines semantic search, lexical search, calibrated ranking indexes, a cross-encoder reranker, and user preference learning to help users discover relevant K-dramas from queries such as `romantic comedy`, `school bullying`, `contract marriage`, `hospital setting`, or `dramas like Crash Landing on You`.

## Features

- Hybrid search combining FAISS semantic retrieval and BM25Plus lexical matching.
- Query analysis, typo-tolerant title matching, and genre, year, and rating filters.
- Cross-encoder reranking with curated priors and calibrated generated fallbacks.
- Personalized recommendations based on ratings and recorded user interactions.
- Drama detail pages, poster images, and a browser-persistent watchlist.
- Email/password accounts with Supabase Auth, server-refreshed sessions, password recovery, and verified FastAPI bearer tokens.
- Internal Streamlit interface for model testing, analytics, and profile exploration.

## Architecture

The FastAPI backend serves the Next.js frontend and internal Streamlit interface. Search combines query analysis, hybrid retrieval, ranking, reranking, and personalization.

| Component | Technology |
| --- | --- |
| Web interface | Next.js, React, TypeScript, Supabase SSR, Tailwind CSS |
| API | FastAPI, Uvicorn |
| Semantic retrieval | Sentence Transformers, FAISS |
| Lexical retrieval and matching | BM25Plus, RapidFuzz |
| Training and data processing | PyTorch, Pandas, NumPy |
| Internal interface | Streamlit |

## Quick start

These instructions use PowerShell from the repository root. Requirements: Python 3.10+, Node.js with npm for the web interface, and the model and index artifacts described in the [training guide](training/README.md#current-production-artifacts).

### 1. Install Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The combined requirements include runtime, training, and internal frontend dependencies.

### 2. Prepare the search index

The backend loads models from `training/models/` and requires `index.faiss` and `meta.pkl` in `training/faiss_index/`. If a matching index already exists, skip this step. Otherwise, with `data/final/kdrama_dataset.csv` available, build it:

```powershell
.\.venv\Scripts\python.exe training\steps\step3_build_index.py
```

This uses an existing embedding model; it does not retrain it. The index and backend must use the same embedding model. See the [training guide](training/README.md) for artifact preparation and model selection.

### 3. Start local Supabase

Start Docker Desktop, then run:

```powershell
supabase start
.\.venv\Scripts\python.exe -m alembic upgrade head
```

This starts the local database, Auth, Storage, Studio, and Mailpit services described in the [quick start](docs/QUICKSTART.md).

### 4. Start the backend

```powershell
.\scripts\run_backend.ps1
```

### 5. Start the web interface

In a second terminal:

```powershell
.\scripts\run_web_frontend.ps1
```

The launcher installs npm dependencies if `node_modules` is absent. For environment configuration, see the [web frontend guide](frontend-web/README.md).

| Service | Default address |
| --- | --- |
| Web interface | http://localhost:3000 |
| API | http://127.0.0.1:8001 |
| Interactive API documentation | http://127.0.0.1:8001/docs |
| Local email inbox | http://127.0.0.1:54324 |

To use the internal Streamlit interface, run `.\scripts\run_frontend.ps1` in another terminal and open `http://localhost:8501`.

## Authentication

The Next.js application uses Supabase Auth with server-refreshed cookie sessions. Create an account at `/auth/sign-up`, sign in at `/auth/login`, manage the current session at `/account`, and request password recovery at `/auth/forgot-password`. Local authentication emails are captured by Mailpit at `http://127.0.0.1:54324`.

Every signup creates a matching row in `public.profiles`. FastAPI validates Supabase access tokens through the project's JWKS endpoint; `GET /auth/me` is the reference protected endpoint. The watchlist and existing taste-profile data remain browser-local or in legacy runtime storage until the next PostgreSQL application-data migration.

## Dataset and posters

The final dataset is `data/final/kdrama_dataset.csv`. After adding dramas or changing recommendation text, rebuild the index with the existing model and restart the backend. New dramas do not require model retraining.

Local posters are optional. To download missing posters:

```powershell
.\.venv\Scripts\python.exe scrapers\DramaList_Scrapper\steps\step3_download_images.py
```

Poster originals are preserved in `scrapers/DramaList_Scrapper/output/drama_image_by_id/`. The production UI receives public Supabase Storage URLs from FastAPI, using WebP thumbnails on cards and original JPEGs on detail pages. Runtime poster delivery has no external image fallback; details are in the [quick start](docs/QUICKSTART.md#prepare-and-upload-posters-to-local-storage).

## Evaluation

With the backend running:

```powershell
.\scripts\run_accuracy.ps1
```

Recorded baseline: **2,081 dramas**, 61-search test set, exact title matching, evaluated on **2026-10-03**.

| Metric | Result |
| --- | ---: |
| Overall accuracy | 87.05% |
| Precision@3 | 60.66% |
| Recall@10 | 94.48% |
| Mean reciprocal rank | 0.992 |

These results describe this benchmark, not all recommendation scenarios. Precision@3 has a 68.3% ceiling on this test set because title and typo cases have a single expected answer. Similar-drama and trope searches have separate evaluations. See the [evaluation report](tests/reports/model_comparison_2026-09-30.md) for methodology, comparisons, and limitations.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `backend/` | API, ranking, personalization, and analytics |
| `frontend-web/` | Next.js user interface |
| `frontend/` | Internal Streamlit interface |
| `training/` | Active training pipeline, models, and FAISS index |
| `training-new/` | Experimental training pipeline |
| `data/final/` | Final drama dataset |
| `scrapers/` | Data collection and poster downloads |
| `tests/` | Evaluation, regression checks, and reports |
| `scripts/` | Local launch and evaluation commands |
| `docs/` | Current guides, plans, and historical archives |

## Documentation

- [Documentation index](docs/README.md)
- [Quick start](docs/QUICKSTART.md)
- [Personalization guide](docs/PERSONALIZATION_QUICK_START.md)
- [Training and index building](training/README.md)
- [Scraper pipeline](scrapers/DramaList_Scrapper/README.md)
- [Web frontend](frontend-web/README.md)
- [Automatic dataset update plan](docs/AUTOMATED_DATASET_UPDATE_PLAN.md)
- [Contributing](CONTRIBUTING.md) and [changelog](CHANGELOG.md)

Scheduled catalog updates are planned, not implemented. User interactions update profiles without automatically retraining the core models. Generated-only ranking remains experimental; the default uses curated priors with calibrated generated fallback support.

## License

[MIT](LICENSE).
