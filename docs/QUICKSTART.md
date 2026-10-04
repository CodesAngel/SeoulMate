# SeoulMate quick start

Updated: 2026-10-04. Run these commands from `D:\Projects\SeoulMate` with the existing virtual environment and dependencies installed. See the [root README](../README.md) for full setup.

## Start the local database

Start Docker Desktop, then run the project-scoped Supabase services:

```powershell
supabase start
```

The ignored `backend/.env` and `frontend-web/.env.local` files must contain the local values printed by `supabase status -o env`; the committed `.env.example` files document the required variable names. Never put a secret key in the frontend environment file.

Apply the application schema and import the validated catalog:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe scripts\import_catalog.py --dry-run
.\.venv\Scripts\python.exe scripts\import_catalog.py
```

The importer is idempotent. It requires the 2,081-row final CSV, matching FAISS metadata, and the complete `drama_image_by_id/` poster directory. It does not import legacy test analytics or store remote poster URLs.

Open the local Supabase Studio at `http://127.0.0.1:54323`. Stop this project's stack without deleting its local data with:

```powershell
supabase stop
```

## Start the app

Start the backend:

```powershell
.\scripts\run_backend.ps1
```

The default API is `http://127.0.0.1:8001`; interactive API documentation is at `/docs`. In another terminal, start the internal Streamlit interface:

```powershell
.\scripts\run_frontend.ps1
```

The default internal frontend is `http://localhost:8501`. The production Next.js frontend has separate instructions in [frontend-web/README.md](../frontend-web/README.md).

## Index rebuilding

The backend needs `training/faiss_index/index.faiss` and `meta.pkl`. If these already match your dataset and model, ordinary startup does not require rebuilding.

After adding dramas or changing the text used for recommendations, rebuild with the existing model:

```powershell
.\.venv\Scripts\python.exe training\steps\step3_build_index.py
```

This reads `data/final/kdrama_dataset.csv`, generates embeddings, and replaces the index and metadata. It does not train a model or download posters. Restart the backend afterwards. When changing the embedding model, rebuild the index with that same model and ensure the backend uses it too.

## Poster downloads

Local posters are optional; the backend can fall back to dataset poster URLs. Download missing ID-based posters with:

```powershell
.\.venv\Scripts\python.exe scrapers\DramaList_Scrapper\steps\step3_download_images.py
```

Files go into `scrapers/DramaList_Scrapper/output/drama_image_by_id/`; failures are recorded in `drama_image_by_id_report.csv` in the same output directory. Rerunning skips saved poster IDs. Restart the backend to discover new files.

The backend no longer reads `output/drama_image/`. Poster changes alone do not require an index rebuild: the backend joins existing metadata to the final CSV at startup to obtain missing poster URLs and IDs, and reads per-drama watcher counts from that CSV when available.

## Check the API

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/'
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/recommend?title=Goblin&top_n=5'
```

For future scheduled updates, see the [automatic dataset update plan](AUTOMATED_DATASET_UPDATE_PLAN.md).
