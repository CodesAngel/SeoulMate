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

## Test local authentication

Open `http://localhost:3000/auth/sign-up` and create an account with a password of at least eight characters. Local development automatically confirms new email addresses. The database trigger creates the matching `public.profiles` row, and `/account` is protected by the server-side Supabase session.

Password-reset messages are captured locally in Mailpit. Request one at `http://localhost:3000/auth/forgot-password`, open `http://127.0.0.1:54324`, and follow the link to choose a new password. Production should enable email confirmations and configure a real SMTP provider.

FastAPI exposes `GET /auth/me` as the reference protected route. It accepts `Authorization: Bearer <access-token>`, verifies the token against Supabase's JWKS, and returns the authenticated user ID, email, and role. Existing discovery routes remain public.

After signing in, save a drama and open `/watchlist` to set its status to Planned, Watching, Completed, On hold, or Dropped. Ratings saved from a drama detail page are stored in PostgreSQL and mark the title Completed. Log out and sign in again to verify that both the status and rating are restored. Saves made while signed out remain local to that browser and merge into the account at the next sign-in.

The authenticated application endpoints are `GET/PUT/DELETE /me/watchlist`, `POST /me/watchlist/merge`, and `GET/PUT/DELETE /me/ratings`. They obtain the user ID from the verified access token; clients do not send a user ID for ownership.

Open `/account` to edit the display name, upload or remove an avatar, change the password, inspect saved/watching/completed/rating statistics, sign out, or permanently delete the account. Avatar uploads accept JPEG, PNG, and WebP files up to 2 MB. Deletion requires typing `DELETE` and removes the Auth user, PostgreSQL-owned rows, avatar object, and matching legacy profile data.

## Index rebuilding

The backend needs `training/faiss_index/index.faiss` and `meta.pkl`. If these already match your dataset and model, ordinary startup does not require rebuilding.

After adding dramas or changing the text used for recommendations, rebuild with the existing model:

```powershell
.\.venv\Scripts\python.exe training\steps\step3_build_index.py
```

This reads `data/final/kdrama_dataset.csv`, generates embeddings, and replaces the index and metadata. It does not train a model or download posters. Restart the backend afterwards. When changing the embedding model, rebuild the index with that same model and ensure the backend uses it too.

## Poster originals

The complete original poster collection is stored under `scrapers/DramaList_Scrapper/output/drama_image_by_id/`. The backend no longer serves this folder or uses external poster URLs at runtime. It joins FAISS results to PostgreSQL by stable catalog position and returns the corresponding Supabase Storage URLs.

## Prepare and upload posters to local Storage

The Storage pipeline uses only the existing originals in `drama_image_by_id`; it does not download external images. Audit the originals, generate the WebP card variants, and upload both variants to local Supabase:

```powershell
.\.venv\Scripts\python.exe scripts\audit_poster_inventory.py
.\.venv\Scripts\python.exe scripts\generate_poster_thumbnails.py
.\.venv\Scripts\python.exe scripts\upload_posters_to_storage.py
```

The uploader creates the public `drama-posters` bucket when needed and upserts objects at `dramas/{drama_id}/original.jpg` and `dramas/{drama_id}/thumbnail.webp`. It verifies every object's Storage metadata, public HTTP size and content type, and database association before updating `dramas.poster_original_key` and `dramas.poster_thumbnail_key`. Detailed manifests are written under `data/reports/`.

## Check the API

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/'
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/recommend?title=Goblin&top_n=5'
```

For future scheduled updates, see the [automatic dataset update plan](AUTOMATED_DATASET_UPDATE_PLAN.md).
