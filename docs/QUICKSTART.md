# 🚀 Quick Start Guide - SeoulMate K-Drama Recommendation System

## ✅ Step-by-Step Setup

### 1️⃣ Build the FAISS Index (Already Running)

The system is currently building the search index with **1,922 dramas**.

**Current Status**: Building embeddings (~5-10 minutes)

```bash
cd d:\Projects\SeoulMate
python training\steps\legacy_build_index.py
```

**What this does:**

- Loads `data/final/kdrama_dataset.csv`
- Generates semantic embeddings for all 1,922 dramas
- Creates FAISS index for fast similarity search
- Saves metadata for recommendations

**Output files:**

- `training/faiss_index/index.faiss` - Vector index
- `training/faiss_index/meta.pkl` - Drama metadata

---

### 2️⃣ Start the Backend API

Once the index building completes, start the FastAPI server:

```bash
cd d:\Projects\SeoulMate\backend
python app.py
```

**Expected output:**

```
Stage 1: Loading models and FAISS index...
Loaded 1922 dramas successfully.
Stage 2: Loading cross-encoder reranker...
Cross-encoder reranker loaded successfully.
INFO:     Uvicorn running on http://127.0.0.1:8001
```

**API Endpoints:**

- Health Check: http://127.0.0.1:8001/
- Recommendations: http://127.0.0.1:8001/recommend
- API Docs: http://127.0.0.1:8001/docs

---

### 3️⃣ Test the Recommendations

#### Option A: Using Web Browser

Open your browser and try these URLs:

```
http://127.0.0.1:8001/recommend?title=Goblin&top_n=5
http://127.0.0.1:8001/recommend?title=Crash%20Landing%20on%20You&top_n=5
http://127.0.0.1:8001/recommend?title=romantic%20comedy&top_n=10
```

#### Option B: Using Test Script

```bash
cd d:\Projects\SeoulMate
python test_api.py
```

This will test multiple queries automatically.

#### Option C: Using PowerShell

```powershell
# Test API health
Invoke-RestMethod -Uri "http://127.0.0.1:8001/"

# Get recommendations
$response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/recommend?title=Goblin&top_n=5"
$response.recommendations | Format-Table Title, Genre, rating_value
```

#### Option D: Using Python

```python
import requests

response = requests.get(
    "http://127.0.0.1:8001/recommend",
    params={"title": "Goblin", "top_n": 5}
)

data = response.json()
for drama in data["recommendations"]:
    print(f"{drama['Title']} - {drama['Genre']}")
```

---

## 🎯 How the Recommendation Works

### Query Types Supported:

1. **Exact Title Match**

   - Input: `"Goblin"`
   - Returns: Similar dramas to Goblin

2. **Fuzzy Title Match** (typo-tolerant)

   - Input: `"Gobblin"` or `"Goblen"`
   - Automatically corrects to "Goblin"

3. **Genre/Mood Search**

   - Input: `"romantic comedy"`
   - Returns: Rom-com dramas

4. **Description-based**

   - Input: `"time travel fantasy romance"`
   - Returns: Dramas matching that description

5. **Cast/Director Search**
   - Input: `"Gong Yoo"`
   - Returns: Dramas with that actor

---

## 📊 Understanding the Results

Example response structure:

```json
{
  "query": {
    "Title": "Goblin"
  },
  "recommendations": [
    {
      "Title": "Guardian: The Lonely and Great God",
      "Genre": "Romance, Fantasy, Drama",
      "Description": "...",
      "Cast": "Gong Yoo, Kim Go Eun, Lee Dong Wook",
      "Director": "Lee Eung Bok",
      "rating_value": "8.7",
      "episodes": "16",
      "aired": "Dec 2, 2016 - Jan 21, 2017",
      "keywords": "Fantasy, Romance, Grim Reaper, Immortality"
    }
  ]
}
```

---

## 🔧 Troubleshooting

### Issue: "Connection refused" when testing API

**Solution:** Make sure the backend server is running:

```bash
cd d:\Projects\SeoulMate\backend
python app.py
```

### Issue: "Index file not found"

**Solution:** Build the index first:

```bash
cd d:\Projects\SeoulMate
python training\steps\build_index.py
```

### Issue: Slow first request

**Expected:** First request loads the model into memory (~5 seconds)
**Subsequent requests:** Fast (<1 second)

### Issue: Import errors (faiss, sentence_transformers, etc.)

**Solution:** Install dependencies:

```bash
cd d:\Projects\SeoulMate\model_traning
pip install -r requirements.txt
```

---

## 📈 Performance Metrics

### Dataset Stats

- **Total Dramas**: 1,922
- **Average Description Length**: ~200 words
- **Genres Covered**: 20+ unique genres
- **Date Range**: Various years

### Search Performance

- **Index Build Time**: ~5-10 minutes (one-time)
- **First Query**: ~5 seconds (model loading)
- **Subsequent Queries**: <1 second
- **Concurrent Requests**: Supported

### Recommendation Quality

- **Semantic Search**: 70% weight
- **Keyword Matching**: 30% weight
- **Reranking**: Cross-encoder for top results
- **Fuzzy Matching**: 70% similarity threshold

---

## 🎨 Example Use Cases

### 1. "I just finished Goblin, what's similar?"

```
Query: "Goblin"
→ Returns: Other fantasy romance dramas with similar vibes
```

### 2. "I want a historical romance"

```
Query: "historical romance"
→ Returns: Period dramas with romantic elements
```

### 3. "Something with Gong Yoo"

```
Query: "Gong Yoo"
→ Returns: Dramas featuring Gong Yoo
```

### 4. "Light-hearted comedy for weekends"

```
Query: "light comedy"
→ Returns: Feel-good comedy dramas
```

---

## 🚀 Next Steps

After confirming the system works:

1. **Build a Frontend**

   - React/Vue web app
   - Drama cards with posters
   - Filter options (genre, year, rating)
   - User watchlist

2. **Add More Features**

   - User ratings integration
   - Collaborative filtering
   - "Because you watched X" recommendations
   - Trending dramas section

3. **Improve Dataset**

   - Add more dramas (currently 1,922)
   - Include OST information
   - Add streaming platform availability
   - Include poster images

4. **Deploy to Production**
   - Docker containerization
   - Cloud hosting (AWS/GCP/Azure)
   - CDN for static assets
   - Database for user data

---

## 📞 Support

If you encounter any issues:

1. Check the terminal output for error messages
2. Verify all files are in the correct locations
3. Ensure Python dependencies are installed
4. Check if ports 8001 is available

---

**Happy drama watching! 🎬✨**
