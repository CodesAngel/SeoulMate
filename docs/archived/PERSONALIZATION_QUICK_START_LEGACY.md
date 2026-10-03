# 🎯 Personalization Quick Start Guide

## Getting Started with Personalized Recommendations

SeoulMate now learns your preferences and gives you personalized K-drama recommendations! Here's how to use it:

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start the Backend

```bash
cd d:\Projects\SeoulMate\backend
python app.py
```

Wait for: `✓ API ready at http://127.0.0.1:8001`

### Step 2: Start the Frontend

```bash
# New terminal window
cd d:\Projects\SeoulMate
streamlit run frontend/streamlit_app.py
```

Browser opens automatically to `http://localhost:8501`

### Step 3: Build Your Taste Profile!

**Option A: Rate Dramas (Fastest)**

1. Go to **"👤 My Profile"** tab
2. Expand **"📝 Rate a Drama"**
3. Enter drama titles and ratings:
   - "Hospital Playlist" = 9.5
   - "Crash Landing on You" = 9.0
   - "Itaewon Class" = 8.5
4. Click **"Submit Rating"** for each
5. Watch your profile build! 🎉

**Option B: Natural Interaction**

1. Search for dramas you like
2. Click **"👁️ View"** on interesting ones
3. Click **"➕ Watchlist"** to save favorites
4. System learns automatically!

---

## 🎯 Using Personalization

### See Your Taste Profile

1. Go to **"👤 My Profile"** tab
2. View:
   - **🎭 Your Persona** (e.g., "Medical Fan")
   - **📊 Statistics** (watched, clicks, etc.)
   - **Top Genres** with preference scores
   - **Favorite Actors & Directors**

### Get Personalized Results

1. Go to **"🔍 Smart Search"** tab
2. Search for anything (e.g., "drama")
3. See the magic:
   - **"✨ Personalized Results!"** banner
   - **"+X% Match"** badges on boosted dramas
   - **Top recommendations** tailored to YOU

### Compare: Before vs After

**Without Profile:**
Search "drama" → Generic top-rated dramas

**With Profile (Medical Fan):**
Search "drama" → Medical dramas boosted to top!

- Hospital Playlist (+34% boost 🎯)
- Doctor John (+34% boost 🎯)
- Romantic Doctor Kim (+34% boost 🎯)

---

## 📊 How It Works

### Preference Learning

- **Watched (rated):** Strong signal (100%)
- **Watchlist add:** Medium signal (60%)
- **View/Click:** Weak signal (30%)

### Boosting Algorithm

- **Genre match:** Up to +50% boost
- **Actor match:** Up to +30% boost
- **Director match:** Up to +20% boost
- **Theme match:** Up to +40% boost

**Example:**

```
Base score: 0.75
Genre boost: +0.25 (50% - you love Medical dramas)
Actor boost: +0.09 (30% - you love this actor)
─────────────────────────────────────
Final score: 1.09 (×1.45 multiplier!)
```

---

## 🎨 Features

### 1. Smart Boosting

- Dramas matching your taste get higher scores
- Multiple factors combined (genre + actor + director)
- Transparent: You can see the boost percentage

### 2. Dynamic Learning

- Profile improves with every interaction
- Recent preferences weighted higher
- Old preferences gradually fade

### 3. Persona Detection

- System determines your "type"
- Examples:
  - "Medical Fan" (loves medical dramas)
  - "Thriller Enthusiast" (prefers suspense)
  - "Romance & Comedy Lover" (multi-genre)

### 4. Adaptive Search

- Adjusts search algorithm to your style
- Focused users: More exploitation (stick to preferences)
- Diverse users: More exploration (try new things)

---

## 🔧 Advanced Features

### API Endpoints

#### Get Your Profile

```bash
curl http://127.0.0.1:8001/profile/user_123
```

#### Rate a Drama

```bash
curl -X POST "http://127.0.0.1:8001/profile/user_123/rate?drama_title=Hospital%20Playlist&rating=9.5"
```

#### Reset Profile

```bash
curl -X DELETE http://127.0.0.1:8001/profile/user_123
```

### Python Integration

```python
import requests

# Rate dramas
requests.post(
    "http://127.0.0.1:8001/profile/user_123/rate",
    params={"drama_title": "Hospital Playlist", "rating": 9.5}
)

# Get personalized recommendations
response = requests.get(
    "http://127.0.0.1:8001/recommend",
    params={
        "title": "medical drama",
        "user_id": "user_123",
        "top_n": 10
    }
)

results = response.json()
print(f"Personalized: {results['personalization']['applied']}")

for drama in results['recommendations']:
    boost = drama.get('boost_multiplier', 1.0)
    print(f"{drama['Title']}: {boost:.2f}x boost")
```

---

## 💡 Pro Tips

### Build a Strong Profile Fast

1. Rate **10-15 dramas** you've watched
2. Mix high ratings (8-10) and medium (6-7)
3. Include different genres to show range
4. Be honest! System learns from your TRUE preferences

### Get Best Recommendations

1. **Use broad searches** (e.g., "drama" instead of specific titles)
   - Lets personalization shine
2. **Try genre mixing** (e.g., "romantic thriller")
   - System balances your preferences
3. **Check "My Profile"** regularly
   - See how your taste evolves

### Reset When Needed

1. Go to **"👤 My Profile"**
2. Scroll to bottom
3. Click **"🔄 Reset My Profile"**
4. Start fresh!

---

## 🎬 Example Scenarios

### Scenario 1: Medical Drama Fan

```
1. Rate: Hospital Playlist (9.5), Good Doctor (9.0)
2. Search: "drama"
3. Result: Medical dramas dominate top 5
4. Persona: "Medical Fan" 🏥
```

### Scenario 2: Thriller Enthusiast

```
1. Rate: Signal (9.0), Stranger (8.5), Mouse (9.5)
2. Search: "korea"
3. Result: Thrillers and crime dramas boosted
4. Persona: "Thriller Enthusiast" 🕵️
```

### Scenario 3: Romance + Comedy Lover

```
1. Rate: Crash Landing on You (10), Business Proposal (8.5)
2. Search: "office"
3. Result: Romantic comedies with office settings
4. Persona: "Romance & Comedy Lover" 💕
```

---

## 📈 Tracking Your Progress

### Statistics to Watch

- **Total Interactions:** How active you are
- **Watched Count:** Dramas you've rated
- **Watchlist Adds:** Saved for later
- **Clicks:** Dramas you viewed

### Preference Scores

- **0.0 - 0.3:** Weak preference
- **0.3 - 0.6:** Medium preference
- **0.6 - 0.8:** Strong preference
- **0.8 - 1.0:** Very strong preference

---

## 🐛 Troubleshooting

### "Profile feature unavailable"

- **Check:** Backend is running (`python backend/app.py`)
- **Check:** API is accessible at `http://127.0.0.1:8001`

### "Drama not found" when rating

- **Tip:** Use exact drama title from search results
- **Tip:** Check spelling and capitalization

### Profile not updating

- **Reload:** Click "🔄" in browser
- **Check:** Look for success message after rating
- **Wait:** Profile updates in real-time

### Not seeing personalization

- **Build profile first:** Need at least 3-5 ratings
- **Check banner:** Look for "✨ Personalized Results!" message
- **Try broad search:** Use "drama" instead of specific title

---

## 🎉 Success Indicators

You know it's working when you see:

- ✅ **"✨ Personalized Results!"** banner in search
- ✅ **"+X% Match"** badges on recommended dramas
- ✅ **Your Persona** label in profile (e.g., "Medical Fan")
- ✅ **Top genres** showing in profile with high scores
- ✅ **Different results** compared to non-personalized search

---

## 📞 Support

**Need Help?**

- Check the **"ℹ️ How It Works"** tab in the app
- Read `docs/PHASE2_STEP2_COMPLETE.md` for technical details
- Run tests: `python tests/test_phase2_complete.py`

**Found a Bug?**

- Reset your profile: **"👤 My Profile" → "🔄 Reset My Profile"**
- Check backend logs for errors
- Restart both backend and frontend

---

**Happy Drama Hunting! 🎬✨**
