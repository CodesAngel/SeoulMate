# SeoulMate Web

The production user interface for SeoulMate, built with Next.js 16, React 19, TypeScript, Tailwind CSS, TanStack Query, Zod, and Lucide icons.

Streamlit remains available under `frontend/` for internal model testing and analytics. This application provides the public discovery experience.

## Features

- Natural-language K-drama discovery with genre, year, rating, and sorting filters
- Responsive poster-led home and result pages
- Supabase Storage thumbnails on cards and original posters on detail pages; external poster hosts are not rendered
- Shareable drama detail pages with cast, themes, ratings, and similar titles
- PostgreSQL-backed account watchlist, viewing statuses, and personal ratings with guest-list merge on sign-in
- Supabase email/password registration, login, logout, session refresh, and password recovery
- Authenticated identity with anonymous fallback for the existing personalization flow
- Rating and taste-profile interface
- Loading, empty, error, image-fallback, and reduced-motion states

## Run locally

Start Docker Desktop and the local Supabase stack from the repository root:

```powershell
supabase start
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Then start the FastAPI backend:

```powershell
.\scripts\run_backend.ps1
```

Then start this frontend:

```powershell
.\scripts\run_web_frontend.ps1
```

Open `http://localhost:3000`. Local confirmation and password-reset emails are captured at `http://127.0.0.1:54324`; they are not sent externally.

The frontend uses `http://127.0.0.1:8001` by default. To use another API address, copy `.env.example` to `.env.local` and change `NEXT_PUBLIC_API_URL` before building or starting the app. Set `NEXT_PUBLIC_SITE_URL` to the public frontend origin so canonical and social metadata use the deployed URL.

## Commands

```powershell
npm install
npm run dev
npm run lint
npm run typecheck
npm run build
npm run start
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Personalized discovery home |
| `/discover?q=...` | Search results and filters |
| `/drama/[title]` | Drama information and similar recommendations |
| `/watchlist` | Synced dramas, viewing statuses, and personal ratings |
| `/profile` | Taste profile, activity, and rating form |
| `/auth/login` | Email/password sign in |
| `/auth/sign-up` | Account registration |
| `/auth/forgot-password` | Request a password-reset email |
| `/auth/update-password` | Set a password after opening the recovery link |
| `/account` | Protected account details and sign out |

Signed-in watchlists and ratings use authenticated FastAPI endpoints and PostgreSQL. Signed-out visitors retain a browser-local guest list, which is merged into their account on sign-in without overwriting existing account statuses. The generated taste-profile API still uses legacy local JSON; preferences and profile generation are the next application-data phase.
