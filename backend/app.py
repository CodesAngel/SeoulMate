from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import pickle
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from rapidfuzz import process, fuzz
from functools import lru_cache
from rank_bm25 import BM25Plus
import uuid
import time
import json
import re
import random
from pathlib import Path
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Import Phase 1 enhancements
from query_analyzer import QueryAnalyzer, QueryIntent, get_search_strategy
from analytics import get_tracker

# Import Phase 2 enhancements
from user_profile import get_profile_manager
from personalization import get_personalization_engine

# ======================================================
# CONFIGURATION
# ======================================================
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
# Override to point the backend at an alternate training tree, e.g.
# SEOULMATE_TRAINING_DIR="training-new/output" to test the training-new artifacts
# without touching the production default.
TRAINING_DIR = PROJECT_DIR / os.environ.get("SEOULMATE_TRAINING_DIR", "training")
RANKING_DIR = BASE_DIR / "ranking"

MODEL_DIR = str(TRAINING_DIR / "models")
INDEX_DIR = str(TRAINING_DIR / "faiss_index")
GENERATED_INDEX_DIR = str(RANKING_DIR / "indexes")
RANKING_CONFIG_DIR = str(RANKING_DIR / "config")

# ======================================================
# FASTAPI SETUP
# ======================================================
app = FastAPI(
    title="SeoulMate Kdrama Recommendation API",
    version="4.0 (Phase 1)",
    description="Intelligent K-Drama recommendations with AI-powered query understanding and user analytics",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# STAGE 1 — LOAD MODELS & INDEXES
# ======================================================
print("Stage 1: Loading models and FAISS index...")

# Try to load a fine-tuned bi-encoder first, fallback to pretrained. Model folder
# names vary across training trees (e.g. sbert-finetuned-full, e5-kdrama-finetuned),
# so any subfolder that isn't a cross-encoder/reranker folder is treated as the
# bi-encoder candidate.
model_subdirs = (
    [d for d in os.listdir(MODEL_DIR) if os.path.isdir(os.path.join(MODEL_DIR, d))]
    if os.path.exists(MODEL_DIR)
    else []
)
finetuned_models = [d for d in model_subdirs if "cross" not in d.lower()]
cross_encoder_dirs = [d for d in model_subdirs if "cross" in d.lower()]

# Using fine-tuned cross-encoder trained on K-drama data, if present.
CROSS_ENCODER_MODEL = (
    os.path.join(MODEL_DIR, cross_encoder_dirs[0])
    if cross_encoder_dirs
    else str(TRAINING_DIR / "models" / "cross-enc-excellent")
)

if finetuned_models:
    model_path = os.path.join(MODEL_DIR, finetuned_models[0])
    print(f"Loading fine-tuned bi-encoder from: {model_path}")
    model = SentenceTransformer(model_path)
else:
    model_path = MODEL_NAME
    print(f"No fine-tuned model found, using pretrained: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_DIR)

# E5 models expect "query: "/"passage: " prefixes on input text for correct
# asymmetric retrieval; MPNet and other non-E5 models don't use this convention.
IS_E5_MODEL = "e5" in model_path.lower()
if IS_E5_MODEL:
    print("Detected E5-family model — applying query:/passage: prefixes to encoded text.")

index = faiss.read_index(os.path.join(INDEX_DIR, "index.faiss"))

with open(os.path.join(INDEX_DIR, "meta.pkl"), "rb") as f:
    metadata = pickle.load(f)

titles = [m["Title"] for m in metadata]
corpus = [
    f"{m.get('Title', '')} {m.get('Genre', '')} {m.get('Description', '')} {m.get('Cast', '')}"
    for m in metadata
]
# Using BM25Plus for better performance (improved IDF handling)
bm25 = BM25Plus([doc.split() for doc in corpus])

print(f"Loaded {len(metadata)} dramas successfully.")

# ======================================================
# STAGE 1.5 — INITIALIZE PHASE 1 ENHANCEMENTS
# ======================================================
print("Stage 1.5: Initializing Phase 1 enhancements...")
query_analyzer = QueryAnalyzer()
analytics_tracker = get_tracker()
print("✓ Query analyzer and analytics tracker initialized.")

# ======================================================
# STAGE 2 — LOAD OPTIONAL RERANKER
# ======================================================
try:
    print("Stage 2: Loading cross-encoder reranker...")
    reranker = CrossEncoder(CROSS_ENCODER_MODEL)
    use_reranker = True
    print("Cross-encoder reranker loaded successfully.")
except Exception as e:
    reranker = None
    use_reranker = False
    print(f"Warning: Could not load reranker ({e}). Continuing without it.")


# ======================================================
# STAGE 3 — HELPER FUNCTIONS
# ======================================================
def fuzzy_match_title(user_input: str, threshold=70):
    """Handle typos and near matches using fuzzy logic."""
    match, score, _ = process.extractOne(user_input, titles, scorer=fuzz.WRatio)
    if score >= threshold:
        return match, score
    return None, score


QUERY_INTENT_PRIORS = {}
GENERIC_QUALITY_QUERY_PATTERNS = []
QUALITY_BROWSE_PRIOR_TITLES = []
SPECIAL_TITLE_TERMS = []
THEME_GENRE_COMBO_PRIORS = {}
QUERY_COMBO_PRIORS = {}
RECENT_DRAMA_PRIOR_TITLES = []
BROAD_TITLE_NOISE = set()


def is_generic_quality_query(query: str) -> bool:
    query_text = query.lower().strip()
    return any(re.search(pattern, query_text) for pattern in GENERIC_QUALITY_QUERY_PATTERNS)


def drama_quality_score(drama):
    try:
        rating = float(drama.get("rating_value", drama.get("score", 0)) or 0)
    except Exception:
        rating = 0.0
    try:
        watchers = float(str(drama.get("watchers", 0)).replace(",", "") or 0)
    except Exception:
        watchers = 0.0
    try:
        popularity = float(str(drama.get("popularity", 0)).replace(",", "") or 0)
    except Exception:
        popularity = 0.0
    watcher_bonus = min(watchers / 100000.0, 1.0)
    popularity_bonus = min(popularity / 100.0, 0.5) if popularity else 0.0
    return rating + watcher_bonus + popularity_bonus


def is_special_or_meta_title(drama):
    searchable_text = " ".join(
        str(drama.get(field, "")) for field in ["Title", "Genre", "Description"]
    ).lower()
    return any(term in searchable_text for term in SPECIAL_TITLE_TERMS)


def resolve_typo_title(user_input: str, candidates, threshold=74):
    candidate_titles = [m["Title"] for m in candidates]
    if not candidate_titles:
        return None, None
    match, score, _ = process.extractOne(
        user_input, candidate_titles, scorer=fuzz.token_set_ratio
    )
    if match and score >= threshold:
        drama = next((m for m in candidates if m["Title"] == match), None)
        return drama, f"typo:{score:.1f}"
    return None, None


@lru_cache(maxsize=128)
def cached_encode(text: str, mode: str = "query"):
    """Cached embedding generation for speed.

    mode is "query" for genuine user search text, or "passage" for drama-metadata
    text being embedded for document-to-document comparison (e.g. title-similarity
    mode, similar_to). Only affects encoding when the loaded model is E5-family,
    which requires this prefix convention for correct asymmetric retrieval.
    """
    encode_text = f"{mode}: {text}" if IS_E5_MODEL else text
    emb = model.encode([encode_text], convert_to_numpy=True)
    faiss.normalize_L2(emb)
    return emb


# Cache for search results (query + filters -> results)
_result_cache = {}
_cache_max_size = 200
_cache_ttl = 300  # 5 minutes
_cache_version = "search-ranking-v2"


def load_generated_index(filename: str, default=None):
    path = os.path.join(GENERATED_INDEX_DIR, filename)
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        print(f"Loaded generated index: {filename} ({len(data)} keys)")
        return data
    except FileNotFoundError:
        print(f"Generated index missing: {filename}; using fallback data.")
        return default
    except Exception as exc:
        print(f"Could not load generated index {filename}: {exc}")
        return default


def merge_title_indexes(generated, curated):
    merged = {key: value[:] for key, value in generated.items()}
    for key, titles in curated.items():
        current = merged.setdefault(key, [])
        for title in titles:
            if title not in current:
                current.insert(0, title)
    return merged


def combo_prior_keys(priors):
    return {
        tuple(part.strip() for part in key.split("|")): titles
        for key, titles in priors.items()
    }


def load_ranking_config(filename: str):
    path = os.path.join(RANKING_CONFIG_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read().strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            data = {}
            cursor = 0
            while cursor < len(text):
                while cursor < len(text) and text[cursor].isspace():
                    cursor += 1
                if cursor >= len(text):
                    break
                if text[cursor] != "{":
                    cursor += 1
                    continue
                parsed, cursor = decoder.raw_decode(text, cursor)
                if isinstance(parsed, dict):
                    merge_prior_maps(data, parsed)
        print(f"Loaded ranking config: {filename}")
        return data
    except FileNotFoundError:
        print(f"Ranking config missing: {filename}; using empty priors.")
        return {}
    except Exception as exc:
        print(f"Could not load ranking config {filename}: {exc}")
        return {}


def merge_prior_maps(target, incoming):
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_prior_maps(target[key], value)
        elif isinstance(value, list) and isinstance(target.get(key), list):
            for item in value:
                if item not in target[key]:
                    target[key].append(item)
        else:
            target[key] = value
    return target


def load_prior_weights(defaults):
    """Load ranking weights, with optional JSON env override for experiments."""
    weights = defaults.copy()
    override = os.environ.get("SEOULMATE_PRIOR_WEIGHTS")
    if not override:
        return weights
    try:
        weights.update(json.loads(override))
        print(f"Loaded ranking weight override: {weights}")
    except Exception as exc:
        print(f"Could not parse SEOULMATE_PRIOR_WEIGHTS: {exc}")
    return weights


GENERATED_TITLE_ALIASES = load_generated_index("title_aliases.json")
QUERY_INTENT_PRIORS = load_ranking_config("query_intent_priors.json")
GENERIC_QUALITY_QUERY_PATTERNS = QUERY_INTENT_PRIORS.get(
    "generic_quality_query_patterns", []
)
QUALITY_BROWSE_PRIOR_TITLES = QUERY_INTENT_PRIORS.get(
    "quality_browse_prior_titles", []
)
SPECIAL_TITLE_TERMS = QUERY_INTENT_PRIORS.get("special_title_terms", [])
THEME_GENRE_COMBO_PRIORS = combo_prior_keys(
    QUERY_INTENT_PRIORS.get("theme_genre_combo_priors", {})
)
QUERY_COMBO_PRIORS = QUERY_INTENT_PRIORS.get("query_combo_priors", {})
RECENT_DRAMA_PRIOR_TITLES = QUERY_INTENT_PRIORS.get(
    "recent_drama_prior_titles", []
)
BROAD_TITLE_NOISE = {
    title.lower() for title in QUERY_INTENT_PRIORS.get("broad_title_noise", [])
}
GENERATED_ACTOR_INDEX = load_generated_index("actor_index.json")
GENERATED_CALIBRATED_ACTOR_INDEX = load_generated_index("calibrated_actor_index.json")
GENERATED_GENRE_INDEX = load_generated_index("genre_index.json")
GENERATED_CALIBRATED_GENRE_INDEX = load_generated_index("calibrated_genre_index.json")
GENERATED_CALIBRATED_GENRE_COMBO_INDEX = load_generated_index(
    "calibrated_genre_combo_index.json"
)
GENERATED_THEME_INDEX = load_generated_index("theme_index.json")
GENERATED_CALIBRATED_THEME_INDEX = load_generated_index("calibrated_theme_index.json")
GENERATED_KEYWORD_INDEX = load_generated_index("keyword_index.json")
GENERATED_CALIBRATED_KEYWORD_INDEX = load_generated_index("calibrated_keyword_index.json")

TITLE_ALIASES = GENERATED_TITLE_ALIASES | QUERY_INTENT_PRIORS.get(
    "manual_title_aliases", {}
)

CURATED_PRIORS = load_ranking_config("curated_priors.json")
GENRE_PRIOR_SOURCE = os.environ.get(
    "SEOULMATE_GENRE_PRIOR_SOURCE",
    CURATED_PRIORS.get("genre_prior_source", "curated"),
)
ACTOR_PRIOR_SOURCE = os.environ.get(
    "SEOULMATE_ACTOR_PRIOR_SOURCE",
    CURATED_PRIORS.get("actor_prior_source", "curated"),
)
THEME_PRIOR_SOURCE = os.environ.get(
    "SEOULMATE_THEME_PRIOR_SOURCE",
    CURATED_PRIORS.get("theme_prior_source", "curated"),
)
PRIOR_WEIGHTS = load_prior_weights(
    CURATED_PRIORS.get(
        "weights",
        {
            "genre_combo": 2.55,
            "genre": 2.2,
            "theme_combo": 3.1,
            "theme": 2.4,
            "actor": 2.35,
            "keyword": 2.0,
            "generated_actor": 0.0,
            "generated_genre": 0.0,
            "generated_theme": 0.0,
            "generated_cap": 1.0,
            "hybrid_genre_combo": 0.95,
            "hybrid_genre": 0.75,
            "hybrid_actor": 1.0,
            "hybrid_theme_combo": 1.15,
            "hybrid_theme": 0.3,
            "fallback_genre_combo": 0.85,
            "fallback_genre": 0.65,
            "fallback_theme": 0.8,
        },
    )
)
THEME_PRIOR_TITLES = CURATED_PRIORS.get("theme_priors", {})
THEME_COMBINATION_PRIOR_TITLES = combo_prior_keys(
    CURATED_PRIORS.get("theme_combo_priors", {})
)
GENRE_PRIOR_TITLES = CURATED_PRIORS.get("genre_priors", {})
GENRE_COMBINATION_PRIOR_TITLES = combo_prior_keys(
    CURATED_PRIORS.get("genre_combo_priors", {})
)
ACTOR_PRIOR_TITLES = CURATED_PRIORS.get("actor_priors", {})
EXTRA_PRIOR_CONFIGS = {
    "mood": load_ranking_config("mood_priors.json"),
    "relationship": load_ranking_config("relationships_priors.json"),
    "setting": load_ranking_config("setting_priors.json"),
    "occupation": load_ranking_config("ocupation_priors.json"),
    "character": load_ranking_config("character_archtype_priors.json"),
    "ending": load_ranking_config("ending_priors.json"),
    "episode_count": load_ranking_config("episode_count_priors.json"),
    "release_year": load_ranking_config("release_year_prior.json"),
    "metadata": load_ranking_config("metadata_priors.json"),
}
SPECIFIC_EXTRA_PRIOR_CATEGORIES = {
    "occupation",
    "setting",
    "relationship",
    "character",
    "ending",
    "episode_count",
}
DEFAULT_SIMILAR_TITLE_PRIORS = {
    "Crash Landing on You": [
        "King2Hearts",
        "Descendants of the Sun",
        "My Love from the Star",
        "The Legend of the Blue Sea",
        "Mr. Sunshine",
        "My Military Valentine",
    ],
    "Guardian: The Lonely and Great God": [
        "Hotel del Luna",
        "My Love from the Star",
        "The Master's Sun",
        "My Demon",
        "Kiss Goblin",
        "The Atypical Family",
    ],
    "Business Proposal": [
        "What's Wrong with Secretary Kim",
        "King the Land",
        "Her Private Life",
        "Touch Your Heart",
        "Fated to Love You",
        "The Greatest Love",
    ],
}
SIMILAR_TITLE_PRIORS = (
    DEFAULT_SIMILAR_TITLE_PRIORS
    | CURATED_PRIORS.get("similar_title_priors", {})
    | QUERY_INTENT_PRIORS.get("similar_title_priors", {})
)
SIMILAR_TITLE_PRIORS_NORMALIZED = {
    key.strip().lower(): value for key, value in SIMILAR_TITLE_PRIORS.items()
}

GENERATED_QUERY_PROFILES = [
    {
        "name": "medical_drama",
        "query_terms": ["medical", "doctor", "hospital"],
        "required_genres": ["medical"],
        "focus_terms": ["hospital", "doctor", "surgeon", "resident", "medical"],
        "penalty_terms": ["action", "fantasy"],
        "boost": 2.05,
        "limit": 8,
    },
    {
        "name": "thriller",
        "query_terms": ["thriller"],
        "required_genres": ["thriller"],
        "focus_terms": ["thriller", "mystery", "suspense", "survival", "game"],
        "penalty_terms": ["romance", "comedy", "youth"],
        "boost": 1.95,
        "limit": 8,
    },
    {
        "name": "zombie_drama",
        "query_terms": ["zombie"],
        "required_genres": ["thriller"],
        "focus_terms": ["zombie", "infected", "infection", "survival", "horror"],
        "penalty_terms": ["revenge", "romance", "comedy"],
        "boost": 2.15,
        "limit": 8,
    },
    {
        "name": "historical",
        "query_terms": ["historical", "sageuk", "royal"],
        "required_genres": ["historical"],
        "focus_terms": ["historical", "king", "queen", "royal", "palace", "joseon"],
        "penalty_terms": ["fantasy", "cooking", "time travel"],
        "boost": 2.0,
        "limit": 8,
    },
    {
        "name": "school_drama",
        "query_terms": ["school", "student", "youth"],
        "required_genres": ["youth"],
        "focus_terms": ["school", "student", "high school", "class", "campus"],
        "penalty_terms": ["action", "gangster", "thriller"],
        "boost": 2.0,
        "limit": 8,
    },
    {
        "name": "romantic_comedy",
        "query_terms": ["romantic comedy", "romcom"],
        "required_genres": ["romance", "comedy"],
        "focus_terms": ["romantic comedy", "romance", "comedy", "office", "secretary"],
        "penalty_terms": ["fantasy", "historical", "melodrama"],
        "boost": 2.0,
        "limit": 8,
    },
    {
        "name": "office_romance",
        "query_terms": ["office romance", "workplace romance"],
        "required_genres": ["romance"],
        "focus_terms": ["office", "workplace", "company", "secretary", "business"],
        "penalty_terms": ["fantasy", "historical", "sports"],
        "boost": 1.95,
        "limit": 8,
    },
    {
        "name": "legal_drama",
        "query_terms": ["legal", "law", "lawyer", "courtroom"],
        "required_genres": ["law"],
        "focus_terms": ["law", "lawyer", "attorney", "court", "prosecutor", "legal"],
        "penalty_terms": ["doctor", "medical", "fantasy"],
        "boost": 1.95,
        "limit": 8,
    },
]

KEYWORD_FILTER_EXPANSIONS = {
    "healing": ["healing", "comfort", "slice of life"],
    "time travel": ["time travel", "time slip", "time loop", "time manipulation"],
    "strong female lead": ["strong female lead", "badass female lead", "smart female lead"],
    "smart female lead": ["smart female lead", "strong female lead"],
    "smart male lead": ["smart male lead", "genius male lead"],
    "slow burn romance": ["slow burn romance", "slow romance", "slow burn"],
    "contract marriage": [
        "contract marriage",
        "contract relationship",
        "marriage of convenience",
        "fake relationship",
    ],
    "marriage of convenience": [
        "marriage of convenience",
        "contract relationship",
        "contract marriage",
    ],
    "contract relationship": [
        "contract relationship",
        "contract marriage",
        "marriage of convenience",
        "fake relationship",
    ],
    "school bullying": ["school bullying", "bullying", "school violence"],
    "revenge": ["revenge", "vengeance", "payback"],
    "doctor": ["doctor", "doctor male lead", "doctor female lead", "hospital setting"],
    "hospital": ["hospital", "hospital setting", "doctor"],
    "lawyer": ["lawyer", "attorney", "courtroom setting"],
}


def keyword_filter_terms(keyword_query: str) -> list[str]:
    query = normalized_text = re.sub(r"\s+", " ", keyword_query.lower().strip())
    terms = [normalized_text]
    for key, expansions in KEYWORD_FILTER_EXPANSIONS.items():
        if key in query:
            terms.extend(expansions)
    return list(dict.fromkeys(term for term in terms if term))


def keyword_generated_fallback_titles(keyword_query: str) -> set[str]:
    fallback_titles = set()
    for term in keyword_filter_terms(keyword_query):
        for title in GENERATED_CALIBRATED_KEYWORD_INDEX.get(term, [])[:40]:
            fallback_titles.add(title.lower())
    return fallback_titles


def keyword_prior_titles(keyword_query: str) -> list[str]:
    title_scores = {}
    for key_order, term in enumerate(keyword_filter_terms(keyword_query)):
        for rank, title in enumerate(
            GENERATED_CALIBRATED_KEYWORD_INDEX.get(term, [])[:40], start=1
        ):
            title_key = title.lower()
            if title_key not in title_scores:
                title_scores[title_key] = {
                    "title": title,
                    "best_rank": rank,
                    "rank_sum": 0,
                    "key_order": key_order,
                    "overlap": 0,
                }
            score = title_scores[title_key]
            score["best_rank"] = min(score["best_rank"], rank)
            score["rank_sum"] += rank
            score["key_order"] = min(score["key_order"], key_order)
            score["overlap"] += 1

    return [
        item["title"]
        for item in sorted(
            title_scores.values(),
            key=lambda item: (
                -item["overlap"],
                item["best_rank"],
                item["rank_sum"],
                item["key_order"],
                item["title"],
            ),
        )
    ]


def flatten_prior_config(config):
    flattened = {}
    for key, value in config.items():
        if isinstance(value, dict):
            merge_prior_maps(flattened, flatten_prior_config(value))
        elif isinstance(value, list):
            flattened[key] = value
    return flattened


def query_matches_prior_term(query_text, term):
    query_norm = re.sub(r"[^a-z0-9]+", " ", query_text.lower()).strip()
    term_norm = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
    if not term_norm:
        return False
    if term_norm in query_norm:
        return True
    term_parts = term_norm.split()
    return len(term_parts) > 1 and all(part in query_norm for part in term_parts)


def extra_prior_matches(query_text):
    matches = []
    for category, config in EXTRA_PRIOR_CONFIGS.items():
        for term, prior_titles in flatten_prior_config(config).items():
            if query_matches_prior_term(query_text, term):
                matches.append((category, term, prior_titles))
    return matches

def get_cache_key(title, top_n, genre, filters_dict):
    """Generate cache key from query parameters"""
    filter_str = json.dumps(filters_dict, sort_keys=True, default=str)
    return f"{_cache_version}_{title}_{top_n}_{filter_str}"


def get_cached_result(cache_key):
    """Get result from cache if exists and not expired"""
    if cache_key in _result_cache:
        result, timestamp = _result_cache[cache_key]
        if time.time() - timestamp < _cache_ttl:
            return result
        else:
            del _result_cache[cache_key]
    return None


def cache_result(cache_key, result):
    """Cache result with timestamp"""
    # Simple LRU: remove oldest if cache is full
    if len(_result_cache) >= _cache_max_size:
        oldest_key = min(_result_cache.keys(), key=lambda k: _result_cache[k][1])
        del _result_cache[oldest_key]
    _result_cache[cache_key] = (result, time.time())


def add_prior_title_boosts(
    combined_scores, filtered_metadata, prior_titles, boost, decay=0.03
):
    """Add or increase scores for curated high-signal matches."""
    title_lookup = {m.get("Title", "").lower(): m for m in filtered_metadata}
    for rank, prior_title in enumerate(prior_titles):
        drama = title_lookup.get(prior_title.lower())
        if not drama:
            continue
        title_key = drama["Title"]
        current = combined_scores.get(title_key, 0.0)
        ranked_boost = boost - (rank * decay)
        combined_scores[title_key] = max(current, ranked_boost)


def generated_profile_matches(profile, query, detected_genres):
    query_lower = query.lower()
    detected_genre_set = {genre.lower() for genre in detected_genres}
    if not any(term in query_lower for term in profile["query_terms"]):
        return False
    return set(profile["required_genres"]).issubset(detected_genre_set)


def generated_profile_title_score(drama, profile):
    searchable_text = " ".join(
        str(drama.get(field, ""))
        for field in ["Title", "Genre", "Description", "keywords"]
    ).lower()
    genre_text = str(drama.get("Genre", "")).lower()

    focus_score = sum(term in searchable_text for term in profile["focus_terms"])
    penalty_score = sum(term in searchable_text for term in profile["penalty_terms"])
    required_score = sum(
        required in genre_text for required in profile["required_genres"]
    )
    try:
        rating = float(drama.get("rating_value", 0))
    except (TypeError, ValueError):
        rating = 0.0
    try:
        episodes = int(float(drama.get("episodes", 0)))
    except (TypeError, ValueError):
        episodes = 0
    episode_score = 1 if 8 <= episodes <= 24 else 0
    return (required_score, focus_score, episode_score, rating, -penalty_score)


def apply_generated_query_profile_boosts(
    combined_scores, filtered_metadata, query, detected_genres
):
    if not GENRE_PRIOR_SOURCE.startswith("calibrated_generated"):
        return
    if os.environ.get("SEOULMATE_ENABLE_QUERY_PROFILES", "0") != "1":
        return

    for profile in GENERATED_QUERY_PROFILES:
        if not generated_profile_matches(profile, query, detected_genres):
            continue
        candidates = sorted(
            filtered_metadata,
            key=lambda drama: generated_profile_title_score(drama, profile),
            reverse=True,
        )[: profile["limit"]]
        for rank, drama in enumerate(candidates):
            title_key = drama.get("Title")
            if not title_key:
                continue
            score = generated_profile_title_score(drama, profile)
            if score[0] == 0 or score[1] == 0:
                continue
            current = combined_scores.get(title_key, 0.0)
            ranked_boost = profile["boost"] - (rank * 0.035)
            combined_scores[title_key] = max(current, ranked_boost)
        print(f"Generated query profile applied: {profile['name']}")


def resolve_title_alias(user_input: str, candidates):
    """Resolve common public titles that differ from dataset titles."""
    canonical_title = TITLE_ALIASES.get(user_input.lower().strip())
    if not canonical_title:
        return None
    return next(
        (m for m in candidates if m.get("Title", "").lower() == canonical_title.lower()),
        None,
    )


def resolve_title(user_input: str, candidates, fuzzy_threshold=90):
    """Resolve exact, alias, or high-confidence fuzzy title against candidates."""
    normalized = user_input.lower().strip()
    exact_match = next(
        (m for m in candidates if m.get("Title", "").lower() == normalized), None
    )
    if exact_match:
        return exact_match, "exact"

    alias_match = resolve_title_alias(user_input, candidates)
    if alias_match:
        return alias_match, "alias"

    candidate_titles = [m.get("Title", "") for m in candidates if m.get("Title")]
    if candidate_titles:
        match, score, _ = process.extractOne(
            user_input, candidate_titles, scorer=fuzz.WRatio
        )
        if match and score >= fuzzy_threshold:
            return (
                next((m for m in candidates if m.get("Title") == match), None),
                f"fuzzy:{score:.1f}",
            )

    return None, None


def extract_similar_to_title(query: str, candidates):
    """Extract and resolve titles from user phrases such as 'like Goblin'."""
    patterns = [
        r"(?:something\s+)?(?:like|similar to|same as|shows like|dramas like|more like)\s+(.+)",
        r"(.+)\s+(?:similar|vibes|vibe)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if not match:
            continue
        raw_title = re.sub(r"\b(?:drama|kdrama|k-drama|show|series)\b", "", match.group(1), flags=re.IGNORECASE)
        raw_title = raw_title.strip(" .!?")
        if not raw_title:
            continue
        resolved, source = resolve_title(raw_title, candidates, fuzzy_threshold=82)
        if resolved:
            return resolved.get("Title"), source
    return None, None


def split_metadata_terms(value):
    return {
        part.strip().lower()
        for part in re.split(r"[,;/|]", str(value or ""))
        if part.strip()
    }


def drama_theme_set(drama):
    searchable_text = " ".join(
        str(drama.get(field, ""))
        for field in ["Title", "Genre", "Description", "keywords"]
    ).lower()
    theme_keywords = {
        "north korea": ["north korea", "north and south korea", "defector", "dmz"],
        "military romance": ["soldier", "army", "military", "army officer"],
        "supernatural romance": ["goblin", "ghost", "supernatural", "immortal", "dokkaebi"],
        "contract relationship": ["contract relationship", "fake identity", "fake dating", "contract marriage"],
        "office romance": ["boss-employee", "company", "office", "ceo", "workplace"],
        "school bullying": ["bullying", "school violence", "bullied"],
        "revenge": ["revenge", "vengeance", "payback"],
        "medical": ["doctor", "hospital", "medical", "surgeon"],
        "legal": ["lawyer", "attorney", "court", "prosecutor"],
        "time travel": ["time travel", "time slip", "time loop", "past life"],
        "healing slice of life": ["healing", "slice of life", "comfort", "everyday"],
    }
    return {
        theme
        for theme, keywords in theme_keywords.items()
        if any(keyword in searchable_text for keyword in keywords)
    }


def seed_similarity_score(seed_drama, candidate, faiss_rank=None):
    seed_genres = split_metadata_terms(seed_drama.get("Genre", ""))
    candidate_genres = split_metadata_terms(candidate.get("Genre", ""))
    genre_overlap = len(seed_genres & candidate_genres)
    genre_union = len(seed_genres | candidate_genres) or 1

    seed_keywords = split_metadata_terms(seed_drama.get("keywords", ""))
    candidate_keywords = split_metadata_terms(candidate.get("keywords", ""))
    keyword_overlap = len(seed_keywords & candidate_keywords)

    seed_themes = drama_theme_set(seed_drama)
    candidate_themes = drama_theme_set(candidate)
    theme_overlap = len(seed_themes & candidate_themes)

    try:
        rating = float(candidate.get("rating_value", 0) or 0)
    except Exception:
        rating = 0.0

    rank_bonus = 0.0
    if faiss_rank is not None:
        rank_bonus = max(0.0, 1.0 - (faiss_rank / 200))

    return (
        (genre_overlap / genre_union) * 3.0
        + theme_overlap * 2.4
        + min(keyword_overlap, 4) * 0.35
        + (rating / 10.0) * 0.8
        + rank_bonus
    )


def apply_similar_title_priors(seed_title, ranked_results, candidates):
    """Move curated similar-title priors to the front when they exist."""
    seed_key = seed_title.strip().lower()
    prior_titles = SIMILAR_TITLE_PRIORS_NORMALIZED.get(seed_key, [])
    if not prior_titles and seed_key in {
        "crash landing on you",
        "guardian: the lonely and great god",
        "business proposal",
    }:
        prior_titles = DEFAULT_SIMILAR_TITLE_PRIORS.get(seed_title.strip(), [])
        if not prior_titles:
            direct_defaults = {
                "crash landing on you": DEFAULT_SIMILAR_TITLE_PRIORS["Crash Landing on You"],
                "guardian: the lonely and great god": DEFAULT_SIMILAR_TITLE_PRIORS[
                    "Guardian: The Lonely and Great God"
                ],
                "business proposal": DEFAULT_SIMILAR_TITLE_PRIORS["Business Proposal"],
            }
            prior_titles = direct_defaults.get(seed_key, [])
    if not prior_titles:
        return ranked_results

    candidate_lookup = {
        item.get("Title", "").lower(): item for item in candidates if item.get("Title")
    }
    ranked_lookup = {
        item.get("Title", "").lower(): item for item in ranked_results if item.get("Title")
    }

    prioritized = []
    for prior_title in prior_titles:
        key = prior_title.lower()
        drama = ranked_lookup.get(key) or candidate_lookup.get(key)
        if drama and drama.get("Title", "").strip().lower() != seed_key:
            prioritized.append(drama)

    seen = {item.get("Title", "").lower() for item in prioritized}
    remainder = [
        item
        for item in ranked_results
        if item.get("Title", "").lower() not in seen
        and item.get("Title", "").strip().lower() != seed_key
    ]
    return prioritized + remainder


def get_similar_title_priors(seed_title):
    seed_key = seed_title.strip().lower()
    prior_titles = SIMILAR_TITLE_PRIORS_NORMALIZED.get(seed_key, [])
    if prior_titles:
        return prior_titles
    direct_defaults = {
        "crash landing on you": DEFAULT_SIMILAR_TITLE_PRIORS["Crash Landing on You"],
        "guardian: the lonely and great god": DEFAULT_SIMILAR_TITLE_PRIORS[
            "Guardian: The Lonely and Great God"
        ],
        "business proposal": DEFAULT_SIMILAR_TITLE_PRIORS["Business Proposal"],
    }
    return direct_defaults.get(seed_key, [])


def generated_index_boosts(result_title, detected_actors, detected_genres, detected_themes):
    """Return a small, capped multiplier from generated indexes.

    Generated indexes are broad metadata signals, so they should only nudge
    already-retrieved results. They should not inject titles or overpower the
    curated ranking layer.
    """
    multiplier = 1.0
    title_lower = result_title.lower()

    for actor in detected_actors:
        actor_titles = GENERATED_ACTOR_INDEX.get(actor.lower(), [])
        if any(title_lower == candidate.lower() for candidate in actor_titles):
            multiplier += PRIOR_WEIGHTS.get("generated_actor", 0.0)
            break

    for genre in detected_genres:
        genre_titles = GENERATED_GENRE_INDEX.get(genre, [])
        if any(title_lower == candidate.lower() for candidate in genre_titles[:80]):
            multiplier += PRIOR_WEIGHTS.get("generated_genre", 0.0)
            break

    for theme in detected_themes:
        theme_titles = GENERATED_THEME_INDEX.get(theme, [])
        if any(title_lower == candidate.lower() for candidate in theme_titles[:60]):
            multiplier += PRIOR_WEIGHTS.get("generated_theme", 0.0)
            break

    return min(multiplier, PRIOR_WEIGHTS.get("generated_cap", 1.0))


def generated_prior_mode_enabled():
    return GENRE_PRIOR_SOURCE.startswith("calibrated_generated")


def hybrid_prior_mode_enabled():
    return GENRE_PRIOR_SOURCE == "hybrid_calibrated"


def fallback_genre_prior_mode_enabled():
    return GENRE_PRIOR_SOURCE == "fallback_generated"


def hybrid_actor_prior_mode_enabled():
    return ACTOR_PRIOR_SOURCE == "hybrid_calibrated"


def hybrid_theme_prior_mode_enabled():
    return THEME_PRIOR_SOURCE == "hybrid_calibrated"


def generated_theme_prior_mode_enabled():
    return THEME_PRIOR_SOURCE == "calibrated_generated"


def fallback_theme_prior_mode_enabled():
    return THEME_PRIOR_SOURCE == "fallback_generated"


def get_actor_prior_titles(actor: str):
    if ACTOR_PRIOR_SOURCE == "calibrated_generated":
        return GENERATED_CALIBRATED_ACTOR_INDEX.get(actor.lower(), [])
    curated_titles = ACTOR_PRIOR_TITLES.get(actor)
    if curated_titles:
        return curated_titles
    return GENERATED_CALIBRATED_ACTOR_INDEX.get(actor.lower(), [])


def get_theme_prior_titles(theme: str):
    if generated_theme_prior_mode_enabled():
        return GENERATED_CALIBRATED_THEME_INDEX.get(theme, []), "generated"
    curated_titles = THEME_PRIOR_TITLES.get(theme, [])
    if curated_titles:
        return curated_titles, "curated"
    if fallback_theme_prior_mode_enabled():
        return GENERATED_CALIBRATED_THEME_INDEX.get(theme, []), "fallback"
    return [], "none"


def iter_theme_combo_priors():
    return THEME_COMBINATION_PRIOR_TITLES.items()


def get_genre_prior_titles(genre: str):
    if GENRE_PRIOR_SOURCE == "calibrated_generated_combo_only":
        return [], "none"
    if GENRE_PRIOR_SOURCE == "calibrated_generated":
        return GENERATED_CALIBRATED_GENRE_INDEX.get(genre, []), "generated"
    curated_titles = GENRE_PRIOR_TITLES.get(genre)
    if curated_titles:
        return curated_titles, "curated"
    if fallback_genre_prior_mode_enabled():
        return GENERATED_CALIBRATED_GENRE_INDEX.get(genre, []), "fallback"
    return [], "none"


def iter_genre_combo_priors():
    if GENRE_PRIOR_SOURCE in {
        "calibrated_generated",
        "calibrated_generated_combo_only",
    }:
        return combo_prior_keys(GENERATED_CALIBRATED_GENRE_COMBO_INDEX).items()
    return GENRE_COMBINATION_PRIOR_TITLES.items()


def iter_generated_genre_combo_priors():
    return combo_prior_keys(GENERATED_CALIBRATED_GENRE_COMBO_INDEX).items()


def drama_matches_detected_genre(drama, genre_name):
    genre_lower = genre_name.lower()
    if genre_lower in str(drama.get("Genre", "")).lower():
        return True
    if generated_prior_mode_enabled() or hybrid_prior_mode_enabled():
        title_lower = str(drama.get("Title", "")).lower()
        generated_titles = GENERATED_CALIBRATED_GENRE_INDEX.get(genre_name, [])
        return any(title_lower == title.lower() for title in generated_titles[:80])
    return False


# ======================================================
# STAGE 4 — HYBRID RECOMMENDATION PIPELINE (v4.0 with Phase 1)
# ======================================================
def recommend(
    title: str,
    top_n=5,
    alpha=0.7,  # Will be overridden by dynamic alpha
    genre=None,
    director=None,
    publisher=None,
    top_rated=False,
    description=None,
    rating_value=None,
    rating_count=None,
    keywords=None,
    screenwriters=None,
    sort_by=None,
    sort_order="desc",
    similar_to=None,
    refresh=0,
    seen_titles=None,
    debug=False,
    user_id=None,  # NEW: For analytics tracking
    session_id=None,  # NEW: For session tracking
):
    """
    Stage-based pipeline with Phase 1 enhancements:
    0. Query Analysis (NEW) - Intent detection, query expansion
    1. Apply filters to create filtered corpus (PRE-FILTERING)
    2. Resolve user input (fuzzy match or free-text)
    3. Semantic search (FAISS) on filtered corpus with expanded query
    4. Lexical search (BM25) on filtered corpus with expanded query
    5. Hybrid combination with dynamic alpha
    6. Optional reranking (Cross-Encoder)
    7. Analytics logging (NEW)
    """

    seen_title_set = {
        title.strip().lower()
        for title in (seen_titles.split("|") if isinstance(seen_titles, str) else seen_titles or [])
        if title and title.strip()
    }
    debug_info = {
        "search_mode": "hybrid",
        "resolved_title": None,
        "resolved_source": None,
        "similar_to": similar_to,
        "semantic_weight": None,
        "bm25_weight": None,
        "excluded_genres": [],
        "excluded_themes": [],
        "seen_titles_penalized": len(seen_title_set),
        "extra_prior_terms": [],
    }
    matched_extra_priors = extra_prior_matches(f"{title} {keywords or ''}")
    has_specific_extra_prior = any(
        category in SPECIFIC_EXTRA_PRIOR_CATEGORIES
        for category, _, _ in matched_extra_priors
    )
    generic_quality_query = is_generic_quality_query(title)
    debug_info["generic_quality_query"] = generic_quality_query

    extracted_similar_to, extracted_source = extract_similar_to_title(title, metadata)
    if not similar_to and extracted_similar_to:
        similar_to = extracted_similar_to
        debug_info["similar_to"] = similar_to
        debug_info["resolved_source"] = f"similar_phrase:{extracted_source}"

    # ---- Check cache first (skip if personalized or debugging) ----
    if not user_id and not debug:
        filters_dict = {
            "genre": genre,
            "director": director,
            "publisher": publisher,
            "rating_value": rating_value,
            "rating_count": rating_count,
            "top_rated": top_rated,
            "description": description,
            "keywords": keywords,
            "screenwriters": screenwriters,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "similar_to": similar_to,
            "refresh": refresh,
            "seen_titles": "|".join(sorted(seen_title_set)),
            "debug": debug,
        }
        cache_key = get_cache_key(title, top_n, genre, filters_dict)
        cached = get_cached_result(cache_key)
        if cached:
            print(f"⚡ Cache hit for query: '{title}'")
            return cached

    # ---- Stage 4.0: QUERY ANALYSIS (Phase 1) ----
    analysis = query_analyzer.analyze(title)
    intent = analysis["intent"]
    expanded_query = analysis["expanded_query"]
    dynamic_alpha = analysis["dynamic_alpha"]
    entities = analysis["entities"]

    print(f"🔍 Query Analysis: Intent={intent.value}, Alpha={dynamic_alpha:.2f}")
    print(f"📝 Expanded Query: {expanded_query}")
    if entities.get("genres"):
        print(f"🎭 Detected Genres: {entities['genres']}")
    if entities.get("actors"):
        print(f"🎬 Detected Actors: {entities['actors']}")

    excluded_genres = entities.get("exclude_genres", [])
    excluded_themes = entities.get("exclude_themes", [])
    excluded_emotions = entities.get("exclude_emotions", [])
    debug_info["excluded_genres"] = excluded_genres
    debug_info["excluded_themes"] = excluded_themes
    debug_info["excluded_emotions"] = excluded_emotions

    # Get search strategy for this intent
    strategy = get_search_strategy(intent)

    # Use dynamic alpha instead of static
    alpha = dynamic_alpha
    is_similar_query = bool(similar_to) or intent == QueryIntent.SIMILAR_TO

    # ---- Stage 4.1: PRE-FILTER the dataset ----
    filtered_metadata = metadata.copy()

    # Check for exact title match FIRST - skip filtering if exact match exists
    exact_title_match, title_match_source = resolve_title(title, metadata, fuzzy_threshold=95)
    title_resolution_match = exact_title_match
    if title_resolution_match:
        debug_info["resolved_title"] = title_resolution_match.get("Title")
        debug_info["resolved_source"] = title_match_source
    if title_resolution_match:
        print(
            f"✓ Title found: {title_resolution_match['Title']} - skipping genre/actor filtering"
        )
        # Skip to search with exact match prioritized
    else:
        # Apply detected genres as filters if no explicit genre filter provided
        detected_genres = entities.get("genres", [])
        detected_actors = entities.get("actors", [])
        detected_themes = entities.get("themes", [])

        if detected_genres and not genre and not detected_themes and not is_similar_query:
            # Filter by detected genres (OR logic - match any detected genre)
            filtered_metadata = [
                r
                for r in filtered_metadata
                if any(drama_matches_detected_genre(r, g) for g in detected_genres)
            ]
            print(
                f"🎯 Genre filtering applied: {len(filtered_metadata)} dramas match genres {detected_genres}"
            )
        elif detected_genres and detected_themes and not genre:
            print(
                f"🎯 Genre pre-filter skipped for theme query; ranking will use genres {detected_genres} and themes {detected_themes}"
            )

    # Define these outside the else block for later use
    detected_genres = entities.get("genres", [])
    detected_actors = entities.get("actors", [])

    # Apply detected actors as filters (search in Cast field)
    if detected_actors:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if any(
                actor.lower() in str(r.get("Cast", "")).lower()
                for actor in detected_actors
            )
        ]
        print(
            f"🎬 Actor filtering applied: {len(filtered_metadata)} dramas with actors {detected_actors}"
        )

    # Apply all filters to create a subset
    if genre:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if genre.lower() in str(r.get("Genre", "")).lower()
            or genre.lower() in str(r.get("genres", "")).lower()
        ]
    if director:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if director.lower() in str(r.get("Director", "")).lower()
            or director.lower() in str(r.get("directors", "")).lower()
        ]
    if publisher:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if publisher.lower() in str(r.get("publisher", "")).lower()
        ]
    if description:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if description.lower() in str(r.get("Description", "")).lower()
            or description.lower() in str(r.get("description", "")).lower()
        ]
    if rating_value:
        try:
            rating_value_val = float(rating_value)
            filtered_metadata = [
                r
                for r in filtered_metadata
                if float(r.get("rating_value", r.get("score", 0))) >= rating_value_val
            ]
        except Exception:
            pass
    if rating_count:
        try:
            rating_count_val = float(rating_count)
            filtered_metadata = [
                r
                for r in filtered_metadata
                if float(r.get("rating_count", 0)) >= rating_count_val
            ]
        except Exception:
            pass
    if keywords:
        keyword_terms = keyword_filter_terms(keywords)
        original_keyword_filtered = [
            r
            for r in filtered_metadata
            if any(term in str(r.get("keywords", "")).lower() for term in keyword_terms)
        ]
        if original_keyword_filtered:
            filtered_metadata = original_keyword_filtered
        else:
            fallback_titles = keyword_generated_fallback_titles(keywords)
            filtered_metadata = [
                r
                for r in filtered_metadata
                if str(r.get("Title", "")).lower() in fallback_titles
            ]
    if screenwriters:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if screenwriters.lower() in str(r.get("screenwriters", "")).lower()
        ]
    if excluded_genres:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if not any(
                excluded.lower() in str(r.get("Genre", "")).lower()
                for excluded in excluded_genres
            )
        ]
    if excluded_themes:
        filtered_metadata = [
            r
            for r in filtered_metadata
            if not any(
                excluded in str(r.get("Description", "")).lower()
                or excluded in str(r.get("keywords", "")).lower()
                for excluded in excluded_themes
            )
        ]
    if excluded_emotions:
        emotion_exclusion_terms = {
            "dark": ["dark", "grim", "violent", "violence", "brutal", "serial killer"],
            "scary": ["scary", "horror", "ghost", "haunted", "creepy"],
            "sad": ["sad", "tragic", "tearjerker", "heartbreaking"],
            "intense": ["intense", "violent", "brutal", "suspense"],
        }
        excluded_terms = [
            term
            for emotion in excluded_emotions
            for term in emotion_exclusion_terms.get(emotion, [emotion])
        ]
        filtered_metadata = [
            r
            for r in filtered_metadata
            if not any(
                term in " ".join(
                    str(r.get(field, ""))
                    for field in ["Title", "Genre", "Description", "keywords"]
                ).lower()
                for term in excluded_terms
            )
        ]
    if re.search(r"\b(without|no|not|exclude|except)\s+zombies?\b", title.lower()):
        filtered_metadata = [
            r
            for r in filtered_metadata
            if "zombie"
            not in " ".join(
                str(r.get(field, "")) for field in ["Title", "Description", "keywords"]
            ).lower()
        ]

    # If no results after filtering, return empty
    if not filtered_metadata:
        return {
            "query": {"Title": title},
            "filters": {
                "genre": genre,
                "director": director,
                "publisher": publisher,
                "top_rated": top_rated,
                "description": description,
                "rating_value": rating_value,
                "rating_count": rating_count,
                "keywords": keywords,
                "screenwriters": screenwriters,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "similar_to": similar_to,
            },
            "recommendations": [],
            "message": "No dramas match your filters. Try broadening your search criteria.",
        }

    print(
        f"Filtered corpus: {len(filtered_metadata)} dramas (from {len(metadata)} total)"
    )

    # Create indices mapping for the filtered corpus
    title_to_original_idx = {m["Title"]: i for i, m in enumerate(metadata)}
    filtered_indices = [title_to_original_idx[m["Title"]] for m in filtered_metadata]

    # ---- Stage 4.2: Title resolution (use expanded query) ----
    drama = next(
        (m for m in filtered_metadata if m["Title"].lower() == title.lower()), None
    )
    resolved_title_match = drama or resolve_title_alias(title, filtered_metadata)
    if resolved_title_match:
        drama = resolved_title_match
    high_confidence_fuzzy_match = None

    if (
        not drama
        and intent == QueryIntent.VAGUE
        and not generic_quality_query
        and not detected_genres
        and not detected_actors
        and not entities.get("themes", [])
        and len(title.strip()) >= 8
    ):
        typo_candidates = [m for m in filtered_metadata if not is_special_or_meta_title(m)]
        typo_title_match, typo_title_source = resolve_typo_title(
            title, typo_candidates or filtered_metadata
        )
        if typo_title_match:
            drama = typo_title_match
            high_confidence_fuzzy_match = typo_title_match
            debug_info["resolved_title"] = drama.get("Title")
            debug_info["resolved_source"] = typo_title_source
            print(
                f"Typo title resolved: '{title}' -> '{drama['Title']}' ({typo_title_source})"
            )

    allow_high_confidence_fuzzy = intent in [QueryIntent.SPECIFIC_TITLE]
    if not drama and allow_high_confidence_fuzzy:
        filtered_titles = [m["Title"] for m in filtered_metadata]
        if filtered_titles:
            match, score, _ = process.extractOne(
                title, filtered_titles, scorer=fuzz.WRatio
            )
            if match and score >= 90:
                high_confidence_fuzzy_match = next(
                    (m for m in filtered_metadata if m["Title"] == match), None
                )
                drama = high_confidence_fuzzy_match
                debug_info["resolved_title"] = drama.get("Title")
                debug_info["resolved_source"] = f"fuzzy:{score:.1f}"
                print(
                    f"High-confidence title match: '{title}' -> '{match}' ({score:.1f}%)"
                )

    # Only try fuzzy matching for specific title searches, not genre/vague queries
    skip_fuzzy_intents = [
        QueryIntent.SIMILAR_TO,
        QueryIntent.GENRE_BROWSE,
        QueryIntent.VAGUE,
        QueryIntent.EMOTION_BASED,
        QueryIntent.TOP_RATED,
        QueryIntent.TRENDING,
        QueryIntent.YEAR_BASED,
        QueryIntent.ACTOR_BASED,
    ]

    if not drama and intent not in skip_fuzzy_intents:
        # Try fuzzy match only within filtered corpus and only for specific title searches
        filtered_titles = [m["Title"] for m in filtered_metadata]
        if filtered_titles:
            match, score, _ = process.extractOne(
                title, filtered_titles, scorer=fuzz.WRatio
            )
            if match and score >= 60:
                drama = next(
                    (m for m in filtered_metadata if m["Title"] == match), None
                )
                print(
                    f"Fuzzy match: '{title}' -> '{match}' (confidence: {score:.1f}%)".encode(
                        "utf-8", errors="replace"
                    ).decode(
                        "utf-8"
                    )
                )
                # Use expanded query for better semantic search
                query_text = f"{drama['Title']} {drama.get('Genre', '')} {drama.get('Description', '')} {drama.get('Cast', '')} {expanded_query}"
            else:
                print(f"No close match found for '{title}', using expanded query.")
                query_text = expanded_query  # Use expanded query
        else:
            query_text = expanded_query
    elif not drama:
        # For genre/vague queries, use expanded query directly
        if generic_quality_query:
            query_text = "highly rated popular acclaimed must watch korean drama"
        else:
            query_text = expanded_query
        print(f"Genre/vague query detected, using expanded query: '{query_text}'")
    else:
        query_text = f"{drama['Title']} {drama.get('Genre', '')} {drama.get('Description', '')} {drama.get('Cast', '')} {expanded_query}"

    title_similarity_mode = bool(drama) and not similar_to
    if title_similarity_mode:
        print(
            f"Title similarity mode: using '{drama['Title']}' as the seed drama and suppressing keyword-only matches"
        )
        query_text = " ".join(
            str(drama.get(field, ""))
            for field in ["Genre", "Description", "keywords", "Cast", "Director"]
        )

    # ---- Stage 4.3: FAISS Semantic Search on filtered corpus ----
    # query_text is drama-metadata-derived (passage-like) whenever a seed drama was
    # resolved (fuzzy title match or title-similarity mode); otherwise it's genuine
    # user query text.
    encode_mode = "passage" if drama else "query"
    query_emb = cached_encode(query_text, mode=encode_mode)
    # Optimize search_k for better performance while maintaining accuracy
    # Only search within filtered corpus + small buffer
    search_k = min(
        len(filtered_metadata) + 20,
        max(top_n * 20, 200) if title_similarity_mode else max(top_n * 5, 50),
    )
    D_all, I_all = index.search(query_emb, search_k)

    # Filter FAISS results to only include filtered_metadata indices
    faiss_results = [
        (metadata[idx], float(score))
        for idx, score in zip(I_all[0], D_all[0])
        if idx < len(metadata) and idx in filtered_indices
    ][
        : top_n + 20
    ]  # Take top results from filtered set

    # ---- Stage 4.3: BM25 Lexical Search on filtered corpus ----
    # Get BM25 scores for all dramas, then filter
    bm25_scores_all = bm25.get_scores(query_text.split())
    bm25_results = [
        (metadata[idx], float(bm25_scores_all[idx])) for idx in filtered_indices
    ]
    bm25_results = sorted(bm25_results, key=lambda x: x[1], reverse=True)[: top_n + 20]

    # ---- Stage 4.4: Combine Results ----
    combined_scores = {}
    semantic_components = {}
    lexical_components = {}
    max_bm25 = max([score for _, score in bm25_results]) if bm25_results else 1
    if max_bm25 == 0:
        max_bm25 = 1

    semantic_weight = 1.0 if title_similarity_mode else alpha
    lexical_weight = 0.0 if title_similarity_mode else (1 - alpha)
    debug_info["semantic_weight"] = semantic_weight
    debug_info["bm25_weight"] = lexical_weight
    debug_info["search_mode"] = (
        "similar_to" if similar_to else "title_similarity" if title_similarity_mode else intent.value
    )

    for rec, score in faiss_results:
        semantic_score = semantic_weight * score
        semantic_components[rec["Title"]] = semantic_score
        combined_scores[rec["Title"]] = semantic_score
    if lexical_weight > 0:
        for rec, score in bm25_results:
            lexical_score = lexical_weight * (score / max_bm25)
            lexical_components[rec["Title"]] = lexical_score
            combined_scores[rec["Title"]] = combined_scores.get(rec["Title"], 0) + (
                lexical_score
            )

    # Apply genre boost if genres were detected
    if detected_genres:
        print(f"🚀 Applying genre boost for: {detected_genres}")
        for result_title, score in list(combined_scores.items()):
            drama = next(
                (m for m in filtered_metadata if m["Title"] == result_title), None
            )
            if drama:
                drama_genres = str(drama.get("Genre", "")).lower()
                # Count matching genres
                matching_count = sum(
                    1 for g in detected_genres if g.lower() in drama_genres
                )

                if matching_count > 0:
                    # Higher boost for dramas matching ALL detected genres
                    if (
                        matching_count >= len(detected_genres)
                        and len(detected_genres) > 1
                    ):
                        boost = 1.6  # 60% boost for full match
                    else:
                        boost = 1.4  # 40% boost for partial match

                    # Additional boost for high-rated dramas (8.0+)
                    try:
                        rating = float(drama.get("rating_value", 0))
                        if rating >= 8.5:
                            boost += 0.15  # Extra 15% for highly rated
                        elif rating >= 8.0:
                            boost += 0.1  # Extra 10% for good rating
                    except:
                        pass

                    combined_scores[result_title] = score * boost
                    print(
                        f"   ✓ Boosted: {result_title} ({matching_count}/{len(detected_genres)} genres, boost={boost:.2f})"
                    )

        detected_genre_set = {genre.lower() for genre in detected_genres}
        genre_prior_decay = 0.09 if generated_prior_mode_enabled() else 0.03
        matched_genre_combo_prior = False
        for genre_combo, prior_titles in iter_genre_combo_priors():
            if {genre.lower() for genre in genre_combo}.issubset(detected_genre_set):
                matched_genre_combo_prior = True
                add_prior_title_boosts(
                    combined_scores,
                    filtered_metadata,
                    prior_titles,
                    boost=PRIOR_WEIGHTS.get("genre_combo", 2.55),
                    decay=genre_prior_decay,
                )

        if fallback_genre_prior_mode_enabled() and not matched_genre_combo_prior:
            for genre_combo, prior_titles in iter_generated_genre_combo_priors():
                if {genre.lower() for genre in genre_combo}.issubset(detected_genre_set):
                    matched_genre_combo_prior = True
                    add_prior_title_boosts(
                        combined_scores,
                        filtered_metadata,
                        prior_titles,
                        boost=PRIOR_WEIGHTS.get("fallback_genre_combo", 0.85),
                        decay=0.08,
                    )

        use_single_genre_priors = not (
            generated_prior_mode_enabled()
            and matched_genre_combo_prior
            and len(detected_genres) > 1
        )
        if use_single_genre_priors:
            for detected_genre in detected_genres:
                prior_titles, prior_source = get_genre_prior_titles(detected_genre)
                if prior_titles:
                    genre_boost = (
                        PRIOR_WEIGHTS.get("fallback_genre", 0.65)
                        if prior_source == "fallback"
                        else PRIOR_WEIGHTS.get("genre", 2.2)
                    )
                    if has_specific_extra_prior and len(detected_genres) == 1:
                        genre_boost = min(
                            genre_boost,
                            PRIOR_WEIGHTS.get("specific_query_genre_cap", 0.9),
                        )
                    add_prior_title_boosts(
                        combined_scores,
                        filtered_metadata,
                        prior_titles,
                        boost=genre_boost,
                        decay=genre_prior_decay,
                    )
        else:
            print(
                "Generated combo prior matched; single generated genre priors skipped"
            )

        if hybrid_prior_mode_enabled():
            matched_generated_combo_prior = False
            for genre_combo, prior_titles in iter_generated_genre_combo_priors():
                if {genre.lower() for genre in genre_combo}.issubset(detected_genre_set):
                    matched_generated_combo_prior = True
                    add_prior_title_boosts(
                        combined_scores,
                        filtered_metadata,
                        prior_titles,
                        boost=PRIOR_WEIGHTS.get("hybrid_genre_combo", 0.95),
                        decay=0.08,
                    )

            if not (matched_generated_combo_prior and len(detected_genres) > 1):
                for detected_genre in detected_genres:
                    prior_titles = GENERATED_CALIBRATED_GENRE_INDEX.get(
                        detected_genre, []
                    )
                    if prior_titles:
                        add_prior_title_boosts(
                            combined_scores,
                            filtered_metadata,
                            prior_titles,
                            boost=PRIOR_WEIGHTS.get("hybrid_genre", 0.75),
                            decay=0.08,
                        )

        apply_generated_query_profile_boosts(
            combined_scores, filtered_metadata, title, detected_genres
        )

    detected_themes = entities.get("themes", [])
    if detected_themes:
        print(f"💡 Applying theme boost for: {detected_themes}")
        detected_theme_set = set(detected_themes)
        for theme_combo, prior_titles in iter_theme_combo_priors():
            if set(theme_combo).issubset(detected_theme_set):
                add_prior_title_boosts(
                    combined_scores,
                    filtered_metadata,
                    prior_titles,
                    boost=PRIOR_WEIGHTS.get("theme_combo", 3.1),
                )

        for detected_theme in detected_themes:
            prior_titles, prior_source = get_theme_prior_titles(detected_theme)
            if prior_titles:
                theme_boost = (
                    PRIOR_WEIGHTS.get("fallback_theme", 0.8)
                    if prior_source == "fallback"
                    else PRIOR_WEIGHTS.get("theme", 2.4)
                )
                add_prior_title_boosts(
                    combined_scores,
                    filtered_metadata,
                    prior_titles,
                    boost=theme_boost,
                )

        if hybrid_theme_prior_mode_enabled():
            for detected_theme in detected_themes:
                generated_prior_titles = GENERATED_CALIBRATED_THEME_INDEX.get(
                    detected_theme, []
                )
                if generated_prior_titles:
                    add_prior_title_boosts(
                        combined_scores,
                        filtered_metadata,
                        generated_prior_titles,
                        boost=PRIOR_WEIGHTS.get("hybrid_theme", 0.3),
                        decay=0.05,
                    )

        theme_keywords = {
            "north korea": ["north korea", "north korean", "defector", "dmz"],
            "food": ["restaurant", "food", "cooking", "chef", "culinary", "kitchen"],
            "time travel": ["time travel", "time slip", "time loop", "past life"],
            "contract marriage": ["contract marriage", "fake marriage", "marriage contract"],
            "rich ceo romance": ["rich ceo", "ceo", "chaebol", "rich boss"],
            "school bullying": [
                "school bullying",
                "bullying",
                "school violence",
                "bully revenge",
                "bullying revenge",
            ],
            "legal corruption": ["law firm", "corruption", "corrupt", "prosecutor"],
            "supernatural hotel": ["ghost", "supernatural", "hotel", "spirit"],
            "survival game": ["survival game", "survival", "deadly game", "game"],
            "startup workplace": ["startup", "start-up", "workplace", "office"],
            "healing slice of life": ["healing", "slice of life", "comfort", "everyday"],
            "revenge": ["revenge", "vengeance", "payback"],
            "medical": ["doctor", "hospital", "medical"],
            "law": ["lawyer", "attorney", "law", "court"],
        }
        for result_title, score in list(combined_scores.items()):
            drama = next(
                (m for m in filtered_metadata if m["Title"] == result_title), None
            )
            if not drama:
                continue
            searchable_text = " ".join(
                str(drama.get(field, ""))
                for field in ["Title", "Genre", "Description", "keywords", "Cast"]
            ).lower()
            matching_theme_count = sum(
                1
                for theme in detected_themes
                if any(
                    keyword in searchable_text
                    for keyword in theme_keywords.get(theme, [])
                )
            )
            if matching_theme_count:
                combined_scores[result_title] = score * (
                    1.35 + 0.15 * matching_theme_count
                )

        if detected_genres:
            for result_title, score in list(combined_scores.items()):
                drama = next(
                    (m for m in filtered_metadata if m["Title"] == result_title), None
                )
                if not drama:
                    continue
                searchable_text = " ".join(
                    str(drama.get(field, ""))
                    for field in ["Title", "Genre", "Description", "keywords"]
                ).lower()
                genre_match = any(
                    drama_matches_detected_genre(drama, genre)
                    for genre in detected_genres
                )
                theme_match = any(
                    any(
                        keyword in searchable_text
                        for keyword in theme_keywords.get(theme, [])
                    )
                    for theme in detected_themes
                )
                if genre_match and theme_match:
                    combined_scores[result_title] = score * 1.35

    if detected_actors:
        print(f"⭐ Applying actor boost for: {detected_actors}")
        for detected_actor in detected_actors:
            prior_titles = get_actor_prior_titles(detected_actor)
            if prior_titles:
                add_prior_title_boosts(
                    combined_scores,
                    filtered_metadata,
                    prior_titles,
                    boost=PRIOR_WEIGHTS.get("actor", 2.35),
                )
            if hybrid_actor_prior_mode_enabled():
                generated_prior_titles = GENERATED_CALIBRATED_ACTOR_INDEX.get(
                    detected_actor.lower(), []
                )
                if generated_prior_titles:
                    add_prior_title_boosts(
                        combined_scores,
                        filtered_metadata,
                        generated_prior_titles,
                        boost=PRIOR_WEIGHTS.get("hybrid_actor", 1.0),
                        decay=0.05,
                    )

        for result_title, score in list(combined_scores.items()):
            drama = next(
                (m for m in filtered_metadata if m["Title"] == result_title), None
            )
            if not drama:
                continue
            cast_text = str(drama.get("Cast", "")).lower()
            actor_match_count = sum(
                1 for actor in detected_actors if actor.lower() in cast_text
            )
            if actor_match_count:
                combined_scores[result_title] = score * (1.25 + 0.2 * actor_match_count)

    if keywords:
        keyword_terms = keyword_filter_terms(keywords)
        prior_titles = keyword_prior_titles(keywords)
        if prior_titles:
            add_prior_title_boosts(
                combined_scores,
                filtered_metadata,
                prior_titles,
                boost=PRIOR_WEIGHTS.get("keyword", 2.0),
                decay=0.04,
            )

        for result_title, score in list(combined_scores.items()):
            drama = next(
                (m for m in filtered_metadata if m["Title"] == result_title), None
            )
            if not drama:
                continue
            keyword_text = str(drama.get("keywords", "")).lower()
            matching_keyword_count = sum(term in keyword_text for term in keyword_terms)
            if matching_keyword_count:
                combined_scores[result_title] = score * (
                    1.25 + 0.15 * min(matching_keyword_count, 3)
                )

    active_extra_priors = [
        (category, term, prior_titles)
        for category, term, prior_titles in matched_extra_priors
        if not any(excluded in term for excluded in excluded_emotions)
    ]
    for category, term, prior_titles in active_extra_priors:
        extra_boost = PRIOR_WEIGHTS.get(f"{category}_prior", 1.45)
        if category in SPECIFIC_EXTRA_PRIOR_CATEGORIES:
            extra_boost = PRIOR_WEIGHTS.get(f"{category}_prior", 1.85)
        add_prior_title_boosts(
            combined_scores,
            filtered_metadata,
            prior_titles,
            boost=extra_boost,
            decay=0.06,
        )
    if active_extra_priors:
        debug_info["extra_prior_terms"] = [
            f"{category}:{term}" for category, term, _ in active_extra_priors[:12]
        ]
        print(f"Extra priors applied: {debug_info['extra_prior_terms']}")

    generated_boosted_count = 0
    if detected_actors or detected_genres or detected_themes:
        for result_title, score in list(combined_scores.items()):
            multiplier = generated_index_boosts(
                result_title, detected_actors, detected_genres, detected_themes
            )
            if multiplier > 1.0:
                combined_scores[result_title] = score * multiplier
                generated_boosted_count += 1
        if generated_boosted_count:
            print(
                f"Generated index boosts applied to {generated_boosted_count} retrieved results"
            )

    if generic_quality_query:
        add_prior_title_boosts(
            combined_scores,
            filtered_metadata,
            QUALITY_BROWSE_PRIOR_TITLES,
            boost=3.0,
            decay=0.05,
        )
        for result_title, score in list(combined_scores.items()):
            drama = next(
                (m for m in filtered_metadata if m["Title"] == result_title), None
            )
            if drama:
                combined_scores[result_title] = score + (
                    drama_quality_score(drama) / 5.0
                )

    query_text_norm = title.lower()
    if re.search(r"\b(recent|new|latest|fresh|2024|2025)\b", query_text_norm):
        add_prior_title_boosts(
            combined_scores,
            filtered_metadata,
            RECENT_DRAMA_PRIOR_TITLES,
            boost=3.0,
            decay=0.06,
        )

    for query_key, prior_titles in QUERY_COMBO_PRIORS.items():
        if query_matches_prior_term(query_text_norm, query_key):
            add_prior_title_boosts(
                combined_scores,
                filtered_metadata,
                prior_titles,
                boost=3.25,
                decay=0.06,
            )

    for (theme_name, genre_name), prior_titles in THEME_GENRE_COMBO_PRIORS.items():
        if theme_name in detected_themes and genre_name in detected_genres:
            add_prior_title_boosts(
                combined_scores,
                filtered_metadata,
                prior_titles,
                boost=4.5,
                decay=0.08,
            )

    # Sort by combined score (filters already applied in Stage 4.0)
    filtered = [
        next(m for m in filtered_metadata if m["Title"] == t)
        for t, _ in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    ]

    if (
        detected_genres
        and not detected_themes
        and not generic_quality_query
    ):
        filtered = [
            result
            for result in filtered
            if result.get("Title", "").strip().lower() not in BROAD_TITLE_NOISE
        ]

    # Apply popularity boost - push highly-rated dramas up in genre searches
    if detected_genres and not exact_title_match:

        def get_popularity_score(drama):
            try:
                rating = float(drama.get("rating_value", 0))
                return rating
            except:
                return 0

        # Sort by combined score but with rating as tiebreaker
        filtered = sorted(
            filtered,
            key=lambda r: (combined_scores.get(r["Title"], 0), get_popularity_score(r)),
            reverse=True,
        )

    # ---- EXACT TITLE INJECTION ----
    # If query matches a title exactly or closely, ensure it's at the top
    exact_match = next(
        (m for m in metadata if m["Title"].lower() == title.lower()), None
    )
    if exact_match and not title_similarity_mode:
        # Remove from current position if exists, then prepend
        filtered = [r for r in filtered if r["Title"] != exact_match["Title"]]
        filtered.insert(0, exact_match)
        print(f"✓ Exact title match injected: {exact_match['Title']}")

    alias_match = resolve_title_alias(title, metadata)
    resolved_match = alias_match or high_confidence_fuzzy_match
    if not resolved_match and not exact_match and intent not in skip_fuzzy_intents:
        resolved_match = drama

    if resolved_match and not title_similarity_mode:
        filtered = [r for r in filtered if r["Title"] != resolved_match["Title"]]
        filtered.insert(0, resolved_match)
        print(f"Title match injected: {resolved_match['Title']}")

    if title_similarity_mode:
        filtered = [r for r in filtered if r["Title"] != drama["Title"]]
        faiss_rank = {rec["Title"]: rank for rank, (rec, _) in enumerate(faiss_results)}
        filtered = sorted(
            filtered,
            key=lambda r: seed_similarity_score(
                drama, r, faiss_rank.get(r["Title"])
            ),
            reverse=True,
        )
        filtered = apply_similar_title_priors(
            drama["Title"], filtered, filtered_metadata
        )
        debug_info["similar_prior_titles"] = get_similar_title_priors(drama["Title"])

    if seen_title_set:
        unseen = [r for r in filtered if r["Title"].lower() not in seen_title_set]
        seen = [r for r in filtered if r["Title"].lower() in seen_title_set]
        filtered = unseen + seen

    # Handle similar_to filter (requires FAISS search)
    if similar_to:
        # Find dramas similar to a given title within filtered metadata
        sim_drama = next(
            (m for m in filtered_metadata if m["Title"].lower() == similar_to.lower()),
            None,
        )
        if sim_drama:
            sim_query = " ".join(
                str(sim_drama.get(field, ""))
                for field in ["Genre", "Description", "keywords", "Cast", "Director"]
            )
            sim_emb = cached_encode(sim_query, mode="passage")
            D_sim, I_sim = index.search(sim_emb, len(filtered_metadata) + 20)
            # Only keep results that are in our filtered set
            sim_results = [
                metadata[idx]
                for idx in I_sim[0]
                if idx < len(metadata)
                and idx in filtered_indices
                and metadata[idx]["Title"].lower() != similar_to.lower()
            ]
            faiss_rank = {
                result["Title"]: rank for rank, result in enumerate(sim_results)
            }
            filtered = sorted(
                sim_results,
                key=lambda r: seed_similarity_score(
                    sim_drama, r, faiss_rank.get(r["Title"])
                ),
                reverse=True,
            )
            filtered = apply_similar_title_priors(
                sim_drama["Title"], filtered, filtered_metadata
            )
            debug_info["similar_prior_titles"] = get_similar_title_priors(
                sim_drama["Title"]
            )

    if seen_title_set:
        unseen = [r for r in filtered if r["Title"].lower() not in seen_title_set]
        seen = [r for r in filtered if r["Title"].lower() in seen_title_set]
        filtered = unseen + seen

    # Sorting
    if sort_by:
        reverse = sort_order == "desc"
        filtered = sorted(
            filtered,
            key=lambda r: (
                float(r.get(sort_by, 0))
                if isinstance(r.get(sort_by, 0), (int, float, str))
                and str(r.get(sort_by, 0)).replace(".", "", 1).isdigit()
                else str(r.get(sort_by, ""))
            ),
            reverse=reverse,
        )
    elif top_rated:
        filtered = sorted(
            filtered,
            key=lambda r: float(r.get("rating_value", r.get("score", 0))),
            reverse=True,
        )

    should_diversify = (
        refresh
        and not sort_by
        and not top_rated
        and not title_similarity_mode
        and intent
        in [QueryIntent.GENRE_BROWSE, QueryIntent.VAGUE, QueryIntent.EMOTION_BASED]
    )
    if should_diversify and len(filtered) > top_n:
        rng = random.Random(f"{title}|{genre}|{refresh}")
        quality_pool_size = min(len(filtered), max(top_n * 4, 20))
        quality_pool = filtered[:quality_pool_size]
        fixed_head = quality_pool[: min(2, len(quality_pool))]
        shuffle_pool = quality_pool[len(fixed_head) :]
        rng.shuffle(shuffle_pool)
        filtered = fixed_head + shuffle_pool + filtered[quality_pool_size:]
        print(f"Applied browse refresh diversification: refresh={refresh}")

    top_results = filtered[:top_n]

    query_alias = title.lower().strip()
    canonical_alias_title = TITLE_ALIASES.get(query_alias)
    if canonical_alias_title:
        aliased_results = []
        for result in top_results:
            if result.get("Title", "").lower() == canonical_alias_title.lower():
                result = result.copy()
                result["original_title"] = result["Title"]
                result["alias_title"] = title.strip()
                result["Title"] = title.strip()
            aliased_results.append(result)
        top_results = aliased_results

    if debug:
        for rank, result in enumerate(top_results, 1):
            result_title = result.get("original_title", result.get("Title", ""))
            semantic_score = semantic_components.get(result_title, 0.0)
            lexical_score = lexical_components.get(result_title, 0.0)
            retrieval_score = semantic_score + lexical_score
            final_score = combined_scores.get(result_title, retrieval_score)
            result["ranking_debug"] = {
                "rank_before_personalization": rank,
                "semantic_component": round(float(semantic_score), 6),
                "bm25_component": round(float(lexical_score), 6),
                "retrieval_score": round(float(retrieval_score), 6),
                "ranking_score": round(float(final_score), 6),
                "boost_delta": round(float(final_score - retrieval_score), 6),
            }

    # ---- Stage 4.5: Optional Reranking ----
    # Disabled for performance - cross-encoder adds 2-3 seconds
    # Re-enable for production if accuracy is critical
    if False and use_reranker and reranker:  # Disabled for speed
        try:
            # Limit to top 20 candidates to reduce reranking time
            rerank_candidates = top_results[:20]
            pairs = [[query_text, r["Description"]] for r in rerank_candidates]
            rerank_scores = reranker.predict(pairs)
            top_results = [
                r
                for _, r in sorted(
                    zip(rerank_scores, rerank_candidates),
                    key=lambda x: x[0],
                    reverse=True,
                )
            ] + top_results[
                20:
            ]  # Keep rest in original order
        except Exception as e:
            print(f"Reranking failed: {e}")

    # ---- Stage 4.6: PERSONALIZATION (Phase 2 - NEW!) ----
    personalization_info = None
    if user_id:
        try:
            # Load user profile
            profile_manager = get_profile_manager()
            user_profile = profile_manager.load_profile(user_id)

            # Apply personalized weighting
            personalization_engine = get_personalization_engine()

            # Adjust alpha based on user preferences (explore vs exploit)
            personalized_alpha = personalization_engine.calculate_user_specific_alpha(
                user_profile, alpha
            )

            # Apply personalized boosting to results
            top_results = personalization_engine.personalize_results(
                top_results, user_profile, apply_boosting=True
            )

            print(
                f"🎯 Personalization Applied: Alpha {alpha:.2f} → {personalized_alpha:.2f}"
            )
            print(f"   Boosted based on user preferences")

            # Prepare personalization info for frontend
            # Calculate average boost for reporting
            avg_boost = (
                sum(r.get("boost_multiplier", 1.0) for r in top_results)
                / len(top_results)
                if top_results
                else 1.0
            )
            boost_applied = any(
                r.get("boost_multiplier", 1.0) > 1.01 for r in top_results
            )

            personalization_info = {
                "applied": True,
                "boost_applied": boost_applied,
                "average_boost": avg_boost,
                "alpha_adjusted": abs(personalized_alpha - alpha) > 0.01,
                "original_alpha": alpha,
                "personalized_alpha": personalized_alpha,
                "top_genres": user_profile.get("preferences", {}).get("genres", {}),
                "top_actors": user_profile.get("preferences", {}).get("actors", {}),
                "persona": user_profile.get("persona", []),
                "total_interactions": user_profile.get("statistics", {}).get(
                    "total_interactions", 0
                ),
            }

        except Exception as e:
            print(f"Warning: Personalization failed: {e}")
            # Continue with non-personalized results
            personalization_info = {"applied": False, "error": str(e)}

    if debug:
        for rank, result in enumerate(top_results, 1):
            ranking_debug = result.setdefault("ranking_debug", {})
            ranking_debug["final_rank"] = rank
            ranking_debug["personalization_multiplier"] = round(
                float(result.get("boost_multiplier", 1.0)), 6
            )
            ranking_debug["personalized_score"] = round(
                float(result.get("personalized_score", ranking_debug.get("ranking_score", 0.0))),
                6,
            )

    # ---- Stage 4.7: Analytics Logging (Phase 1) ----
    result_titles = [r["Title"] for r in top_results]

    # Log search if user_id and session_id provided
    if user_id and session_id:
        try:
            search_id = analytics_tracker.log_search(
                user_id=user_id,
                query=title,
                intent=intent.value,
                results=result_titles,
                filters={
                    "genre": genre,
                    "director": director,
                    "publisher": publisher,
                    "rating_value": rating_value,
                    "rating_count": rating_count,
                },
                session_id=session_id,
            )
            print(f"📊 Search logged: {search_id}")
        except Exception as e:
            print(f"Warning: Analytics logging failed: {e}")

    # Build response with personalization info
    if debug:
        ranking_scores = []
        for rank, result in enumerate(top_results, 1):
            result_title = result.get("original_title", result.get("Title", ""))
            semantic_score = semantic_components.get(result_title, 0.0)
            lexical_score = lexical_components.get(result_title, 0.0)
            retrieval_score = semantic_score + lexical_score
            final_score = combined_scores.get(result_title, retrieval_score)
            score_debug = result.setdefault("ranking_debug", {})
            score_debug.update(
                {
                    "title": result.get("Title", result_title),
                    "final_rank": rank,
                    "semantic_component": round(float(semantic_score), 6),
                    "bm25_component": round(float(lexical_score), 6),
                    "retrieval_score": round(float(retrieval_score), 6),
                    "ranking_score": round(float(final_score), 6),
                    "boost_delta": round(float(final_score - retrieval_score), 6),
                    "personalization_multiplier": round(
                        float(result.get("boost_multiplier", 1.0)), 6
                    ),
                    "personalized_score": round(
                        float(result.get("personalized_score", final_score)), 6
                    ),
                }
            )
            ranking_scores.append(score_debug.copy())
        debug_info["ranking_scores"] = ranking_scores

    response = {
        "query": {"Title": title, "expanded": expanded_query},
        "analysis": {
            "intent": intent.value,
            "dynamic_alpha": dynamic_alpha,
            "confidence": analysis["confidence"],
        },
        "filters": {
            "genre": genre,
            "director": director,
            "publisher": publisher,
            "top_rated": top_rated,
            "description": description,
            "rating_value": rating_value,
            "rating_count": rating_count,
            "keywords": keywords,
            "screenwriters": screenwriters,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "similar_to": similar_to,
            "refresh": refresh,
            "seen_titles": "|".join(sorted(seen_title_set)),
            "debug": debug,
        },
        "recommendations": top_results,
    }
    if debug:
        response["debug"] = debug_info

    # Add personalization info if available
    if personalization_info:
        response["personalization"] = personalization_info
        response["personalization_info"] = (
            personalization_info  # For backward compatibility
        )

    # Cache result if not personalized
    if not user_id and not debug:
        filters_dict = {
            "genre": genre,
            "director": director,
            "publisher": publisher,
            "rating_value": rating_value,
            "rating_count": rating_count,
            "top_rated": top_rated,
            "description": description,
            "keywords": keywords,
            "screenwriters": screenwriters,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "similar_to": similar_to,
            "refresh": refresh,
            "seen_titles": "|".join(sorted(seen_title_set)),
            "debug": debug,
        }
        cache_key = get_cache_key(title, top_n, genre, filters_dict)
        cache_result(cache_key, response)

    return response


# ======================================================
# STAGE 5 — API ROUTES
# ======================================================
@app.get("/")
def root():
    return {
        "message": "SeoulMate Kdrama Recommendation API v4.0 Phase 2 is running",
        "phase_1_features": [
            "Query Intent Detection",
            "Dynamic Weight Adjustment",
            "Query Expansion with Synonyms",
            "Click Tracking & Analytics",
            "Auto-Genre Detection",
        ],
        "phase_2_features": [
            "User Preference Learning",
            "Personalized Weighting (Genre, Actor, Director, Theme)",
            "User Taste Profiles",
            "Dynamic Alpha Adjustment",
            "Interaction-based Learning",
        ],
        "docs": "/docs",
    }


@app.get("/analyze")
def analyze_query(query: str = Query(..., description="Query to analyze")):
    """
    Analyze a query to detect intent, genres, and other entities.
    This is a lightweight endpoint for quick analysis without full recommendation.
    """
    try:
        analysis = query_analyzer.analyze(query)
        return {
            "query": query,
            "intent": (
                analysis["intent"].value
                if hasattr(analysis["intent"], "value")
                else str(analysis["intent"])
            ),
            "entities": analysis["entities"],
            "detected_genres": analysis["entities"].get(
                "genres", []
            ),  # For evaluation script
            "confidence": analysis.get("confidence", 0.8),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/recommend")
def get_recommendations(
    title: str = Query(..., description="Kdrama title or user query"),
    top_n: int = Query(5, description="Number of recommendations"),
    genre: str = Query(None, description="Genre filter"),
    director: str = Query(None, description="Director filter"),
    publisher: str = Query(None, description="Publisher filter"),
    top_rated: bool = Query(False, description="Sort by top rating"),
    description: str = Query(None, description="Description keyword filter"),
    rating_value: float = Query(None, description="Minimum rating value"),
    rating_count: float = Query(None, description="Minimum rating count"),
    keywords: str = Query(None, description="Keywords filter"),
    screenwriters: str = Query(None, description="Screenwriters filter"),
    sort_by: str = Query(
        None,
        description="Sort by field (e.g., rating_value, popularity, date_published, episodes, duration)",
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    similar_to: str = Query(None, description="Find dramas similar to this title"),
    refresh: int = Query(0, description="Refresh token for varied browse results"),
    seen_titles: str = Query(None, description="Pipe-separated titles already shown to the user"),
    debug: bool = Query(False, description="Include search routing/debug details"),
    user_id: str = Query(None, description="User ID for analytics (optional)"),
    session_id: str = Query(None, description="Session ID for analytics (optional)"),
):
    """Main recommendation endpoint with advanced filters, sorting, and Phase 1 enhancements."""
    # Generate session ID if not provided
    if user_id and not session_id:
        import uuid

        session_id = f"session_{uuid.uuid4().hex[:8]}"

    return recommend(
        title,
        top_n,
        alpha=0.7,  # Will be overridden by dynamic alpha
        genre=genre,
        director=director,
        publisher=publisher,
        top_rated=top_rated,
        description=description,
        rating_value=rating_value,
        rating_count=rating_count,
        keywords=keywords,
        screenwriters=screenwriters,
        sort_by=sort_by,
        sort_order=sort_order,
        similar_to=similar_to,
        refresh=refresh,
        seen_titles=seen_titles,
        debug=debug,
        user_id=user_id,
        session_id=session_id,
    )


# ======================================================
# ANALYTICS ENDPOINTS (Phase 1)
# ======================================================
class InteractionRequest(BaseModel):
    user_id: str
    drama_title: str
    interaction_type: str
    search_id: Optional[str] = None
    position: Optional[int] = None
    session_id: Optional[str] = None


@app.post("/analytics/interaction", tags=["Analytics"])
def log_interaction(request: InteractionRequest):
    """
    Log user interaction with a drama
    Used for:
    - Click tracking
    - Implicit feedback
    - Recommendation improvement
    """
    try:
        analytics_tracker.log_interaction(
            user_id=request.user_id,
            drama_title=request.drama_title,
            action=request.interaction_type,
            search_id=request.search_id,
            position=request.position,
            session_id=request.session_id,
        )
        return {"status": "success", "message": "Interaction logged"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to log interaction: {str(e)}"
        )


@app.get("/analytics/popular", tags=["Analytics"])
def get_popular_dramas(
    days: int = Query(7, description="Look back period in days"),
    limit: int = Query(20, description="Number of results"),
):
    """
    Get most popular dramas based on user interactions
    Useful for:
    - Trending section
    - Homepage recommendations
    - Popular now widget
    """
    try:
        popular = analytics_tracker.get_popular_dramas(days=days, limit=limit)
        return {"popular_dramas": popular, "period_days": days}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get popular dramas: {str(e)}"
        )


@app.get("/analytics/trending-searches", tags=["Analytics"])
def get_trending_searches(
    days: int = Query(7, description="Look back period in days"),
    limit: int = Query(20, description="Number of results"),
):
    """
    Get trending search queries
    Useful for:
    - Search suggestions
    - Understanding user interests
    - Content discovery
    """
    try:
        trending = analytics_tracker.get_trending_searches(days=days, limit=limit)
        return {"trending_searches": trending, "period_days": days}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get trending searches: {str(e)}"
        )


@app.get("/analytics/summary", tags=["Analytics"])
def get_analytics_summary(
    days: int = Query(7, description="Look back period in days"),
):
    """
    Get overall analytics summary
    Includes:
    - Total searches
    - Total interactions
    - Click-through rate
    - Unique users
    """
    try:
        summary = analytics_tracker.get_analytics_summary(days=days)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get analytics summary: {str(e)}"
        )


@app.get("/analytics/search-quality", tags=["Analytics"])
def get_search_quality_report(
    days: int = Query(7, description="Look back period in days"),
    limit: int = Query(20, description="Number of rows per section"),
):
    """
    Show search quality signals from runtime analytics:
    - Queries with searches but no clicks/watchlist adds
    - Recent searches without feedback
    - Positive query-drama examples for future training data
    """
    try:
        report = analytics_tracker.get_search_quality_report(days=days, limit=limit)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get search quality report: {str(e)}"
        )


# ======================================================
# USER PROFILE ENDPOINTS (Phase 2)
# ======================================================
@app.get("/profile/{user_id}", tags=["Personalization"])
def get_user_profile(user_id: str):
    """
    Get user's taste profile with preferences and statistics

    Returns:
    - Genre preferences with scores
    - Favorite actors and directors
    - Viewing patterns
    - User persona labels
    - Interaction statistics
    """
    try:
        profile_manager = get_profile_manager()
        user_profile = profile_manager.load_profile(user_id)

        # Get top preferences for easier consumption
        top_genres = profile_manager.get_top_preferences(user_id, "genres", n=10)
        top_actors = profile_manager.get_top_preferences(user_id, "actors", n=10)
        top_directors = profile_manager.get_top_preferences(user_id, "directors", n=5)
        top_themes = profile_manager.get_top_preferences(user_id, "themes", n=10)

        # Convert datetime strings to ensure JSON serialization
        import datetime

        def serialize_datetime(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return obj

        # Ensure all datetime fields are serialized
        if "created_at" in user_profile:
            user_profile["created_at"] = str(user_profile["created_at"])
        if "last_updated" in user_profile:
            user_profile["last_updated"] = str(user_profile["last_updated"])

        return {
            "user_id": user_id,
            "profile": user_profile,
            "top_preferences": {
                "genres": top_genres,
                "actors": top_actors,
                "directors": top_directors,
                "themes": top_themes,
            },
            "persona": user_profile.get("persona", []),
            "statistics": user_profile.get("statistics", {}),
        }
    except Exception as e:
        # Log the full error for debugging
        import traceback

        print(f"ERROR in get_user_profile: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get user profile: {str(e)}"
        )


@app.post("/profile/{user_id}/rate", tags=["Personalization"])
def rate_drama(
    user_id: str,
    drama_title: str = Query(..., description="Title of the drama to rate"),
    rating: float = Query(..., ge=0.0, le=10.0, description="Rating from 0-10"),
):
    """
    Rate a drama and update user preferences

    This will:
    - Update user's genre preferences
    - Update actor/director preferences
    - Adjust user's taste profile
    - Log the rating for analytics
    """
    try:
        # Find the drama in the metadata
        drama_data = None
        for drama in metadata:
            if drama.get("Title", "").lower() == drama_title.lower():
                drama_data = drama
                break

        if not drama_data:
            raise HTTPException(
                status_code=404, detail=f"Drama '{drama_title}' not found"
            )

        # Update user profile
        profile_manager = get_profile_manager()
        profile_manager.update_from_interaction(
            user_id=user_id,
            drama_data=drama_data,
            interaction_type="watched",
            rating=rating,
        )

        # Also log to analytics
        analytics_tracker.log_interaction(
            user_id=user_id,
            session_id=f"rating_{time.time()}",
            search_id=None,
            drama_title=drama_title,
            action="rating",
            position=None,
            metadata={"drama_data": drama_data, "rating": rating},
        )

        return {
            "success": True,
            "message": f"Rating recorded: {drama_title} = {rating}/10",
            "user_id": user_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rate drama: {str(e)}")


@app.delete("/profile/{user_id}", tags=["Personalization"])
def reset_user_profile(user_id: str):
    """
    Reset a user's profile (clear all preferences)

    Use this to:
    - Start fresh with recommendations
    - Clear test data
    - Reset after major preference changes
    """
    try:
        profile_manager = get_profile_manager()
        from pathlib import Path

        profile_path = Path(profile_manager.profiles_dir) / f"{user_id}.json"

        if profile_path.exists():
            profile_path.unlink()
            return {
                "success": True,
                "message": f"Profile reset for user {user_id}",
            }
        else:
            return {
                "success": True,
                "message": f"No profile found for user {user_id} (nothing to reset)",
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset profile: {str(e)}"
        )


@app.get("/analytics/user-stats/{user_id}", tags=["Analytics"])
def get_user_statistics(user_id: str):
    """
    Get statistics for a specific user
    Includes:
    - Total clicks
    - Watchlist additions
    - Interaction history
    - Preferences
    """
    try:
        stats = analytics_tracker.get_user_stats(user_id)
        if not stats:
            return {"user_id": user_id, "message": "No data found for this user"}
        return {"user_id": user_id, "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get user stats: {str(e)}"
        )


# ======================================================
# STAGE 6 — RUN LOCALLY
# ======================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("SEOULMATE_PORT", "8001"))
    reload_enabled = os.environ.get("SEOULMATE_RELOAD", "1") != "0"
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=reload_enabled)
