# Fan features plan: beyond recommendations

Status: proposed 2026-11-16. **Feature 2 (K-drama Wrapped) is built and live** (2026-11-17, see the CHANGELOG); the other five are proposals. Six features that give fans something to do on SeoulMate besides searching. Each one uses data the project already has; none needs an LLM.

Mockups: open `design/fan-features/index.html`. One page per feature shows today's site next to the proposed design (phone and computer, light and dark, every state), with what changes and open questions.

Suggested build order (reasons in the summary at the end):

| # | Feature | Size | Needs first |
|---|---|---|---|
| 1 | Actor and writer pages | M | Fix issue #4 item 2 (duplicate actor spellings) |
| 2 | K-drama Wrapped | M | **Built** (2026-11-17) |
| 3 | Daily "Guess the drama" | M | Quiz labels checked (`quiz/README.md`, Phase 0) |
| 4 | Six degrees of K-drama | S | Feature 1 (reuses its people data and links) |
| 5 | Fan lists | M | Nothing |
| 6 | Airing now and calendar | L | A scraper change (air weekdays) |

Sizes: S = about one working session, M = two to three, L = four or more.

What the data already holds (checked 2026-11-16): 2,130 dramas with `actors` (main cast first), `directors`, `screenwriters`, `episodes`, `duration` ("1 hr. 10 min."), `aired` ("Aug 19, 2009 - Oct 8, 2009"), `publisher` (network; blank for 534), `keywords`, `watchers`. In Postgres: `people` (4,577), `drama_credits` (role `actor` / `director` / `screenwriter`, `billing_order`), `watchlist_items` (status `planned` / `watching` / `completed` / `paused` / `dropped`, with `updated_at`), `ratings`. 3,327 actors, 1,363 of them in 3 or more dramas. The episode tracker on drama pages saved progress in the browser only (`localStorage`); since Wrapped it saves to `watchlist_items.episodes_watched` for signed-in users.

---

## 1. Actor and writer pages

**What fans get:** a page for every actor, director and writer. It lists all their dramas, shows how many you've seen, names the co-stars they work with most, and suggests where to start. Fans can follow a person.

### Screens

`/people/park-bo-young` (phone layout):

```
┌──────────────────────────────────┐
│ ACTOR · 14 DRAMAS                │
│ Park Bo Young                    │
│ Known for: Strong Girl Bong Soon,│
│ Oh My Ghost, Daily Dose of Sun.. │
│ [♡ Follow]                       │
├──────────────────────────────────┤
│ You've watched 4 of 14  ▓▓▓░░░░░ │
│ Start here → Oh My Ghost (8.3)   │
├──────────────────────────────────┤
│ Dramas            [Lead ▾][Year ▾]│
│ ┌────┐ ┌────┐ ┌────┐             │
│ │post│ │post│ │post│  ← cards    │
│ └────┘ └────┘ └────┘  with LEAD /│
│                       ✓ WATCHED  │
├──────────────────────────────────┤
│ Often works with                 │
│ (Park Hyung Sik ×2) (Jo Jung Suk)│
├──────────────────────────────────┤
│ Directors and writers            │
│ Yoo Je Won · Baek Mi Kyung …     │
└──────────────────────────────────┘
```

- Cast names on drama pages become links to these pages, and so do director and writer names.
- Actor searches on Discover ("Park Bo Young") get a small "See all of Park Bo Young's dramas →" link above the results.
- **No actor photos:** the catalog has none, and scraping photos of real people raises rights questions. The header shows a collage of their top posters instead.

### Data and API

- **No backend change for the page itself.** The catalog is public-read, so the page reads `people`, `drama_credits` and `dramas` from Supabase REST on the server, the same way `lib/catalog-server.ts` does, cached for a day.
- **"Lead" or "supporting"** comes from `billing_order`: 1–2 is lead (to be checked on a sample).
- **"Known for"** is the top 3 dramas by `watchers`. **"Start here"** is their highest-rated lead role you haven't watched.
- **"Often works with"** counts people who share 2 or more dramas with this person. It's computed on the server with one query over `drama_credits`.
- **Following** needs a new table, `person_follows (user_id, person_id, created_at)`, with RLS like `watchlist_items`, plus `PUT` / `DELETE /me/follows/{person_id}` and `GET /me/follows` on the `/me` router.
- **Later:** followed people feed into personalization (`user_profile.py` already boosts by actor) and a home row, "New from people you follow".
- **Slug:** the name in kebab case (`park-bo-young`). Duplicate names would get a number suffix; the `people.name` column is unique, so this can't happen yet.

### SEO

Add people with 3 or more dramas (about 1,400) to `sitemap.ts`, with `Person` JSON-LD and a title like "Park Bo Young dramas (14) | SeoulMate".

### Risks

- **Duplicate spellings** (Park Seo Joon vs Park Seo Jun, issue #4 item 2) would split one actor into two pages. Fix that first.
- **Two different people with the same name** (two actors called Kim Soo Hyun, issue #4 item 9) are merged into one, because the scraper keeps names, not MyDramaList person IDs. Storing the person ID in the scraper is the proper fix. Until then, a page could hide credits that don't fit (for example, different decades with no shared co-stars), but that is a guess.

---

## 2. K-drama Wrapped (year in review)

**What fans get:** a personal summary of their year in K-dramas, shown as a few swipeable "slides", that ends with a shareable image card.

> **Built 2026-11-17** (CHANGELOG 2026-11-17 and 2026-11-18). Differences from this plan: progress is saved through a new `PATCH /me/watchlist/{id}/progress` instead of the watchlist `PUT`; a new `completed_at` column decides which year a drama counts for; slides with nothing to show (actor, trope, top-rated) are skipped; the top trope weights keywords by rarity and leaves out non-trope keywords; fan types are genre-share rules (e.g. "The Thrill Seeker") with "The Binger" and "The Explorer" as fallbacks; the share card has a "Show my name" checkbox; the Profile banner shows all year (a quieter "so far" version outside 1 December – 15 January). The text below is the original proposal.

### Screens

`/wrapped/2026`, one slide at a time (tap to go on):

```
 slide 1                slide 2               slide 3
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Your 2026     │     │ Your most-    │     │ You can't     │
│ in K-dramas   │     │ watched actor │     │ resist…       │
│               │     │               │     │ ENEMIES TO    │
│ 23 dramas     │ ──▶ │ Lee Jong Suk  │ ──▶ │ LOVERS        │
│ 312 episodes  │     │ 3 dramas      │     │ in 7 of your  │
│ 287 hours     │     │ [posters]     │     │ 23 dramas     │
└───────────────┘     └───────────────┘     └───────────────┘
 slide 4: genre mix (bar)   slide 5: your top-rated drama
 slide 6: share card ──▶ [Download image] [Copy link]
```

Share card (1080×1350 image):

```
┌──────────────────────────┐
│ SeoulMate Wrapped 2026   │
│ 23 dramas · 287 hours    │
│ Top actor: Lee Jong Suk  │
│ Top trope: Enemies to    │
│ lovers                   │
│ #1 drama: [poster] …     │
│ seoulmate-azure.vercel.app│
└──────────────────────────┘
```

### How each number is worked out (no LLM)

| Stat | Source |
|---|---|
| Dramas this year | `watchlist_items` with status `completed` and `updated_at` in the year |
| Episodes | `episodes` of those dramas, plus episodes watched on dramas still `watching` |
| Hours | episodes × `duration` (parse "1 hr. 10 min." → 70 min; default 60 if blank) |
| Top actor | the most frequent lead actor (`billing_order` ≤ 3) across those dramas |
| Top trope | the most frequent keyword, weighted so common tags ("Romance") don't always win (IDF, as in similar-drama scoring) |
| Genre mix | genre counts, top 5 |
| Top-rated | the user's highest `ratings` row this year |
| "Fan type" label | rule-based from the stats, e.g. "The Binger" (> 200 hours), "The Romantic" (romance ≥ 60%), "The Sleuth" (thriller/mystery ≥ 40%) |

### Data and API

- **Before building:** move the episode tracker from `localStorage` to the database (a new column `watchlist_items.episodes_watched`, saved through the existing watchlist `PUT`). Without it, "episodes" and "hours" can only count completed dramas. Feature 6 also uses this column.
- **API:** `GET /me/wrapped?year=2026` on the backend returns the stats as JSON. It's computed on request; at this size that takes milliseconds.
- **Sharing:** `POST /me/wrapped/share` saves a snapshot to a new table, `wrapped_shares (id, user_id, year, stats_json, created_at)`, and returns a link `/wrapped/s/{id}`. The shared page shows the snapshot only, never live account data, and the owner can delete it.
- **Share image:** built with Next's image response API (check the Next 16 docs in `node_modules/next/dist/docs/` first, as `frontend-web/AGENTS.md` asks). It's also used as the shared page's `og:image`, so links preview nicely in chats.
- **Thin years:** Wrapped needs at least 3 dramas in the year. Below that, show "Your Wrapped unlocks after 3 completed dramas" with a link to the watchlist.

### Timing

To be useful in December 2026, it must be live by about 1 December. Fans who started using the site recently will have little history, so the first year is a soft launch.

---

## 3. Daily "Guess the drama" quiz

**What fans get:** five picture questions a day, the same for everyone. Each has four answer choices. There's a streak counter and a score they can share. The full category quiz from `quiz/README.md` stays as "Practice mode".

### Screens

`/quiz` (daily):

```
┌──────────────────────────────────┐
│ Daily quiz #12 · Nov 16  🔥 5    │
│ Question 2 of 5                  │
│ ┌──────────────────────────────┐ │
│ │        [ image ]             │ │
│ └──────────────────────────────┘ │
│ ( Goblin              )          │
│ ( Hotel del Luna       )          │
│ ( Tale of the Nine-Tailed )       │
│ ( My Demon             )          │
└──────────────────────────────────┘
 after answering: ✓/✗, the right poster, [View drama] [+ Watchlist]
```

Result screen and share text:

```
SeoulMate Daily #12  4/5  🔥5
🟩🟩🟥🟩🟩
seoulmate-azure.vercel.app/quiz
```

### Questions

- **Picture questions** use the 144 labelled images in `quiz/`. That's only about 4 weeks of content at 5 a day.
- **Poster zoom questions** make the supply effectively endless: a tight crop of a real poster (no title text; crop chosen at random away from the top and bottom thirds, where titles usually sit), from dramas with at least 20k watchers so they're guessable. Fans who answer wrong see the full poster.
- **Each day mixes** 3 picture questions and 2 poster zooms, chosen by a seed from the date, so everyone gets the same set.
- **Wrong choices** come from the same genre and decade as the right answer, so the question isn't trivial. Franchise siblings are excluded (Season 2 isn't a fair wrong answer for Season 1).

### Data and API

- **Images:** go into a new Storage bucket, `quiz-images` (public-read). `labels.json` becomes a `quiz_items` table: id, type (`cartoon` / `historical` / `reference` / `poster_crop`), image path, drama_id, crop box.
- **Endpoints:** `GET /quiz/daily?date=` returns 5 questions **without** answers; `POST /quiz/daily/answer` checks one answer. That way the answers aren't readable in the page source.
- **Scores and streaks:**
  - Guests keep their streak in `localStorage`.
  - Signed-in fans get a new table, `quiz_results (user_id, quiz_date, score, time_ms)`, unique per user per day; the streak is computed from it.
  - Optional later: a weekly leaderboard.

### Risks

- The images are fan art and drama stills owned by others (see `quiz/README.md`). For a public site, credit the artists or keep to poster crops.
- Labels must be checked before launch; a wrong answer key ruins a daily game.

---

## 4. Six degrees of K-drama

**What fans get:** a puzzle where they link two actors through dramas they share, like "Park Bo Young → Song Joong Ki in 3 steps". There's one daily pair, and a free-play mode for any two actors.

### Screens

`/connect`:

```
┌──────────────────────────────────┐
│ Today: connect                   │
│ Park Bo Young  ⟶  Song Joong Ki  │
│ Best possible: 2 steps           │
├──────────────────────────────────┤
│ Park Bo Young                    │
│   └ in [ Strong Girl Bong Soon ▾]│  ← pick a drama
│        with [ Park Hyung Sik   ▾]│  ← pick a co-star
│   └ in [ … ]                     │
│ [Check]   [Give up → show path]  │
└──────────────────────────────────┘
 result: "Solved in 3 steps (best is 2) 🟩🟩🟨" + the shortest path drawn as
 actor → drama poster → actor → …
```

### How it works

- **The graph:** actors and dramas form a graph; an actor connects to every drama they're in. It uses main cast only (`billing_order` ≤ 6), so links go through real roles, not cameos. With about 3,300 actors and 15,600 credits it's tiny.
- **Shortest path:** found with a breadth-first search, under 10 ms in memory.
- **Free play:** `GET /connect/path?from=&to=` returns the shortest path (or "no link within 6 steps").
- **Daily pair:** chosen by a date seed from actors with at least 5 dramas and a shortest path of 2–4 steps, so it's neither instant nor impossible.
- **Checking a fan's chain:** each step is checked against the same graph.
- **The dropdowns** only offer valid choices: the dramas of the current actor, then that drama's cast. A fan can't make an invalid step; the challenge is finding a short route.
- **Backend:** the graph is built at backend startup from `meta.pkl` (already in memory), in a new small module, `backend/connect.py`, with its own router. No database tables are needed; daily results can reuse `localStorage` like the quiz.

### Why S

The data is already loaded, the search is about 30 lines of code, and the actor links come from feature 1.

---

## 5. Fan lists

**What fans get:** their own named lists ("Comfort dramas for rainy days", "Best second leads", "Start here if you're new to K-dramas"), each drama with a short note. Lists can be private or public, and public lists can be liked and shared.

### Screens

```
/lists (browse)                    /lists/{id}
┌───────────────────────────┐      ┌───────────────────────────┐
│ Fan lists  [Popular|New]  │      │ Comfort dramas for rainy  │
│ ┌───────────────────────┐ │      │ days · by minji · ♥ 42    │
│ │[4 poster collage]     │ │      │ "When work is too much."  │
│ │Comfort dramas for     │ │      │ 1. Hometown Cha-Cha-Cha   │
│ │rainy days · 8 · ♥ 42  │ │      │    "The sea village heals"│
│ └───────────────────────┘ │      │ 2. Reply 1988             │
│ …                         │      │ [♥ Like] [Share] [Copy]   │
└───────────────────────────┘      └───────────────────────────┘
```

- **Drama pages** get an "Add to list" button next to "Add to watchlist". It opens a small menu of the fan's lists plus "+ New list".
- **Drama pages** also get a "Featured in fan lists" section with up to 3 public lists that include the drama.
- **Profile pages** show the fan's public lists.

### Data and API

- **New tables** (Alembic migration, RLS like the community tables):
  - `fan_lists (id, user_id, title ≤ 80, description ≤ 300, is_public, created_at, updated_at)`
  - `fan_list_items (list_id, drama_id, position, note ≤ 200)`, max 50 per list
  - `fan_list_likes (list_id, user_id, created_at)`
- **Endpoints:** a new `/lists` router in the backend, modelled on `community.py`:
  - list, create, update and delete lists;
  - add, remove and reorder items;
  - like and unlike;
  - `GET /lists?drama_id=` for the drama-page section.
- **Moderation:** list titles and notes are user text shown publicly. Reuse whatever the community posts use (length limits, a report link). Lists are private by default.

### SEO

Public lists with at least 5 dramas and 3 likes go into the sitemap. Pages like "Best second lead dramas" are the kind of thing people search for.

---

## 6. Airing now and calendar

**What fans get:** which dramas are on air this week and on which days new episodes come out, with their watchlist dramas highlighted. They can also add a calendar feed to their phone, which gives reminders without email.

### Screens

```
/airing                                   home strip (when something airs today)
┌──────────────────────────────────┐      ┌──────────────────────────────┐
│ On air this week                 │      │ New tonight: Ep 7 of         │
│ Mon  Tue  Wed  Thu  Fri  Sat  Sun│      │ [poster] Drama X  (on your   │
│      [p]  [p]       [p]  [p]  [p]│      │ watchlist) →                 │
│      [p]            [p]          │      └──────────────────────────────┘
│ ★ = on your watchlist            │
├──────────────────────────────────┤      /watchlist: "Ep 7 out today" badge
│ Coming soon (next 30 days)       │      on airing dramas you're watching
│ [p] Title · starts Dec 2 · tvN   │
└──────────────────────────────────┘
```

### Data

- **What we can already derive:** `aired` gives start and end dates, so "airing now" means start ≤ today ≤ end, and "coming soon" means a start date within 30 days. The network comes from `publisher`.
- **What we can't:** the air weekdays aren't stored. MyDramaList pages have an "Aired On" field (for example "Friday, Saturday"), and the scraper already saves those pages, so extraction needs one new field, `air_days`, carried into a new column, `dramas.air_days`.
- **Freshness:** airing data goes stale quickly. The refresh scrape (`run_pipeline.py --refresh`) would need to run on a schedule (the nightly catalog job, still an open item), at least for currently airing and upcoming dramas.
- **Which episode airs on which date:** an estimate from the start date, the air days and the episode count, labelled "expected". Korean dramas sometimes skip weeks, so it's never shown as certain.

### API and reminders

- **Endpoints:** `GET /airing?week=` and `GET /airing/upcoming` read from the catalog.
- **Calendar feed:** `GET /me/calendar.ics?token=` is a private feed with expected episode dates for the fan's `watching` and `planned` dramas, and works in Google or Apple Calendar. The token is a random per-user secret (new column `profiles.calendar_token`) that can be reset. It doesn't need email (account emails now use custom SMTP, but reminders by email would need a proper sending service).
- **Badge:** the watchlist badge uses `episodes_watched` (see feature 2) to show "1 new episode" when the expected count is ahead of the fan's progress.

### Why L

It needs a scraper change, a regular refresh, a schema change and date logic, and it's only as good as the scrape schedule.

---

## Summary and recommended order

1. **Actor and writer pages** go first: the data is ready, fans browse by actor more than anything else, and about 1,400 new pages help Google traffic. Fix the duplicate actor spellings (issue #4 item 2) before or alongside it.
2. **K-drama Wrapped**: built and live (2026-11-17), with the episode tracker moved to the database, which feature 6 can now use.
3. **Daily quiz** is the best feature for bringing people back every day. Poster zoom questions solve the small image supply.
4. **Six degrees** is a small add-on once actor pages exist.
5. **Fan lists** add community content and search pages, and need no other feature first.
6. **Airing calendar** is last, because it depends on a scheduled scraper.

Every feature adds rows to the CHANGELOG and, where search or ranking changes (the actor link on Discover, followed-people boosts), a re-run of the evaluator and the regression suite.
