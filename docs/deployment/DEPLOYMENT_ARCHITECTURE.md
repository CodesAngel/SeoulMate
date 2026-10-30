# Deployment Architecture

Where each part of SeoulMate runs in production. The search engine runs on the VM because it needs RAM and local files. Everything that stores data or belongs to users runs on Supabase.

**Live since 2026-10-31:**

| Part | Where | URL |
|---|---|---|
| Website | Vercel | https://seoulmate-azure.vercel.app |
| API | Azure VM | https://seoulmate.indiasouthcentral.cloudapp.azure.com |
| Database, Auth, Storage | Supabase (Tokyo) | Supabase dashboard |

## Azure VM: search engine

A small Linux VM on Azure (India region). **Live since 2026-10-31** at `https://seoulmate.indiasouthcentral.cloudapp.azure.com`.

Chosen over Hugging Face Spaces, whose free tier no longer runs Docker Spaces (PRO required since 2026).

- **Code**: a clone of the GitHub repo in `~/SeoulMate` on the VM (update with `git pull`).
- **Python**: `.venv` with only the backend's packages, pinned in `backend/requirements-server.txt` (PyTorch 2.13.0 CPU from the PyTorch CPU index, then `pip install -r backend/requirements-server.txt`).
- **Search files**, not in Git, streamed from the PC with `tar | ssh` (1.2 GB, 2 minutes; checksums verified):
  - `training/models/sbert-finetuned-full` (1.1 GB) and `training/models/cross-enc-excellent` (88 MB)
  - `training/faiss_index/` (`index.faiss`, `meta.pkl`, `dataset.csv`, `manifest.json`)
  - `backend/ranking/indexes/` comes with Git; `backend/runtime_data/` is created by the backend and starts empty.
- **Service**: systemd unit `seoulmate-api` runs `app.py` in `backend/` (`SEOULMATE_RELOAD=0`), reachable only through Nginx; it starts on boot and restarts on failure. Logs: `journalctl -u seoulmate-api`. Startup takes about 2 minutes while the models load.
- **Nginx and Let's Encrypt**: Nginx proxies to the backend; a Let's Encrypt certificate provides HTTPS (with an HTTP → HTTPS redirect) and renews automatically.
- **Production `.env`**: `backend/.env` on the VM with the live database and Supabase settings, plus `FRONTEND_URL=https://seoulmate-azure.vercel.app`. The backend allows only that origin plus `localhost:3000` (CORS); without it, the browser's `OPTIONS` preflight gets `400` and every search from the site fails. Restart `seoulmate-api` after changing it.
- **Checked 2026-10-31**: accuracy test against the VM 89.10% (identical to the PC), regression 33/33.

Common commands:

```bash
sudo systemctl restart seoulmate-api        # after git pull or new index files
journalctl -u seoulmate-api -f              # follow the log
sudo certbot certificates                   # certificate expiry
```

## Live Supabase: data, users and files

Region **Tokyo (ap-northeast-1)**. Mumbai (ap-south-1) would be closest to the VM, but Supabase cannot move a project between regions. Measured from the VM: about 117 ms per database round trip.

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

Live since 2026-10-31 at **https://seoulmate-azure.vercel.app** (Hobby plan, connected to the GitHub repo; every push to `main` deploys).

- The Next.js app in `frontend-web/` (**Root Directory** `frontend-web`, Next.js preset).
- Environment variables:
  - `NEXT_PUBLIC_API_URL` = `https://seoulmate.indiasouthcentral.cloudapp.azure.com`
  - `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (the **publishable** key only)
  - `NEXT_PUBLIC_SITE_URL` = `https://seoulmate-azure.vercel.app` (link previews and canonical URL; baked in at build time, so redeploy after changing it)
- Never put the secret key or the database URL here: every `NEXT_PUBLIC_` value is visible in the browser.
- If the domain changes, update `NEXT_PUBLIC_SITE_URL`, the VM's `FRONTEND_URL`, and the Supabase Auth URL Configuration together.

## Developer PC: catalog updates (for now)

- The scraper, `data/final`, the original poster folders and `scripts/update_catalog.py`.
- These stay on the PC because:
  - the scraper steps hardcode `D:\...` paths;
  - rebuilding the index is too heavy for a 2 GB VM.
- After each release, send two things to production:
  1. **New index files**: copy `training/faiss_index/` to the VM (`tar cf - training/faiss_index | ssh <user>@<vm> 'cd ~/SeoulMate && tar xf -'`), then `sudo systemctl restart seoulmate-api`.
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
- **Free-tier pausing**: projects pause after about a week with no activity. The GitHub Actions workflow `.github/workflows/supabase-keepalive.yml` reads one row twice a week (Monday and Thursday) to keep the project awake, even when the PC is off. GitHub turns off scheduled workflows in a public repository after 60 days without activity; the workflow re-enables itself through the API on every run to reset that timer. A second, independent pinger runs on cron-job.org (set up 2026-10-30): the same request every few days, with email alerts if it fails or gets disabled.
- **Email**: Supabase's built-in email has a very low rate limit. Set up your own SMTP if sign-up emails matter.

## Migration order

Steps 1–7 were done on 2026-10-30 (details in `CHANGELOG.md`).

1. ✅ Back up the local catalog and dump the local schema.
2. ✅ Create the Supabase project (Tokyo).
3. ✅ Run `alembic upgrade head` against the live database and compare its schema with the local one.
4. ✅ Import the catalog.
5. ✅ Run the poster audit and upload the posters.
6. ✅ Point the backend at the live database and re-run the eval and regression suite: 89.10% overall, regression 33/33, identical to local.
7. ✅ Switch the frontend to the live project and set the Auth URLs.
8. Test sign-up, login, watchlist, ratings, community and avatars in the browser.
9. ✅ Backend on the VM (2026-10-31): HTTPS, systemd service, accuracy 89.10%, regression 33/33.
10. ✅ Frontend on Vercel (2026-10-31): https://seoulmate-azure.vercel.app.
11. ✅ `FRONTEND_URL=https://seoulmate-azure.vercel.app` on the VM (fixed the CORS `400`), and the Vercel domain added to Supabase Auth URL Configuration.
12. Add a cron-job.org monitor for the backend URL with the "TLS certificate is about to expire" alert on.

## Still open

- Whether the scraper and update pipeline should move to the VM. Keep them on the PC until the scraper paths work on Linux and a few releases have gone to production.
