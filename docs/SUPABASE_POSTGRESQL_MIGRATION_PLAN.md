# Supabase PostgreSQL migration plan

Date: 2026-10-04. Status: implementation in progress. The local database foundation, catalog migration, verified poster Storage migration, poster URL cutover, authentication, and persistent watchlists/ratings are complete; hosted deployment and the profile/preference/analytics cutover remain.

## Implementation progress

- [x] Initialize the project-scoped local Supabase stack.
- [x] Configure ignored local backend and frontend environment files.
- [x] Add SQLAlchemy, Psycopg, Pydantic Settings, and Alembic.
- [x] Create and apply the initial 14-table schema locally.
- [x] Enable and verify Row Level Security and Supabase Auth foreign keys.
- [x] Validate and import all 2,081 dramas with stable FAISS positions and local poster IDs.
- [ ] Integrate FastAPI reads and writes with PostgreSQL.
- [x] Add Supabase Auth to Next.js and JWT verification to FastAPI.
- [x] Generate poster thumbnails and upload the local poster collection to Storage.
- [x] Migrate frontend watchlists, viewing statuses, and ratings.
- [ ] Migrate generated profiles, learned preferences, and analytics events.
- [ ] Validate and deploy the schema and catalog to the hosted project.

## Decisions

- Use Supabase PostgreSQL as SeoulMate's permanent application database.
- Keep FastAPI as the application and recommendation API.
- Use Supabase Auth, starting with email and password authentication.
- Use Next.js for the production frontend.
- Keep JSON as the HTTP request and response format; replace JSON and CSV files only as permanent application storage.
- Import the 2,081-drama catalog into PostgreSQL.
- Start production user data clean. Do not import the existing generated test analytics or anonymous profiles; retain those files as an archive.
- Keep the fine-tuned SBERT model, FAISS index, BM25 search, ranking configuration, query-intent priors, and multi-facet scoring outside PostgreSQL.
- Use the 2,081 local originals in `scrapers/DramaList_Scrapper/output/drama_image_by_id/`. Do not fetch posters from online sources at runtime.
- Store poster originals and locally generated WebP thumbnails in Supabase Storage for deployment.
- Access application data primarily through FastAPI so business logic and database access remain portable to another PostgreSQL provider.
- Defer pgvector until there is measured value in replacing or supplementing FAISS.

## Target architecture

```text
Next.js frontend
  |- Supabase Auth
  |- public poster delivery
  `- JSON API requests
             |
             v
FastAPI backend
  |- JWT verification and authorization
  |- business and personalization logic
  |- FAISS, BM25, and ranking rules
  `- SQLAlchemy repositories
             |
             v
Supabase PostgreSQL
  |- drama catalog
  |- user profiles and preferences
  |- watchlists and ratings
  `- searches, recommendations, and interactions

Supabase Storage
  |- original posters
  `- optimized WebP card thumbnails
```

The browser must never receive the database password or Supabase secret/service-role key. Public visitors may browse and search. Authentication is required to synchronize profiles, watchlists, ratings, preferences, and history.

## Current migration inventory

| Data | Current size | Records | Destination |
| --- | ---: | ---: | --- |
| Final drama catalog | 2.14 MiB | 2,081 dramas, 16 source columns | PostgreSQL |
| Runtime analytics and profiles | 2.15 MiB | 1,057 interactions, 525 searches, 345 user-stat entries, 3 profiles | Archive; not imported initially |
| Complete ID-based poster collection | 301.95 MiB | 2,081 JPG files | Supabase Storage later |
| Production FAISS index and metadata | 8.16 MiB | 2,081 indexed dramas | Application artifact |
| Ranking indexes and configuration | 2.18 MiB | Derived and curated data | Application artifact |

Of the 345 current user-stat entries, 338 have test IDs. There is no reliable mapping from the anonymous local IDs to future Supabase Auth users. A clean start avoids attaching generated or ambiguous behavior to real accounts.

The current Supabase database reports 28 MB in use. The catalog, schema, and indexes should initially keep the project well below the 500 MB free-plan database limit. The poster originals use about 302 MiB of the 1 GB file-storage allowance. Monthly image delivery, rather than database capacity, is the first resource to monitor.

## Phase 1: Supabase project preparation

1. Select the SeoulMate Supabase project and choose a region close to the deployed FastAPI service.
2. Enable email and password authentication. Additional OAuth providers can be added later.
3. Store the following values in ignored local environment files:

   ```env
   DATABASE_URL=
   SUPABASE_URL=
   SUPABASE_PUBLISHABLE_KEY=
   SUPABASE_SECRET_KEY=
   ```

   The dashboard may label the last two as the anonymous and service-role keys. Only the publishable/anonymous key may be used in the browser.
4. Use the existing project as the development environment. Create a separate production project before public release if the available project quota and deployment plan allow it.
5. Record the selected project region, database connection type, and environment ownership in the deployment documentation without recording secrets.

## Phase 2: Backend database foundation

1. Add SQLAlchemy 2, a supported PostgreSQL driver, Alembic, and environment-based settings to the FastAPI backend.
2. Add database engine and session lifecycle management suitable for the Supabase connection pooler.
3. Add a repository layer so API handlers and recommendation services do not contain raw connection management.
4. Add a database health check that does not expose connection details.
5. Track every schema change in Alembic. Do not make unrecorded production-only schema changes in the dashboard.
6. Support a temporary migration setting such as `DATA_SOURCE=postgres`. Keep the final CSV available for rollback until PostgreSQL validation is complete.

## Phase 3: Database schema

### Catalog tables

```text
dramas
genres
drama_genres
people
drama_credits
keywords
drama_keywords
```

The `dramas` table should include a generated primary key, a stable source key, the existing FAISS catalog position, an image identifier, a URL slug, scalar catalog fields, a poster storage key, and timestamps. Titles must not be used as primary keys because titles can repeat or change.

Normalized relationship tables support reliable filtering by genre, keyword, actor, director, and screenwriter. Appropriate unique constraints must prevent duplicate relationships.

### User and activity tables

```text
profiles
watchlist_items
ratings
user_preferences
interactions
search_events
recommendation_events
```

Required constraints include:

- one profile per authenticated user;
- one watchlist record per user and drama;
- one rating per user and drama;
- ratings constrained to the supported range;
- valid user and drama references for interactions;
- explicit behavior for deleting or anonymizing a user;
- indexed user, drama, action, and timestamp columns used by application queries.

Activity tables should store drama IDs and compact event data. They must not duplicate complete drama descriptions, cast lists, or ranking payloads in every event.

## Phase 4: Authentication and authorization

1. Next.js performs registration, login, logout, and session refresh through Supabase Auth.
2. Next.js sends the current access token to FastAPI in the authorization header.
3. FastAPI verifies the JWT and obtains the authenticated Supabase user ID.
4. Every private query scopes reads and writes to that user ID.
5. Enable Row Level Security on exposed tables and define explicit grants and policies.
6. Disable unauthenticated writes to user data.
7. Keep privileged database and Supabase keys on the server.
8. Add ownership tests proving one account cannot read or change another account's profile, ratings, or watchlist.

## Phase 5: Catalog import

Create an idempotent import command for `data/final/kdrama_dataset.csv`.

The importer must:

1. Parse all 2,081 source records.
2. Preserve the row-to-FAISS relationship through a stable catalog position.
3. Derive and store the poster image identifier without retaining an online runtime dependency.
4. Insert or update dramas without duplicating rows when the command is rerun.
5. Populate genres, keywords, people, and their relationships.
6. Report invalid values, duplicate source keys, ambiguous titles, and missing poster mappings.
7. Run in a transaction or use a staging-and-publish process so a failed import does not leave a partial catalog.

The initial acceptance checks are:

```text
Source drama records:       2,081
Imported drama records:     2,081
Mapped local posters:       2,081
Missing poster mappings:        0
Invalid foreign keys:           0
```

The import report should also record a source-file hash and catalog version for comparison with the deployed FAISS artifacts.

## Phase 6: Poster preparation and storage

Use `scrapers/DramaList_Scrapper/output/drama_image_by_id/` as the source. It is the complete active set; the older `drama_image/` directory contains only 2,077 files and must not be uploaded as a second copy.

1. Keep every original JPG unchanged.
2. Generate a WebP card thumbnail locally while preserving aspect ratio.
3. Associate both variants with the same numeric PostgreSQL drama ID.
4. Verify both variants for all 2,081 dramas before upload.
5. Upload into a public bucket with a stable layout:

   ```text
   drama-posters/
   `- dramas/{drama_id}/
      |- original.jpg
      `- thumbnail.webp
   ```

6. Store both the original and thumbnail object paths in PostgreSQL.
7. Use card thumbnails on lists and recommendations, originals on detail pages, lazy loading, and long browser cache headers.
8. Remove online poster fallback after the Storage mapping passes validation.

The target is to keep originals plus thumbnails below roughly 450 MB. An average 30-50 KiB card thumbnail will materially reduce the free plan's egress consumption compared with serving every original on result pages.

## Phase 7: Recommendation integration

Keep the current SBERT, FAISS, BM25, ranking-prior, query-intent, and multi-facet scoring implementation.

```text
query
  -> FAISS and BM25 candidate generation
  -> current ranking and personalization
  -> stable drama IDs
  -> batched PostgreSQL metadata lookup
  -> JSON API response
```

Do not query PostgreSQL once per result. Resolve recommendation identifiers in one batch. Cache stable catalog data in the backend where useful while treating PostgreSQL as the canonical application catalog.

Record a catalog version alongside each index release. When catalog content used by embeddings changes, update PostgreSQL, rebuild matching indexes and metadata, run regression evaluation, and deploy the compatible artifacts together. See [Automatic dataset update plan](AUTOMATED_DATASET_UPDATE_PLAN.md) for the broader refresh workflow.

## Phase 8: Frontend migration

1. Add registration, login, logout, and account states to Next.js.
2. Replace browser-only profiles, ratings, and watchlists with authenticated FastAPI endpoints.
3. Keep public discovery, search, detail, and similar-drama pages available without login.
4. Preserve an anonymous local watchlist for guests if desired.
5. After sign-in, offer to merge locally stored watchlist items and ratings into the account, then treat PostgreSQL as the permanent source.
6. Use optimistic interactions with visible success, retry, empty, and error states.
7. Keep API requests and responses in JSON.
8. Load poster thumbnails on cards and original posters only when the detail page requires them.

## Phase 9: Validation

Before switching production traffic, verify:

- all 2,081 catalog rows and poster mappings;
- no runtime poster request depends on MyDramaList or another external image host;
- authentication token validation and user-data isolation;
- persistent watchlist add, remove, and merge behavior;
- rating create and update behavior;
- search filters and drama-detail responses;
- FAISS result positions and PostgreSQL IDs remain aligned;
- recommendation regression results remain within the accepted baseline;
- all original and card poster URLs return successfully;
- desktop and mobile frontend flows;
- migration rollback from PostgreSQL to the preserved catalog snapshot.

## Phase 10: Rollout and cleanup

Deploy in this order:

```text
1. Database migrations
2. Catalog import and validation
3. Poster thumbnail generation and upload
4. FastAPI PostgreSQL integration
5. Authentication and authorization
6. Profile, watchlist, and rating persistence
7. Next.js integration
8. Search and recommendation event persistence
9. Production validation
10. Legacy runtime cleanup
```

Keep the CSV, runtime JSON files, and the prior application release until production has been stable. Create a logical database backup before substantial migrations. After validation, remove obsolete JSON write paths while retaining archived data and reproducible import tooling.

## Free-plan capacity and monitoring

Monitor Supabase usage weekly during development and beta.

| Resource | Current or expected initial use | Review threshold |
| --- | ---: | ---: |
| Database | About 33-43 MB after migration | 350 MB |
| File storage | About 302 MB plus thumbnails | 800 MB |
| Egress | Traffic-dependent | 70% of monthly allowance |
| Log ingestion | Currently about 0.01 GB | 70% of monthly allowance |
| Monthly active users | Currently 4 | 40,000 |

Image delivery is the likely first free-plan constraint. Use thumbnails, public CDN caching, lazy loading, and stable URLs. Reduce database egress by selecting only required fields, batching metadata queries, and caching the stable catalog in FastAPI. The recommendation model and FAISS artifacts remain on the backend host, whose memory and compute must be planned separately from Supabase.

## Documentation deliverables

Implementation must update:

- the root `.env.example` and frontend environment example;
- the root README and relevant component READMEs;
- local database and migration commands;
- authentication setup;
- catalog import and poster-upload procedures;
- deployment, backup, and recovery instructions;
- the changelog.

## Delivery milestones

1. **Database foundation:** configuration, SQLAlchemy, Alembic, initial schema, health check.
2. **Catalog migration:** idempotent importer, 2,081-row validation, stable recommendation mapping.
3. **Authentication and user data:** Supabase Auth, protected APIs, profiles, watchlists, ratings, preferences.
4. **Poster deployment:** locally generated thumbnails, Storage upload, CDN paths, external fallback removal.
5. **Frontend migration:** authentication UI, persistent user features, guest-data merge, loading and failure states.
6. **Release validation:** security, data integrity, recommendation regression, image scan, monitoring, documentation.

The first implementation batch is milestone 1 followed by the catalog importer from milestone 2. No legacy data path should be removed until the imported catalog and recommendation mapping pass their acceptance checks.
