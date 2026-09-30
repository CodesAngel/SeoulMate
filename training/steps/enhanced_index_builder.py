"""
Enhanced FAISS Index Builder with K-Drama Specific Embeddings

This script builds a better FAISS index by:
1. Using K-drama optimized embeddings (genre, theme, actor weighted)
2. Creating separate indices for different search types
3. Adding theme-based embeddings

Usage:
    python enhanced_index_builder.py --mode full
    python enhanced_index_builder.py --mode themes-only
"""

import os
import argparse
import pandas as pd
import numpy as np
import pickle
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import json

# ======================================================
# Configuration (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "kdrama_dataset.csv")
MODEL_DIR = os.path.join(TRAINING_ROOT, "models")
INDEX_DIR = os.path.join(TRAINING_ROOT, "faiss_index")

# Base model (use fine-tuned if available)
BASE_MODEL = "paraphrase-multilingual-mpnet-base-v2"

# Theme definitions for theme-based embeddings
THEME_DEFINITIONS = {
    "time_travel": {
        "keywords": [
            "time travel",
            "time slip",
            "time loop",
            "past life",
            "future",
            "time machine",
            "temporal",
        ],
        "description": "Stories involving traveling through time, time loops, or characters from different eras meeting",
        "known_dramas": [
            "Signal",
            "Twinkling Watermelon",
            "Queen In-Hyun's Man",
            "Nine: Nine Time Travels",
            "Tomorrow with You",
            "Go Back Couple",
            "Familiar Wife",
            "The King: Eternal Monarch",
            "Rooftop Prince",
            "Dr. Jin",
            "Faith",
            "Live Up to Your Name",
        ],
    },
    "north_korea": {
        "keywords": [
            "north korea",
            "north korean",
            "defector",
            "dmz",
            "soldier",
            "military border",
            "spy",
        ],
        "description": "Stories involving North Korea, defectors, or inter-Korean relations",
        "known_dramas": [
            "Crash Landing on You",
            "The King 2 Hearts",
            "Iris",
            "Athena: Goddess of War",
            "Spy",
            "Snowdrop",
            "Joint Security Area",
        ],
    },
    "food_cooking": {
        "keywords": [
            "restaurant",
            "chef",
            "cooking",
            "food",
            "culinary",
            "kitchen",
            "ramen",
            "cafe",
            "bakery",
            "bistro",
        ],
        "description": "Stories centered around food, cooking, restaurants, or the culinary world",
        "known_dramas": [
            "Wok of Love",
            "Let's Eat",
            "Let's Eat 2",
            "Let's Eat 3",
            "Mystic Pop-up Bar",
            "Pasta",
            "Jewel in the Palace",
            "My Love from the Star",
            "Weightlifting Fairy Kim Bok-joo",
        ],
    },
    "revenge": {
        "keywords": ["revenge", "vengeance", "payback", "retribution", "avenge"],
        "description": "Stories driven by revenge plots and characters seeking justice or payback",
        "known_dramas": [
            "The Glory",
            "Penthouse",
            "Eve",
            "Mine",
            "Sky Castle",
            "The Innocent Man",
            "Cruel City",
            "Defendant",
            "The Devil Judge",
        ],
    },
    "medical": {
        "keywords": [
            "doctor",
            "hospital",
            "medical",
            "surgery",
            "nurse",
            "patient",
            "clinic",
            "physician",
        ],
        "description": "Medical dramas set in hospitals with doctors and healthcare workers",
        "known_dramas": [
            "Hospital Playlist",
            "Hospital Playlist 2",
            "Dr. Romantic",
            "Dr. Romantic 2",
            "Good Doctor",
            "Doctors",
            "Blood",
            "Yong-Pal",
            "Emergency Couple",
            "Brain",
        ],
    },
    "law_legal": {
        "keywords": [
            "lawyer",
            "attorney",
            "court",
            "legal",
            "prosecutor",
            "judge",
            "trial",
            "law firm",
        ],
        "description": "Legal dramas involving lawyers, courtrooms, and the justice system",
        "known_dramas": [
            "Extraordinary Attorney Woo",
            "Law School",
            "Vincenzo",
            "Lawless Lawyer",
            "Suspicious Partner",
            "While You Were Sleeping",
            "I Hear Your Voice",
        ],
    },
    "supernatural": {
        "keywords": [
            "ghost",
            "supernatural",
            "spirit",
            "demon",
            "goblin",
            "magic",
            "fantasy",
            "immortal",
            "gumiho",
        ],
        "description": "Stories with supernatural elements, ghosts, goblins, or magical beings",
        "known_dramas": [
            "Goblin",
            "Hotel Del Luna",
            "My Love from the Star",
            "Guardian",
            "Tale of the Nine Tailed",
            "Alchemy of Souls",
            "The Master's Sun",
        ],
    },
    "office_workplace": {
        "keywords": [
            "office",
            "workplace",
            "company",
            "boss",
            "employee",
            "corporate",
            "business",
            "CEO",
        ],
        "description": "Stories set in office/corporate environments with workplace dynamics",
        "known_dramas": [
            "Business Proposal",
            "What's Wrong with Secretary Kim",
            "Start-Up",
            "Misaeng",
            "Radiant Office",
            "Chief Kim",
            "Hot Stove League",
        ],
    },
    "school_youth": {
        "keywords": [
            "school",
            "student",
            "high school",
            "college",
            "university",
            "campus",
            "teenager",
            "youth",
        ],
        "description": "Coming-of-age stories set in schools with young protagonists",
        "known_dramas": [
            "True Beauty",
            "Extraordinary You",
            "School 2017",
            "Dream High",
            "Reply 1997",
            "Reply 1988",
            "Weightlifting Fairy Kim Bok-joo",
            "Our Beloved Summer",
        ],
    },
    "historical_royalty": {
        "keywords": [
            "king",
            "queen",
            "prince",
            "princess",
            "palace",
            "joseon",
            "dynasty",
            "throne",
            "royal",
        ],
        "description": "Historical dramas set in royal courts with political intrigue",
        "known_dramas": [
            "The Red Sleeve",
            "Moon Lovers",
            "Mr. Sunshine",
            "Kingdom",
            "Jewel in the Palace",
            "Empress Ki",
            "Queen for Seven Days",
            "100 Days My Prince",
        ],
    },
}

# Genre mappings for better matching
GENRE_SYNONYMS = {
    "thriller": ["Thriller", "Suspense", "Mystery", "Crime", "Psychological"],
    "historical": ["Historical", "Period Drama", "Sageuk", "Historical Drama"],
    "romantic comedy": ["Romance", "Comedy"],
    "romcom": ["Romance", "Comedy"],
    "action": ["Action", "Adventure", "Martial Arts"],
    "horror": ["Horror", "Supernatural", "Thriller"],
    "melodrama": ["Melodrama", "Drama", "Romance"],
    "fantasy": ["Fantasy", "Supernatural", "Sci-Fi"],
    "crime": ["Crime", "Thriller", "Mystery", "Detective"],
    "family": ["Family", "Life", "Drama"],
}


def load_dataset(path: str) -> pd.DataFrame:
    """Load and preprocess the drama dataset."""
    print(f"Loading dataset from {path}...")
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df.fillna("", inplace=True)

    # Standardize column names
    column_mapping = {
        "title": "Title",
        "genres": "Genre",
        "description": "Description",
        "actors": "Cast",
        "directors": "Director",
        "alternate_names": "Also Known As",
        "publisher": "Network",
        "aired": "Release Years",
    }
    df.rename(columns=column_mapping, inplace=True)

    # Ensure required columns exist
    for col in ["Title", "Genre", "Description", "Cast"]:
        if col not in df.columns:
            df[col] = ""

    # Clean text fields
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .apply(lambda x: " ".join(str(x).replace("\n", " ").split()))
        )

    print(f"Loaded {len(df)} dramas")
    return df


def create_weighted_content(row: pd.Series, weights: Dict[str, float] = None) -> str:
    """
    Create weighted content string for embedding.

    Weights determine how much each field contributes to the final embedding.
    Higher weight = field is repeated more times = more influence on embedding.
    """
    if weights is None:
        weights = {
            "Title": 3.0,  # Title is most important
            "Genre": 2.0,  # Genre is very important for discovery
            "Cast": 1.5,  # Actors are important
            "Description": 1.0,  # Description provides context
            "keywords": 1.5,  # Keywords capture themes
            "Director": 0.5,  # Less weight on director
        }

    parts = []
    for field, weight in weights.items():
        if field in row and str(row[field]).strip():
            text = str(row[field]).strip()
            # Repeat text based on weight (integer times)
            repeat_times = max(1, int(weight))
            parts.extend([text] * repeat_times)

    return " ".join(parts)


def create_genre_focused_content(row: pd.Series) -> str:
    """Create content focused on genre for genre-based search."""
    genre = str(row.get("Genre", ""))
    title = str(row.get("Title", ""))
    description = str(row.get("Description", ""))[:200]  # First 200 chars

    # Repeat genre to give it more weight
    return f"{genre} {genre} {genre} {title} {description}"


def create_actor_focused_content(row: pd.Series) -> str:
    """Create content focused on cast for actor-based search."""
    cast = str(row.get("Cast", ""))
    title = str(row.get("Title", ""))

    # Repeat cast to give it more weight
    return f"{cast} {cast} {cast} {title}"


def create_theme_embeddings(
    df: pd.DataFrame, encoder: SentenceTransformer
) -> Tuple[np.ndarray, Dict]:
    """
    Create theme-based embeddings by tagging dramas with themes.

    Returns:
        theme_embeddings: Array of theme embeddings for each drama
        theme_assignments: Dict mapping drama index to themes
    """
    print("\nCreating theme-based embeddings...")

    theme_assignments = {}

    for idx, row in df.iterrows():
        title = str(row.get("Title", "")).lower()
        desc = str(row.get("Description", "")).lower()
        keywords = str(row.get("keywords", "")).lower()
        combined = f"{title} {desc} {keywords}"

        assigned_themes = []
        for theme_name, theme_data in THEME_DEFINITIONS.items():
            # Check if drama matches theme keywords
            if any(kw in combined for kw in theme_data["keywords"]):
                assigned_themes.append(theme_name)
            # Check if drama is in known dramas list
            if any(known.lower() in title for known in theme_data["known_dramas"]):
                if theme_name not in assigned_themes:
                    assigned_themes.append(theme_name)

        if assigned_themes:
            theme_assignments[idx] = assigned_themes

    print(f"Assigned themes to {len(theme_assignments)} dramas")

    # Create theme description texts
    theme_texts = []
    for idx in range(len(df)):
        if idx in theme_assignments:
            themes = theme_assignments[idx]
            # Combine theme descriptions
            theme_desc = " ".join([THEME_DEFINITIONS[t]["description"] for t in themes])
            theme_texts.append(theme_desc)
        else:
            theme_texts.append("")

    # Encode theme texts
    theme_embeddings = encoder.encode(
        theme_texts, convert_to_numpy=True, show_progress_bar=True
    )

    return theme_embeddings, theme_assignments


def build_multi_index(
    df: pd.DataFrame, encoder: SentenceTransformer, output_dir: str
) -> Dict[str, str]:
    """
    Build multiple FAISS indices for different search types.

    Creates:
    1. main_index - General purpose with weighted content
    2. genre_index - Genre-focused for genre browsing
    3. actor_index - Actor-focused for actor search
    4. theme_index - Theme-focused for theme search
    """
    os.makedirs(output_dir, exist_ok=True)
    indices = {}

    # Prepare metadata
    metadata = df.to_dict("records")

    # === 1. Main Index (Weighted Content) ===
    print("\n=== Building Main Index ===")
    main_contents = [create_weighted_content(row) for _, row in df.iterrows()]
    main_embeddings = encoder.encode(
        main_contents, convert_to_numpy=True, show_progress_bar=True
    )
    faiss.normalize_L2(main_embeddings)

    dim = main_embeddings.shape[1]
    main_index = faiss.IndexFlatIP(dim)
    main_index.add(main_embeddings)

    faiss.write_index(main_index, os.path.join(output_dir, "index.faiss"))
    indices["main"] = "index.faiss"
    print(f"Main index: {main_index.ntotal} vectors")

    # === 2. Genre Index ===
    print("\n=== Building Genre Index ===")
    genre_contents = [create_genre_focused_content(row) for _, row in df.iterrows()]
    genre_embeddings = encoder.encode(
        genre_contents, convert_to_numpy=True, show_progress_bar=True
    )
    faiss.normalize_L2(genre_embeddings)

    genre_index = faiss.IndexFlatIP(dim)
    genre_index.add(genre_embeddings)

    faiss.write_index(genre_index, os.path.join(output_dir, "genre_index.faiss"))
    indices["genre"] = "genre_index.faiss"
    print(f"Genre index: {genre_index.ntotal} vectors")

    # === 3. Actor Index ===
    print("\n=== Building Actor Index ===")
    actor_contents = [create_actor_focused_content(row) for _, row in df.iterrows()]
    actor_embeddings = encoder.encode(
        actor_contents, convert_to_numpy=True, show_progress_bar=True
    )
    faiss.normalize_L2(actor_embeddings)

    actor_index = faiss.IndexFlatIP(dim)
    actor_index.add(actor_embeddings)

    faiss.write_index(actor_index, os.path.join(output_dir, "actor_index.faiss"))
    indices["actor"] = "actor_index.faiss"
    print(f"Actor index: {actor_index.ntotal} vectors")

    # === 4. Theme Index ===
    print("\n=== Building Theme Index ===")
    theme_embeddings, theme_assignments = create_theme_embeddings(df, encoder)
    faiss.normalize_L2(theme_embeddings)

    theme_index = faiss.IndexFlatIP(dim)
    theme_index.add(theme_embeddings)

    faiss.write_index(theme_index, os.path.join(output_dir, "theme_index.faiss"))
    indices["theme"] = "theme_index.faiss"
    print(f"Theme index: {theme_index.ntotal} vectors")

    # === Save Metadata ===
    # Add theme assignments to metadata
    for idx, themes in theme_assignments.items():
        metadata[idx]["themes"] = themes

    # Save main metadata
    with open(os.path.join(output_dir, "meta.pkl"), "wb") as f:
        pickle.dump(metadata, f)

    # Save theme definitions
    with open(
        os.path.join(output_dir, "theme_definitions.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(THEME_DEFINITIONS, f, indent=2, ensure_ascii=False)

    # Save theme assignments
    with open(
        os.path.join(output_dir, "theme_assignments.json"), "w", encoding="utf-8"
    ) as f:
        json.dump({str(k): v for k, v in theme_assignments.items()}, f, indent=2)

    # Save genre synonyms
    with open(
        os.path.join(output_dir, "genre_synonyms.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(GENRE_SYNONYMS, f, indent=2)

    # Save index manifest
    with open(os.path.join(output_dir, "index_manifest.json"), "w") as f:
        json.dump(
            {
                "indices": indices,
                "embedding_dim": dim,
                "num_dramas": len(df),
                "model_used": encoder.get_sentence_embedding_dimension(),
            },
            f,
            indent=2,
        )

    print(f"\n✅ All indices saved to {output_dir}")
    return indices


def get_encoder(model_dir: str, base_model: str) -> SentenceTransformer:
    """Load the best available encoder model."""
    # Check for fine-tuned model
    finetuned_path = os.path.join(model_dir, "sbert-finetuned-full")
    if os.path.exists(finetuned_path):
        print(f"Using fine-tuned model: {finetuned_path}")
        return SentenceTransformer(finetuned_path)

    # Check for any fine-tuned model
    for name in os.listdir(model_dir):
        if name.startswith("sbert-finetuned") and os.path.isdir(
            os.path.join(model_dir, name)
        ):
            path = os.path.join(model_dir, name)
            print(f"Using fine-tuned model: {path}")
            return SentenceTransformer(path)

    # Use base model
    print(f"Using base model: {base_model}")
    return SentenceTransformer(base_model)


def main():
    parser = argparse.ArgumentParser(description="Build enhanced FAISS indices")
    parser.add_argument(
        "--mode",
        choices=["full", "themes-only", "genre-only"],
        default="full",
        help="Build mode",
    )
    parser.add_argument("--data", default=DATA_PATH, help="Path to dataset")
    parser.add_argument("--output", default=INDEX_DIR, help="Output directory")
    args = parser.parse_args()

    # Load dataset
    df = load_dataset(args.data)

    # Load encoder
    encoder = get_encoder(MODEL_DIR, BASE_MODEL)

    if args.mode == "full":
        # Build all indices
        build_multi_index(df, encoder, args.output)
    elif args.mode == "themes-only":
        # Only build theme index (faster for testing)
        print("Building theme index only...")
        theme_embeddings, theme_assignments = create_theme_embeddings(df, encoder)
        faiss.normalize_L2(theme_embeddings)

        theme_index = faiss.IndexFlatIP(theme_embeddings.shape[1])
        theme_index.add(theme_embeddings)

        faiss.write_index(theme_index, os.path.join(args.output, "theme_index.faiss"))

        with open(os.path.join(args.output, "theme_assignments.json"), "w") as f:
            json.dump({str(k): v for k, v in theme_assignments.items()}, f, indent=2)

        print(f"Theme index saved to {args.output}")

    print("\n" + "=" * 60)
    print("INDEX BUILD COMPLETE")
    print("=" * 60)
    print(f"\nNext steps:")
    print("1. Update backend/app.py to use multiple indices")
    print("2. Run evaluation: python tests/evaluate_accuracy.py")


if __name__ == "__main__":
    main()
