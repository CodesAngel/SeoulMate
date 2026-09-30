"""
K-Drama Specific Training Data Generator

This script generates training data for fine-tuning sentence transformers
specifically on K-drama content patterns:

1. Title-to-Description pairs (learn drama semantics)
2. Genre-similar pairs (dramas in same genre should be close)
3. Actor-co-occurrence pairs (dramas with same actors)
4. Theme-based pairs (dramas with similar themes)
5. Hard negatives (dramas that look similar but are different)

Usage:
    python generate_training_data.py --output training_data.json --mode full
"""

import os
import argparse
import pandas as pd
import numpy as np
import json
import random
from collections import defaultdict
from typing import List, Dict, Tuple, Iterator
from itertools import combinations, islice
import gc

# ======================================================
# Configuration (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "kdrama_dataset.csv")
OUTPUT_DIR = os.path.join(TRAINING_ROOT, "training_data")

# Theme definitions (same as enhanced_index_builder.py)
THEME_DEFINITIONS = {
    "time_travel": {
        "keywords": ["time travel", "time slip", "time loop", "past life", "future"],
        "known_dramas": [
            "Signal",
            "Twinkling Watermelon",
            "Queen In-Hyun's Man",
            "Nine: Nine Time Travels",
        ],
    },
    "north_korea": {
        "keywords": ["north korea", "north korean", "defector", "dmz", "soldier"],
        "known_dramas": ["Crash Landing on You", "The King 2 Hearts", "Iris"],
    },
    "food_cooking": {
        "keywords": ["restaurant", "chef", "cooking", "food", "culinary", "kitchen"],
        "known_dramas": ["Wok of Love", "Let's Eat", "Mystic Pop-up Bar", "Pasta"],
    },
    "medical": {
        "keywords": ["doctor", "hospital", "medical", "surgery", "nurse"],
        "known_dramas": ["Hospital Playlist", "Dr. Romantic", "Good Doctor"],
    },
    "legal": {
        "keywords": ["lawyer", "attorney", "court", "legal", "prosecutor"],
        "known_dramas": ["Extraordinary Attorney Woo", "Law School", "Vincenzo"],
    },
    "supernatural": {
        "keywords": ["ghost", "supernatural", "spirit", "demon", "goblin", "magic"],
        "known_dramas": ["Goblin", "Hotel Del Luna", "My Love from the Star"],
    },
    "revenge": {
        "keywords": ["revenge", "vengeance", "payback"],
        "known_dramas": ["The Glory", "Penthouse", "Eve"],
    },
}


def load_dataset(path: str) -> pd.DataFrame:
    """Load and preprocess dataset."""
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig")
    df.fillna("", inplace=True)

    # Standardize columns
    column_mapping = {
        "title": "Title",
        "genres": "Genre",
        "description": "Description",
        "actors": "Cast",
        "directors": "Director",
    }
    df.rename(columns=column_mapping, inplace=True)

    for col in ["Title", "Genre", "Description", "Cast"]:
        if col not in df.columns:
            df[col] = ""

    return df


def generate_title_description_pairs(df: pd.DataFrame) -> List[Dict]:
    """
    Generate (title, description) pairs.

    Purpose: Teach model that title and description of same drama are related.
    """
    pairs = []
    for _, row in df.iterrows():
        title = str(row["Title"]).strip()
        desc = str(row["Description"]).strip()

        if title and desc and len(desc) > 50:
            pairs.append(
                {
                    "anchor": title,
                    "positive": desc[:500],  # Truncate long descriptions
                    "type": "title_description",
                }
            )

            # Also add genre-enhanced version
            genre = str(row.get("Genre", ""))
            if genre:
                pairs.append(
                    {
                        "anchor": f"{title} {genre}",
                        "positive": desc[:500],
                        "type": "title_genre_description",
                    }
                )

    print(f"Generated {len(pairs)} title-description pairs")
    return pairs


def sample_combinations(items: List, n: int, max_samples: int) -> List[tuple]:
    """
    Memory-efficient sampling from combinations.
    Instead of materializing all combinations, sample indices.
    """
    if len(items) < 2:
        return []

    total_combinations = len(items) * (len(items) - 1) // 2

    if total_combinations <= max_samples:
        # Small enough to enumerate
        return list(combinations(items, n))

    # Sample random pairs by indices
    sampled = set()
    attempts = 0
    max_attempts = max_samples * 3

    while len(sampled) < max_samples and attempts < max_attempts:
        i = random.randint(0, len(items) - 1)
        j = random.randint(0, len(items) - 1)
        if i != j:
            pair = (min(i, j), max(i, j))
            if pair not in sampled:
                sampled.add(pair)
        attempts += 1

    return [(items[i], items[j]) for i, j in sampled]


def generate_genre_pairs(df: pd.DataFrame, max_pairs_per_genre: int = 50) -> List[Dict]:
    """
    Generate pairs of dramas from the same genre.

    Purpose: Teach model that dramas with same genre are related.
    """
    # Group dramas by genre
    genre_dramas = defaultdict(list)

    for _, row in df.iterrows():
        genres = str(row.get("Genre", "")).split(",")
        title = str(row["Title"]).strip()

        for genre in genres:
            genre = genre.strip()
            if genre and title:
                genre_dramas[genre].append(title)

    pairs = []
    for genre, titles in genre_dramas.items():
        if len(titles) < 2:
            continue

        # Memory-efficient sampling
        sampled = sample_combinations(titles, 2, max_pairs_per_genre)

        for t1, t2 in sampled:
            pairs.append(
                {"anchor": t1, "positive": t2, "type": "same_genre", "genre": genre}
            )

    print(f"Generated {len(pairs)} genre-based pairs from {len(genre_dramas)} genres")
    gc.collect()  # Free memory
    return pairs


def generate_actor_pairs(
    df: pd.DataFrame, max_pairs_per_actor: int = 20, max_total: int = 5000
) -> List[Dict]:
    """
    Generate pairs of dramas with the same actor.

    Purpose: Teach model that dramas with same actor are related when searching by actor.
    """
    # Group dramas by actor
    actor_dramas = defaultdict(list)

    for _, row in df.iterrows():
        cast = str(row.get("Cast", ""))
        title = str(row["Title"]).strip()

        # Split cast and clean
        actors = [a.strip() for a in cast.split(",")]
        for actor in actors:
            if actor and len(actor) > 2 and title:
                actor_dramas[actor].append(title)

    pairs = []

    # Sort actors by number of dramas (prioritize prolific actors)
    sorted_actors = sorted(actor_dramas.items(), key=lambda x: len(x[1]), reverse=True)

    for actor, titles in sorted_actors:
        if len(pairs) >= max_total:
            break

        if len(titles) < 2:
            continue

        # Only use actors with 2-10 dramas (too many = too general)
        if len(titles) > 10:
            titles = random.sample(titles, 10)

        # Create limited pairs using sample_combinations
        sampled_pairs = sample_combinations(titles, 2, max_pairs_per_actor)

        for t1, t2 in sampled_pairs[:max_pairs_per_actor]:
            pairs.append(
                {"anchor": f"{actor} dramas", "positive": t1, "type": "actor_drama"}
            )
            if len(pairs) < max_total:
                pairs.append(
                    {
                        "anchor": f"dramas with {actor}",
                        "positive": t2,
                        "type": "actor_drama",
                    }
                )

    print(f"Generated {len(pairs)} actor-based pairs from {len(actor_dramas)} actors")
    gc.collect()  # Free memory
    return pairs


def generate_theme_pairs(df: pd.DataFrame) -> List[Dict]:
    """
    Generate theme-based training pairs.

    Purpose: Teach model to associate theme queries with relevant dramas.
    """
    pairs = []

    for theme_name, theme_data in THEME_DEFINITIONS.items():
        # Find dramas matching this theme
        matching_dramas = []

        for _, row in df.iterrows():
            title = str(row["Title"]).strip().lower()
            desc = str(row.get("Description", "")).lower()
            keywords = str(row.get("keywords", "")).lower()
            combined = f"{title} {desc} {keywords}"

            # Check if drama matches theme
            if any(kw in combined for kw in theme_data["keywords"]):
                matching_dramas.append(str(row["Title"]).strip())
            elif any(
                known.lower() in title for known in theme_data.get("known_dramas", [])
            ):
                matching_dramas.append(str(row["Title"]).strip())

        # Create pairs for this theme
        theme_query = theme_name.replace("_", " ")
        theme_variants = [
            theme_query,
            f"{theme_query} drama",
            f"{theme_query} kdrama",
            f"korean drama about {theme_query}",
            f"dramas about {theme_query}",
        ]

        for drama_title in matching_dramas[:20]:  # Limit per theme
            for query_variant in theme_variants:
                pairs.append(
                    {
                        "anchor": query_variant,
                        "positive": drama_title,
                        "type": "theme_query",
                        "theme": theme_name,
                    }
                )

    print(f"Generated {len(pairs)} theme-based pairs")
    return pairs


def generate_genre_query_pairs(df: pd.DataFrame) -> List[Dict]:
    """
    Generate genre query training pairs.

    Purpose: Teach model to match "romantic comedy" → actual romantic comedy dramas.
    """
    pairs = []

    genre_queries = {
        "romantic comedy": ["Romance", "Comedy"],
        "romcom": ["Romance", "Comedy"],
        "medical drama": ["Medical", "Drama"],
        "thriller": ["Thriller", "Suspense", "Mystery"],
        "historical": ["Historical", "Period Drama", "Sageuk"],
        "action": ["Action", "Adventure"],
        "horror": ["Horror", "Supernatural"],
        "melodrama": ["Melodrama", "Romance", "Drama"],
        "crime": ["Crime", "Thriller", "Mystery"],
        "fantasy": ["Fantasy", "Supernatural"],
        "school drama": ["School", "Youth", "Coming of Age"],
        "family drama": ["Family", "Life"],
        "legal drama": ["Law", "Legal", "Lawyer"],
    }

    for query, target_genres in genre_queries.items():
        # Find dramas matching ALL target genres
        matching_dramas = []

        for _, row in df.iterrows():
            drama_genres = str(row.get("Genre", "")).lower()
            if all(g.lower() in drama_genres for g in target_genres):
                matching_dramas.append(str(row["Title"]).strip())

        # Create pairs
        query_variants = [
            query,
            f"{query} drama",
            f"{query} kdrama",
            f"best {query}",
            f"good {query}",
        ]

        for drama_title in matching_dramas[:30]:  # Limit per genre
            for q in query_variants:
                pairs.append(
                    {
                        "anchor": q,
                        "positive": drama_title,
                        "type": "genre_query",
                        "query": query,
                    }
                )

    print(f"Generated {len(pairs)} genre query pairs")
    return pairs


def generate_hard_negatives(
    df: pd.DataFrame, all_pairs: List[Dict], max_triplets: int = 5000
) -> List[Dict]:
    """
    Add hard negatives to training data.

    Hard negatives are examples that look similar but should NOT match.
    This teaches the model to distinguish subtle differences.
    """
    # Get all titles for negative sampling
    all_titles = list(df["Title"].astype(str).unique())

    # Create title to genre mapping
    title_to_genre = {}
    for _, row in df.iterrows():
        title_to_genre[str(row["Title"])] = str(row.get("Genre", ""))

    triplets = []

    # Sample pairs to process (don't process all)
    eligible_pairs = [
        p
        for p in all_pairs
        if p["type"] in ["same_genre", "genre_query", "theme_query"]
    ]
    if len(eligible_pairs) > max_triplets:
        eligible_pairs = random.sample(eligible_pairs, max_triplets)

    for pair in eligible_pairs:
        anchor = pair["anchor"]
        positive = pair["positive"]
        positive_genre = title_to_genre.get(positive, "")

        # Find a negative that's in a DIFFERENT genre
        for _ in range(5):  # Try 5 times
            negative = random.choice(all_titles)
            negative_genre = title_to_genre.get(negative, "")

            # Ensure negative is truly different
            if negative != positive and not any(
                g in negative_genre for g in positive_genre.split(",")
            ):
                triplets.append(
                    {
                        "anchor": anchor,
                        "positive": positive,
                        "negative": negative,
                        "type": f"{pair['type']}_triplet",
                    }
                )
                break

    print(f"Generated {len(triplets)} hard negative triplets")
    gc.collect()  # Free memory
    return triplets


def generate_query_variations(df: pd.DataFrame) -> List[Dict]:
    """
    Generate query variation pairs.

    Purpose: Teach model that different ways of asking for same thing are equivalent.
    """
    pairs = []

    # Query variations for popular dramas
    popular_dramas = (
        df.nlargest(100, "rating_value")["Title"].tolist()
        if "rating_value" in df.columns
        else []
    )

    for title in popular_dramas[:50]:
        variations = [
            title,
            title.lower(),
            title.upper(),
            f"drama {title}",
            f"{title} kdrama",
            f"korean drama {title}",
        ]

        # Pair each variation with the original title
        for var in variations[1:]:
            pairs.append({"anchor": var, "positive": title, "type": "query_variation"})

    print(f"Generated {len(pairs)} query variation pairs")
    return pairs


def save_training_data(pairs: List[Dict], triplets: List[Dict], output_dir: str):
    """Save training data in multiple formats."""
    os.makedirs(output_dir, exist_ok=True)

    # Save as JSON (full data)
    with open(
        os.path.join(output_dir, "training_pairs.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(pairs, f, indent=2, ensure_ascii=False)

    with open(
        os.path.join(output_dir, "training_triplets.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(triplets, f, indent=2, ensure_ascii=False)

    # Save as sentence-transformers format (InputExample compatible)
    st_pairs = []
    for p in pairs:
        st_pairs.append({"texts": [p["anchor"], p["positive"]], "label": 1.0})

    with open(os.path.join(output_dir, "st_pairs.json"), "w", encoding="utf-8") as f:
        json.dump(st_pairs, f, indent=2, ensure_ascii=False)

    st_triplets = []
    for t in triplets:
        st_triplets.append({"texts": [t["anchor"], t["positive"], t["negative"]]})

    with open(os.path.join(output_dir, "st_triplets.json"), "w", encoding="utf-8") as f:
        json.dump(st_triplets, f, indent=2, ensure_ascii=False)

    # Save statistics
    stats = {
        "total_pairs": len(pairs),
        "total_triplets": len(triplets),
        "pair_types": defaultdict(int),
        "triplet_types": defaultdict(int),
    }
    for p in pairs:
        stats["pair_types"][p["type"]] += 1
    for t in triplets:
        stats["triplet_types"][t["type"]] += 1

    stats["pair_types"] = dict(stats["pair_types"])
    stats["triplet_types"] = dict(stats["triplet_types"])

    with open(os.path.join(output_dir, "training_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\n✅ Training data saved to {output_dir}")
    print(f"   - {len(pairs)} pairs")
    print(f"   - {len(triplets)} triplets")
    print(f"\nPair type breakdown:")
    for ptype, count in stats["pair_types"].items():
        print(f"   {ptype}: {count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=DATA_PATH, help="Path to dataset")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "--mode", choices=["full", "pairs-only", "triplets-only"], default="full"
    )
    args = parser.parse_args()

    # Load dataset
    df = load_dataset(args.data)
    print(f"Loaded {len(df)} dramas")

    # Generate all pair types
    all_pairs = []

    print("\n=== Generating Training Data ===")

    # 1. Title-Description pairs
    all_pairs.extend(generate_title_description_pairs(df))

    # 2. Genre pairs
    all_pairs.extend(generate_genre_pairs(df))

    # 3. Actor pairs
    all_pairs.extend(generate_actor_pairs(df))

    # 4. Theme pairs
    all_pairs.extend(generate_theme_pairs(df))

    # 5. Genre query pairs
    all_pairs.extend(generate_genre_query_pairs(df))

    # 6. Query variations
    all_pairs.extend(generate_query_variations(df))

    # Generate triplets with hard negatives
    triplets = []
    if args.mode != "pairs-only":
        triplets = generate_hard_negatives(df, all_pairs)

    # Save everything
    save_training_data(all_pairs, triplets, args.output)

    print("\n" + "=" * 60)
    print("TRAINING DATA GENERATION COMPLETE")
    print("=" * 60)
    print(f"\nNext steps:")
    print("1. Fine-tune model: python fine_tune_kdrama_sbert.py")
    print("2. Rebuild index: python enhanced_index_builder.py")


if __name__ == "__main__":
    main()
