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
- Drama detail pages, poster images, an account-synced watchlist, viewing statuses, and personal ratings.
- Spoiler-safe K-drama community: public reading, authenticated discussions, reviews (with 1–10 scores), recommendations, oldest-first comments, optimistic likes, and drama catalog associations.
- Email/password accounts with Supabase Auth, server-refreshed sessions, password recovery, and verified FastAPI bearer tokens.
- Switchable real API and self-contained mock modes for frontend development.
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

To work only on the frontend while FastAPI and Supabase are stopped, launch the same application with representative mock data and local posters:

```powershell
.\scripts\run_web_frontend.ps1 -Mode mock
```

Use `-Mode api` or omit `-Mode` to restore the existing real backend integration. Restart the Next.js development server when switching modes.

| Service | Default address |
| --- | --- |
| Web interface | http://localhost:3000 |
| API | http://127.0.0.1:8001 |
| Interactive API documentation | http://127.0.0.1:8001/docs |
| Local email inbox | http://127.0.0.1:54324 |

To use the internal Streamlit interface, run `.\scripts\run_frontend.ps1` in another terminal and open `http://localhost:8501`.

### Stop local services

Press `Ctrl+C` in each terminal that is running the backend, Next.js frontend, or Streamlit interface. If the backend terminal is no longer available but port 8001 is still occupied, stop its process from PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen |
    Select-Object -ExpandProperty OwningProcess |
    ForEach-Object { Stop-Process -Id $_ -Force }
```

Confirm that the backend stopped by running the following command. No output means nothing is listening on port 8001:

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
```

Stop the local Supabase containers separately when they are no longer needed:

```powershell
supabase stop
```

## Authentication

The Next.js application uses Supabase Auth with server-refreshed cookie sessions. Create an account at `/auth/sign-up`, sign in at `/auth/login`, manage the current session at `/account`, and request password recovery at `/auth/forgot-password`. Local authentication emails are captured by Mailpit at `http://127.0.0.1:54324`.

Every signup creates a matching row in `public.profiles`. FastAPI validates Supabase access tokens through the project's JWKS endpoint; `GET /auth/me` is the reference protected endpoint. Signed-in watchlists, viewing statuses, and ratings are stored in PostgreSQL and restored on later sessions. Guest saves remain in the browser and merge into the account after sign-in. The generated taste profile and preference learning still use legacy runtime storage pending their PostgreSQL migration.

The protected `/account` area supports display-name updates, per-user avatar uploads, password changes, active profile statistics, sign-out, and permanent account deletion. Avatars use the public `avatars` Storage bucket with owner-scoped upload policies and a 2 MB JPEG/PNG/WebP limit. Account deletion removes the avatar and legacy profile artifacts, deletes the Supabase Auth user, and cascades through PostgreSQL-owned data.

## Community system (Phase 1)

SeoulMate includes a spoiler-safe K-drama community where visitors can read discussions, reviews, and recommendations, and signed-in members can share insights and join conversations.

### Community routes

| Route | Purpose | Access |
| --- | --- | --- |
| `/community` | Feed with Trending, Recent, Reviews, Recommendations tabs, search, and drama filtering | Public read |
| `/community/new` | Post composer for discussions, reviews (with 1–10 scores), and recommendations linked to dramas | Authenticated |
| `/community/[postId]` | Complete post detail, full markdown/body, associated drama links, reaction heart, and comments | Public read, authenticated comments |
| `/community/edit/[postId]` | Post editor for authors to update their title, body, spoiler flag, and review rating | Post author only |

### Homepage community sections

- **Trending in the community**: Four engagement-ranked posts placed after the statistics strip and before "Start with these", showing drama thumbnails, short titles, post type badges, spoiler tags, comment/like counts, and participant avatars.
- **From the community**: Three recent community posts placed after the mood section, showing author avatars, relative post timestamps, drama poster banners, like buttons, comment links, and a "Join the conversation" CTA.

### Database migration and security

The database schema is managed via Alembic migration `backend/migrations/versions/f2c84d1e9a73_add_community_system.py`:
- `community_posts`: UUID primary key, `user_id` referencing `profiles(id)` (CASCADE), nullable `drama_id` referencing `dramas(id)` (SET NULL), post type (`discussion`, `review`, `recommendation`), title (max 120 chars), body (max 2,000 chars), rating (1.0–10.0), `contains_spoilers` boolean, timestamps with triggers.
- `community_comments`: UUID primary key, `post_id` (CASCADE), `user_id` (CASCADE), body (max 1,000 chars), `contains_spoilers` boolean, timestamps.
- `community_reactions`: `post_id` (CASCADE), `user_id` (CASCADE), `reaction_type` (`like`), unique constraint on `(post_id, user_id, reaction_type)`.
- Row Level Security (RLS) is enabled on all community tables: anonymous users have read-only access; authenticated members can only create content under their own identity, edit/delete their own posts/comments, and add/remove their own reactions.

### API endpoints

- **Public**:
  - `GET /community/posts`: List posts with cursor/page pagination, post-type filtering, search query, drama filter, and trending or recent sorting.
  - `GET /community/posts/{post_id}`: Fetch single post with drama details, author profile, reaction counts, and author permissions.
  - `GET /community/posts/{post_id}/comments`: Fetch comments ordered oldest-first.
  - `GET /community/trending`: Returns top 4 posts ranked by deterministic score.
- **Authenticated**:
  - `POST /community/posts`: Create a discussion, review, or recommendation (201 Created).
  - `PATCH /community/posts/{post_id}`: Edit post title, body, rating, or spoiler status (author only).
  - `DELETE /community/posts/{post_id}`: Delete post and cascade reactions/comments (204 No Content, author only).
  - `POST /community/posts/{post_id}/comments`: Post a comment (201 Created).
  - `PATCH /community/comments/{comment_id}`: Edit comment body or spoiler flag (author only).
  - `DELETE /community/comments/{comment_id}`: Delete comment (204 No Content, author only).
  - `PUT /community/posts/{post_id}/like`: Like a post (idempotent, increments count).
  - `DELETE /community/posts/{post_id}/like`: Unlike a post (decrements count).

### Deterministic trending formula

Trending posts are calculated deterministically without ML models or heavy background workers:
$$\text{Trending Score} = \text{Likes} + (\text{Comments} \times 2) + \text{Recency Bonus}$$
where the recency bonus awards up to 21 points for posts active within the last 7 days ($(\max(0, 7 - \text{age}_{\text{days}})) \times 3$).

### Spoiler behavior

Any post or comment marked with `contains_spoilers: true` initially masks its text behind a "Contains spoilers — Reveal" guard. Previews in the homepage sections, feed cards, search results, and page metadata never render unmasked spoiler text. Content is only revealed when the visitor explicitly clicks "Reveal".

### Mock mode support

Run `.\scripts\run_web_frontend.ps1 -Mode mock` to use the community system completely standalone without starting PostgreSQL, Docker, or FastAPI. Mock mode provides 8+ community posts (including the 4 trending and 3 homepage items), multi-user comments, spoiler guards, and interactive in-memory CRUD operations (create, edit, delete posts and comments, toggle likes) that reset upon dev-server restart.

### Phase 1 MVP boundaries

Features deliberately excluded from Phase 1 and reserved for subsequent phases:
- Nested comment threads / replies
- User follow graphs and direct messaging
- Custom image/media uploads in post bodies
- Multiple reaction emojis (only "like" is supported in Phase 1)
- WebSocket-based real-time push notifications
- Moderation review dashboards

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
