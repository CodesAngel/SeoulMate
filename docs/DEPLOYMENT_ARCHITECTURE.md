# Deployment Architecture

Where each part of SeoulMate runs in production. The search engine runs on the VM because it needs RAM and local files. Everything that stores data or belongs to users runs on Supabase.

## Azure VM: search engine

VM: `seoulmate`, B1ms (2 GB), Ubuntu 24.04, India South Central, `seoulmate.indiasouthcentral.cloudapp.azure.com`.

- **FastAPI backend**: `backend/app.py` and its modules (auth, community, user_library, personalization, ranking), run as a systemd service.
- **Search files** loaded from disk at startup (about 1.2 GB, copied with `scp`):
  - live FAISS index in `training/faiss_index/` (`index.faiss`, `meta.pkl`, `dataset.csv`, `manifest.json`)
  - embedding model
  - `backend/ranking/indexes/` and `backend/runtime_data/`
- **Nginx and Let's Encrypt**: HTTPS on the VM's domain, passing requests to the backend.
- **Production `.env`**: live `DATABASE_URL` (Session pooler), `SUPABASE_URL` and the **secret key**. The secret key lives only here.
- **2 GB of swap**, because the VM has only 2 GB of RAM.

## Live Supabase: data, users and files

Region: Mumbai (ap-south-1), the closest region to the VM.

- **Postgres database**:
  - Catalog tables: dramas, genres, keywords, people, credits and their link tables
  - User tables: profiles, watchlist and ratings, episode tracker, community posts and comments
  - RLS policies and the profile-on-signup trigger
  - All created by `alembic upgrade head`
- **Auth**: sign-up, login and password reset. Set the Site URL and redirect URLs to the real domains.
- **Storage**:
  - Poster originals and WebP thumbnails, loaded directly by the frontend
  - User avatars

## Vercel: frontend

- The Next.js app in `frontend-web/`.
- Holds only the **publishable** key and the backend URL.

## Developer PC: catalog updates (for now)

- The scraper, `data/final`, the original poster folders and `scripts/update_catalog.py`.
- These stay on the PC because:
  - the scraper steps hardcode `D:\...` paths;
  - rebuilding the index is too heavy for a 2 GB VM.
- After each release, send two things to production:
  1. **New index files**: copy them to the VM, then restart the backend.
  2. **Catalog import and poster upload**: run them against live Supabase.
- Use a **separate** env file for production on the PC, never the local Docker one, and choose it on purpose. `update_catalog.py` can import with `--prune`, so pointing it at the wrong database by accident could delete production rows.

## How a request flows

```
Browser ──page──> Vercel (Next.js)
   │
   ├──search──> Azure VM (FastAPI + FAISS) ──drama details──> Supabase Postgres
   ├──login───> Supabase Auth
   └──images──> Supabase Storage
```

The VM uses FAISS to find matching dramas, then reads their details from Supabase Postgres.

## Connection and hosting notes

- **Connection string**: use the Session pooler (port 5432) with `?sslmode=require`.
  - The direct connection only works over IPv6 on the free tier, and the VM and PC probably don't have IPv6.
  - Don't use the transaction pooler (port 6543) for the backend or Alembic. It can break prepared statements and migrations.
- **Free-tier limits**: 500 MB database and 1 GB file storage. Check that the poster originals and thumbnails fit before uploading.
- **Free-tier pausing**: projects pause after about a week with no activity. A small scheduled ping from the VM keeps the project awake.
- **Email**: Supabase's built-in email has a very low rate limit. Set up your own SMTP if sign-up emails matter.

## Migration order

1. Back up the local catalog and dump the local schema.
2. Create the Supabase project in Mumbai.
3. Run `alembic upgrade head` against the live database. Diff its schema against the local dump once, to catch anything created in Studio that has no migration.
4. Import the catalog.
5. Upload the posters and run the poster audit.
6. Point the backend at the live database and re-run the eval and regression suite. Results should match local (89.00% overall, regression 33/33).
7. Switch the frontend to the live project.

## Still open

- Whether the scraper and update pipeline should move to the VM. Keep them on the PC until the scraper paths work on Linux and a few releases have gone to production.
