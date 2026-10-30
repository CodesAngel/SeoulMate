# SeoulMate quick start

Full local setup. Run the commands in PowerShell from the repository root.

## Requirements and install

- Python 3.10+, Node.js with npm, Docker Desktop and the Supabase CLI (for the local database).
- The model and index files described in the [training guide](../../training/README.md#current-production-artifacts) (`training/models/` and `training/faiss_index/`; they are not in Git).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` includes the runtime, training and Streamlit dependencies. A server that only runs the API can use `backend/requirements-server.txt` instead (install CPU PyTorch first, as the file explains).

If `training/faiss_index/` is missing, build it from `data/final/kdrama_dataset.csv` with the existing model (see [Index rebuilding](#index-rebuilding)).

## Frontend-only mock mode

To review or redesign the Next.js interface without starting Docker, Supabase, or FastAPI, run:

```powershell
.\scripts\run_web_frontend.ps1 -Mode mock
```

This uses representative local data and posters across discovery, details, watchlist, taste profile, authentication, and account screens. Restart with `-Mode api` or omit the argument to reconnect the existing real services.

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

The importer is idempotent. It requires the final CSV (2,130 dramas), matching FAISS metadata, and the complete `drama_image_by_id/` poster directory. It does not import legacy test analytics or store remote poster URLs.

Open the local Supabase Studio at `http://127.0.0.1:54323`. Stop this project's stack without deleting its local data with:

```powershell
supabase stop
```

### Or use the hosted Supabase project

Put the hosted project's values in `backend/.env` (see `backend/.env.example`) and `frontend-web/.env.local`, and skip `supabase start`. Use the **Session pooler** connection string from the dashboard's Connect window; the direct `db.<ref>.supabase.co` host needs IPv6. Keep the local values in `backend/.env.docker` and `frontend-web/.env.docker` to switch back. Scripts that write to the database (such as `update_catalog.py`) then change the hosted data.

## Start the app

Start the backend:

```powershell
.\scripts\run_backend.ps1
```

The default API is `http://127.0.0.1:8001`; interactive API documentation is at `/docs`. In another terminal, start the internal Streamlit interface:

```powershell
.\scripts\run_frontend.ps1
```

The default internal frontend is `http://localhost:8501`.

Start the Next.js website in another terminal (it installs npm packages on first run):

```powershell
.\scripts\run_web_frontend.ps1
```

More settings are in [frontend-web/README.md](../../frontend-web/README.md).

| Service | Default address |
| --- | --- |
| Website | http://localhost:3000 |
| API | http://127.0.0.1:8001 |
| API documentation | http://127.0.0.1:8001/docs |
| Streamlit (internal) | http://localhost:8501 |
| Supabase Studio | http://127.0.0.1:54323 |
| Local email inbox (Mailpit) | http://127.0.0.1:54324 |

## Stop local services

Press `Ctrl+C` in each terminal running the backend, Next.js or Streamlit. If the backend terminal is gone but port 8001 is still taken, stop its process:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen |
    Select-Object -ExpandProperty OwningProcess |
    ForEach-Object { Stop-Process -Id $_ -Force }
```

No output from `Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue` means it stopped. Stop the database with `supabase stop`.

## Test local authentication

Open `http://localhost:3000/auth/sign-up` and create an account with a password of at least eight characters. Local development automatically confirms new email addresses. The database trigger creates the matching `public.profiles` row, and `/account` is protected by the server-side Supabase session.

Password-reset messages are captured locally in Mailpit. Request one at `http://localhost:3000/auth/forgot-password`, open `http://127.0.0.1:54324`, and follow the link to choose a new password. Production should enable email confirmations and configure a real SMTP provider.

FastAPI exposes `GET /auth/me` as the reference protected route. It accepts `Authorization: Bearer <access-token>`, verifies the token against Supabase's JWKS, and returns the authenticated user ID, email, and role. Existing discovery routes remain public.

After signing in, save a drama and open `/watchlist` to set its status to Planned, Watching, Completed, On hold, or Dropped. Ratings saved from a drama detail page are stored in PostgreSQL and mark the title Completed. Log out and sign in again to verify that both the status and rating are restored. Saves made while signed out remain local to that browser and merge into the account at the next sign-in.

The authenticated application endpoints are `GET/PUT/DELETE /me/watchlist`, `POST /me/watchlist/merge`, and `GET/PUT/DELETE /me/ratings`. They obtain the user ID from the verified access token; clients do not send a user ID for ownership.

Open `/account` to edit the display name, upload or remove an avatar, change the password, inspect saved/watching/completed/rating statistics, sign out, or permanently delete the account. Avatar uploads accept JPEG, PNG, and WebP files up to 2 MB (public `avatars` bucket, owner-scoped upload policies). Deletion requires typing `DELETE` and removes the Auth user, PostgreSQL-owned rows, avatar object, and matching legacy profile data.

The generated taste profile and preference learning still use legacy runtime storage (`backend/runtime_data/`) until their PostgreSQL migration.

## Test the community system (Phase 1)

How the community works (routes, database, API, trending formula) is described in [COMMUNITY.md](COMMUNITY.md).

1. Open `http://localhost:3000` to view the two homepage community sections:
   - **Trending in the community**: 4 cards with drama posters, discussion titles, badges, and comment counts.
   - **From the community**: 3 recent community posts with author avatars, drama banners, and reaction buttons.
2. Open `http://localhost:3000/community` to browse the full feed. Filter by **Trending**, **Recent**, **Reviews**, or **Recommendations**, search by keyword, or filter by drama.
3. Click **Start a discussion** (or navigate to `/community/new`) to publish a new post with optional drama linking, review score (1–10), and spoiler flag.
4. Click on any post card to open its detail page at `/community/[postId]`.
5. For posts or comments flagged with spoilers, verify the spoiler guard: content is masked with *"Contains spoilers — Reveal"* until explicitly clicked.
6. Post, edit, or delete comments on the post detail page (comments render in chronological oldest-first order).
7. Test the heart reaction button: clicking likes or unlikes the post with instant optimistic feedback and automatic rollback on failure.
8. To run tests covering API endpoints, authorization guards, deterministic trending scores, and database foreign key cascades:
   ```powershell
   .\.venv\Scripts\python.exe -u tests\test_community_system.py
   ```

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

To update the catalog with new dramas, see [CATALOG_UPDATES.md](CATALOG_UPDATES.md).
