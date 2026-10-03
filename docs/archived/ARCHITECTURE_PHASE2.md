# Phase 2 Architecture - Personalization System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Streamlit)                                │
│                        frontend/streamlit_app.py                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐         │
│  │  🔍 Smart Search │  │  👤 My Profile   │  │  📊 Statistics     │         │
│  │                  │  │                   │  │                    │         │
│  │ • Search box     │  │ • Taste Profile   │  │ • Platform stats   │         │
│  │ • Filters        │  │ • Top Genres      │  │ • Trending         │         │
│  │ • Results        │  │ • Favorite Actors │  │ • Analytics        │         │
│  │ • +X% Match tags │  │ • Rating System   │  │ • Popular dramas   │         │
│  │ • Personalized!  │  │ • Reset Profile   │  │                    │         │
│  └─────────────────┘  └──────────────────┘  └────────────────────┘         │
│                                                                               │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ HTTP Requests
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                          BACKEND API (FastAPI)                                │
│                            backend/app.py                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  API ENDPOINTS:                                                               │
│  ┌────────────────────────────────────────────────────────────┐             │
│  │ GET  /recommend        → Personalized recommendations       │             │
│  │ GET  /profile/{user_id} → Get user taste profile            │             │
│  │ POST /profile/{user_id}/rate → Rate drama                   │             │
│  │ DELETE /profile/{user_id} → Reset profile                   │             │
│  │ POST /analytics/interaction → Log interactions              │             │
│  └────────────────────────────────────────────────────────────┘             │
│                                                                               │
│  RECOMMENDATION PIPELINE:                                                     │
│  ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌──────────────┐                 │
│  │  1  │───│  2  │───│  3  │───│  4  │───│      5       │                 │
│  │Query│   │FAISS│   │BM25 │   │Cross│   │Personalize  │                 │
│  │Parse│   │     │   │Plus │   │Enc. │   │(NEW Phase 2)│                 │
│  └─────┘   └─────┘   └─────┘   └─────┘   └──────────────┘                 │
│                                                   │                           │
│                                                   │                           │
└───────────────────────────────────────────────────┼───────────────────────────┘
                                                    │
                     ┌──────────────────────────────┴────────────────┐
                     │                                                │
                     ▼                                                ▼
    ┌────────────────────────────────┐          ┌──────────────────────────────┐
    │   USER PROFILE MANAGER         │          │  PERSONALIZATION ENGINE       │
    │   backend/user_profile.py      │          │  backend/personalization.py   │
    ├────────────────────────────────┤          ├──────────────────────────────┤
    │                                │          │                              │
    │ • Load/Save profiles           │◄─────────┤ • Calculate boosts           │
    │ • Track preferences:           │          │ • Genre boost (50%)          │
    │   - Genres                     │          │ • Actor boost (30%)          │
    │   - Actors                     │          │ • Director boost (20%)       │
    │   - Directors                  │          │ • Theme boost (40%)          │
    │   - Themes                     │          │ • Adjust alpha               │
    │   - Publishers                 │          │ • Re-rank results            │
    │ • Update from interactions     │          │                              │
    │ • Exponential Moving Avg       │          │                              │
    │ • Determine personas           │          │                              │
    │                                │          │                              │
    └────────────────┬───────────────┘          └──────────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │     USER PROFILES (JSON)       │
    │  backend/user_profiles/*.json  │
    ├────────────────────────────────┤
    │                                │
    │ {                              │
    │   "preferences": {             │
    │     "genres": {                │
    │       "Medical": 0.70,         │
    │       "Life": 0.58,            │
    │       ...                      │
    │     },                         │
    │     "actors": { ... },         │
    │     "directors": { ... }       │
    │   },                           │
    │   "persona": ["Medical Fan"],  │
    │   "statistics": { ... }        │
    │ }                              │
    │                                │
    └────────────────────────────────┘


DATA FLOW - User Interaction:
═════════════════════════════════

1. USER RATES A DRAMA
   │
   ├─► Frontend: "Rate Drama" form
   │   • User enters title + rating
   │   • Clicks "Submit Rating"
   │
   ├─► POST /profile/{user_id}/rate
   │   • Backend receives request
   │   • Finds drama in metadata
   │
   ├─► user_profile.update_from_interaction()
   │   • Calculates preference updates
   │   • Applies EMA algorithm
   │   • Updates genres, actors, directors
   │   • Saves profile to JSON
   │
   └─► Frontend shows success ✅


2. USER SEARCHES
   │
   ├─► Frontend: Search box
   │   • User enters query
   │   • Includes user_id in request
   │
   ├─► GET /recommend?title=drama&user_id=...
   │   • Query analysis (Phase 1)
   │   • FAISS + BM25 search
   │   • Cross-encoder reranking
   │
   ├─► Personalization Layer (Phase 2)
   │   • Load user profile
   │   • Calculate boosts per drama
   │   • Adjust alpha for user
   │   • Re-rank by personalized_score
   │
   └─► Frontend displays results
       • "✨ Personalized Results!" banner
       • "+34% Match" badges
       • Boosted dramas at top


3. USER CLICKS DRAMA
   │
   ├─► Frontend: "👁️ View" button
   │   • Logs interaction
   │
   ├─► POST /analytics/interaction
   │   • type: "click"
   │   • position: rank in results
   │
   ├─► analytics.py logs + updates profile
   │   • Stores click event
   │   • Calls user_profile.update_from_interaction()
   │   • Updates preferences (weaker signal)
   │
   └─► Profile improves over time 📈


ALGORITHMS:
═══════════

Exponential Moving Average (EMA):
──────────────────────────────────
new_score = (old_score × 0.8) + (interaction_weight × 0.2)

Where:
• old_score = existing preference (0-1)
• interaction_weight:
  - watched: 1.0
  - watchlist_add: 0.6
  - click: 0.3

Example:
• Genre "Medical" = 0.5
• User watches medical drama (weight=1.0)
• new_score = (0.5 × 0.8) + (1.0 × 0.2)
• new_score = 0.4 + 0.2 = 0.6 ✅


Personalization Boost:
──────────────────────
total_boost = 1.0
total_boost += genre_boost    (0 to 0.5)
total_boost += actor_boost    (0 to 0.3)
total_boost += director_boost (0 to 0.2)
total_boost += theme_boost    (0 to 0.4)

personalized_score = base_score × total_boost

Example:
• base_score = 0.75
• User loves Medical (genre match): +0.25
• User loves this actor: +0.09
• User loves this director: +0.05
• total_boost = 1.0 + 0.25 + 0.09 + 0.05 = 1.39
• personalized_score = 0.75 × 1.39 = 1.04 ✅


Dynamic Alpha Adjustment:
─────────────────────────
diversity = 1.0 - (max_genre_score - avg_genre_score)
alpha_adjustment = diversity × 0.2

personalized_alpha = base_alpha - alpha_adjustment

Where:
• Low diversity (focused user) → Lower alpha → More exploitation
• High diversity (diverse user) → Higher alpha → More exploration

Example:
• base_alpha = 0.7
• User loves only Medical (low diversity = 0.3)
• alpha_adjustment = 0.3 × 0.2 = 0.06
• personalized_alpha = 0.7 - 0.06 = 0.64 ✅
• More lexical search (finds specific medical terms)


TESTING:
════════

Test 1: User Profile Learning
├─ Create "Medical Fan" profile
├─ Watch: Hospital Playlist, Good Doctor
├─ Result: Medical genre = 0.70 ✅
└─ Persona: "Medical Fan" ✅

Test 2: Personalized Weighting
├─ Medical fan searches "drama"
├─ Result: Doctor John boosted ×1.34 ✅
├─ Thriller fan searches "drama"
├─ Result: Flower of Evil boosted ×1.34 ✅
└─ Different users → Different results ✅

Test 3: Complete Integration
├─ Rate dramas via API ✅
├─ Profile updates correctly ✅
├─ Search returns personalized results ✅
├─ Frontend displays boost badges ✅
└─ All endpoints working ✅


FILES & RESPONSIBILITIES:
═════════════════════════

backend/user_profile.py (400 lines)
├─ UserProfileManager class
├─ load_profile() - Get or create profile
├─ save_profile() - Persist to JSON
├─ update_from_interaction() - Update preferences
├─ _update_genre_preferences() - EMA for genres
├─ get_top_preferences() - Get sorted preferences
└─ _determine_persona() - Generate persona labels

backend/personalization.py (350 lines)
├─ PersonalizationEngine class
├─ personalize_results() - Apply boosting
├─ _calculate_genre_boost() - Genre matching
├─ _calculate_actor_boost() - Actor matching
├─ calculate_user_specific_alpha() - Adjust explore/exploit
└─ get_personalization_summary() - Explain recommendations

backend/app.py (+150 lines)
├─ GET /profile/{user_id} - Fetch profile
├─ POST /profile/{user_id}/rate - Rate drama
├─ DELETE /profile/{user_id} - Reset profile
└─ Modified /recommend - Include personalization

backend/analytics.py (+15 lines)
└─ log_interaction() - Auto-update profiles

frontend/streamlit_app.py (+200 lines)
├─ Enhanced "My Profile" tab
├─ Taste profile visualization
├─ Rating system
├─ Personalization badges in results
└─ Updated UI for Phase 2


VERSION HISTORY:
════════════════

v4.0 Phase 1 ✅
├─ Query intent detection
├─ Dynamic weight adjustment
├─ Query expansion
└─ Click tracking & analytics

v4.0 Phase 2 (Current) ✅
├─ User preference learning
├─ Personalized weighting
├─ Taste profile building
└─ Genre/Actor/Director boosting

v4.0 Phase 2 (Next Steps)
├─ Step 3: "Because You Watched"
├─ Step 4: Taste Profile Visualization
├─ Step 5: Recommendation Explanations
└─ Step 6: Personalized Homepage
```

**Status:** ✅ Phase 2 Step 2 COMPLETE  
**Next:** Phase 2 Step 3 - "Because You Watched" Feature
