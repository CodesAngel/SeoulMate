# Personalization quick start

Updated: 2026-10-04. See the [quick start](QUICKSTART.md) to launch the backend and internal frontend.

## Build a profile

In the internal frontend, use My Profile to rate dramas you have watched. Search and watchlist interactions can also contribute to your preferences. Use the same user ID across interactions and recommendation requests.

The backend stores profiles through `backend/user_profile.py`. `backend/personalization.py` applies genre, actor, director, and theme preference boosts to recommendation results. These factors adjust ranking; they are not measured accuracy gains or guaranteed percentages for an individual drama.

## API examples

With the backend running on its default port:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/profile/user_123'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8001/profile/user_123/rate?drama_title=Hospital%20Playlist&rating=9.5'
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/recommend?title=medical%20drama&user_id=user_123&top_n=10'
```

Use a drama title from the current catalog. Check the response's `personalization` field to see whether personalization was applied. Explore the API request and response schemas at `http://127.0.0.1:8001/docs`.

## Troubleshooting

- If rating fails, confirm the backend is running and the title exists in the catalog.
- If results do not appear personalized, check the user ID and profile response, and inspect backend logs for personalization errors.
- The historic Phase 2 diagrams and examples are in [archived/ARCHITECTURE_PHASE2.md](archived/ARCHITECTURE_PHASE2.md). The [original guide](archived/PERSONALIZATION_QUICK_START_LEGACY.md) preserves the older UI walkthrough and illustrative boost values.
