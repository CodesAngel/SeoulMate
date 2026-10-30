# Project documentation

Organized by purpose on 2026-10-31.

```
docs/
├── guides/       how to run and use SeoulMate
├── deployment/   how production is set up
├── plans/        design and rollout plans
├── archived/     past designs and results (not current guidance)
├── assets/       images used by the root README
└── internal/     private, gitignored (exists only on the maintainer's PC)
```

## Guides

| Document | Purpose |
| --- | --- |
| [Quick start](guides/QUICKSTART.md) | Full local setup: install, database, API, website, accounts, community testing, posters, stopping services |
| [Catalog updates](guides/CATALOG_UPDATES.md) | Scrape new dramas, rebuild the index, and release with `scripts/update_catalog.py` |
| [Community](guides/COMMUNITY.md) | Community routes, database and security, API endpoints, trending formula, spoilers |
| [Personalization guide](guides/PERSONALIZATION_QUICK_START.md) | Profile and recommendation API usage |
| [Training guide](../training/README.md) | Active training and index pipeline |
| [Scraper guide](../scrapers/DramaList_Scrapper/README.md) | Data collection scripts |
| [Web frontend guide](../frontend-web/README.md) | Next.js app: running locally, data modes, production settings |

## Deployment

| Document | Purpose |
| --- | --- |
| [Deployment architecture](deployment/DEPLOYMENT_ARCHITECTURE.md) | Live since 2026-10-31: website on Vercel, API on an Azure VM, data on hosted Supabase; setup, commands and the developer PC's role |

## Plans

| Document | Purpose |
| --- | --- |
| [Supabase PostgreSQL migration plan](plans/SUPABASE_POSTGRESQL_MIGRATION_PLAN.md) | Database, authentication, Storage and rollout plan; catalog, posters, Auth, watchlists and ratings implemented; hosted since 2026-10-30 |
| [Automatic dataset update plan](plans/AUTOMATED_DATASET_UPDATE_PLAN.md) | Update manager and scheduled workflow; the one-command release exists as `scripts/update_catalog.py`, scheduling is not set up yet |

## Internal (private)

`docs/internal/` is listed in `.gitignore`, so it never reaches GitHub. It holds the details the public docs leave out: server addresses and specs, account names, costs, exact schedules, and step-by-step operations (`README.md`, `DEPLOYMENT_INTERNAL.md`, `RUNBOOK.md`). It contains no passwords or keys, only where each one is stored.

## Historical documents

Files in [archived/](archived/) preserve past designs, results, and instructions. They are not current setup guidance.

Archived during the 2026-10-04 review:

- `QUICKSTART_LEGACY.md`: outdated 1,922-drama snapshot, missing script paths, and old setup instructions. Replaced by the current quick start.
- `MODEL_UPGRADE_OVERVIEW.md`: historical upgrade proposal with projected accuracy gains, not measured guarantees. See the root README and linked evaluation reports for the current baseline.
- `ARCHITECTURE_PHASE2.md`: historical Phase 2 implementation snapshot and illustrative results.
- `PERSONALIZATION_QUICK_START_LEGACY.md`: original UI walkthrough and illustrative boost claims; replaced by a concise API-based guide.

The existing `archived/docs_guide.txt` relocation is retained.
