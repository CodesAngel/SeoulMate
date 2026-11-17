# Design

Mockups for planned SeoulMate features. Nothing here is used by the app.

| Folder | What it is |
|---|---|
| `fan-features/` | Proposals for the six fan features in `docs/plans/FAN_FEATURES_PLAN.md` |

## fan-features

Open `fan-features/index.html` in a browser. It links to one page per feature (`1-actor-pages.html` … `6-airing.html`). Each page has:

- **Today and Proposed side by side**, on a phone (390 px) and on a computer (1280 px, scaled to fit), at the same scale. "Today" is a screenshot of the live site.
- **Buttons** to switch the mock's state (for example signed out / signed in, or each Wrapped slide) and theme (light / dark). Most buttons inside the mocks work too.
- **What changes**, **Details**, **Cost** and **To decide** below the mock.

Files:

| Path | Contents |
|---|---|
| `screens/*.html` | The mocks. Each loads `assets/site.css`, so the header, drama cards, buttons and colours are the site's real ones. |
| `assets/site.css` | A copy of the site's compiled CSS from `next build` (2026-11-16). Recopy it from `frontend-web/.next/static/chunks/` after big style changes. |
| `assets/mock.js`, `mock.css` | Icons, the real header markup, drama cards, and state switching for the mocks. |
| `assets/doc.js`, `doc.css` | The proposal pages: Today/Proposed figures, toggles, scaling. |
| `today/` | Screenshots of the live site taken on 2026-11-16 (WebP). |
| `posters/` | Small copies (300 px) of the real catalog posters used in the mocks. |
| `thumbs/` | Previews used on the index page. |

Drama titles, ratings, years, episodes, casts, writers, airing dates and the actor chains are real catalog data. User names, likes, ratings and quiz scores are sample data. Quiz fan art isn't copied here (rights); a placeholder stands in.

Fonts load from Google Fonts, so the pages need an internet connection to look right.
