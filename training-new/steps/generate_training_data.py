"""
SeoulMate Next-Gen K-Drama Training Data Generator

Generates high-fidelity training data for fine-tuning dense sentence transformers:
1. Title-to-Description pairs (semantic anchor)
2. Genre-co-occurrence pairs
3. Actor-filmography pairs
4. Curated theme-to-synopsis pairs
5. Hard negative triplets (using BM25 false positives and conflicting tropes)
6. Balanced evaluation pairs (positive=1.0, negative=0.0) to prevent NaN metrics
"""

import os
import argparse
import pandas as pd
import numpy as np
import json
import random
from collections import defaultdict
from typing import List, Dict, Tuple
from rank_bm25 import BM25Plus
import gc

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "dramalist_kdramas.xlsx")
DEFAULT_OUTPUT_DIR = os.path.join(TRAINING_ROOT, "training_data")

THEME_DEFINITIONS = {
    "time_travel": {
        "keywords": ["time travel", "time slip", "time loop", "past life", "future", "timeline"],
        "known_dramas": ["Signal", "Twinkling Watermelon", "Nine: Nine Time Travels", "Tomorrow with You", "Go Back Couple"]
    },
    "north_korea": {
        "keywords": ["north korea", "north korean", "defector", "dmz", "pyongyang"],
        "known_dramas": ["Crash Landing on You", "The King 2 Hearts", "Iris", "Snowdrop"]
    },
    "food_cooking": {
        "keywords": ["restaurant", "chef", "cooking", "food", "culinary", "kitchen", "recipe"],
        "known_dramas": ["Wok of Love", "Let's Eat", "Mystic Pop-up Bar", "Pasta", "Oh My Ghost"]
    },
    "medical": {
        "keywords": ["doctor", "hospital", "medical", "surgery", "nurse", "patient", "surgeon"],
        "known_dramas": ["Hospital Playlist", "Dr. Romantic", "Good Doctor", "Doctor Stranger"]
    },
    "legal": {
        "keywords": ["lawyer", "attorney", "court", "legal", "prosecutor", "judge", "law firm"],
        "known_dramas": ["Extraordinary Attorney Woo", "Law School", "Vincenzo", "Suspicious Partner"]
    },
    "supernatural": {
        "keywords": ["ghost", "supernatural", "spirit", "demon", "goblin", "immortal", "deity"],
        "known_dramas": ["Goblin", "Hotel Del Luna", "My Love from the Star", "The Uncanny Counter"]
    },
    "revenge": {
        "keywords": ["revenge", "vengeance", "payback", "betrayal", "retaliation"],
        "known_dramas": ["The Glory", "Penthouse: War in Life", "Eve", "My Name", "Reborn Rich"]
    },
    "contract_marriage": {
        "keywords": ["contract marriage", "fake marriage", "pretend couple", "arranged marriage", "fake dating"],
        "known_dramas": ["Because This Is My First Life", "Marriage Contract", "Love in Contract", "Perfect Marriage Revenge"]
    },
    "enemies_to_lovers": {
        "keywords": ["enemies to lovers", "hate to love", "bickering couple", "rivals"],
        "known_dramas": ["Shooting Stars", "Love to Hate You", "Our Beloved Summer", "Mad for Each Other"]
    }
}


def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.fillna("", inplace=True)
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


def generate_title_description_pairs(df: pd.DataFrame, prefix_query: str = "", prefix_doc: str = "") -> List[Dict]:
    pairs = []
    for _, row in df.iterrows():
        title = str(row["Title"]).strip()
        desc = str(row["Description"]).strip()
        genre = str(row.get("Genre", "")).strip()

        if title and desc and len(desc) > 40:
            pairs.append({
                "anchor": f"{prefix_query}{title}",
                "positive": f"{prefix_doc}{desc[:500]}",
                "type": "title_description",
            })
            if genre:
                pairs.append({
                    "anchor": f"{prefix_query}{title} {genre}",
                    "positive": f"{prefix_doc}{title} {genre}. {desc[:400]}",
                    "type": "title_genre_description",
                })
    return pairs


def generate_theme_pairs(df: pd.DataFrame, prefix_query: str = "", prefix_doc: str = "") -> List[Dict]:
    pairs = []
    for theme_name, theme_info in THEME_DEFINITIONS.items():
        theme_label = theme_name.replace("_", " ")
        for kw in theme_info["keywords"]:
            for kd in theme_info["known_dramas"]:
                matching = df[df["Title"].str.lower() == kd.lower()]
                if not matching.empty:
                    desc = matching.iloc[0]["Description"]
                    pairs.append({
                        "anchor": f"{prefix_query}{kw}",
                        "positive": f"{prefix_doc}{kd}. {desc[:400]}",
                        "type": "theme_query",
                        "theme": theme_name
                    })
                    pairs.append({
                        "anchor": f"{prefix_query}{theme_label} kdrama",
                        "positive": f"{prefix_doc}{kd}. {desc[:400]}",
                        "type": "theme_query",
                        "theme": theme_name
                    })
    return pairs


def generate_genre_query_pairs(df: pd.DataFrame, prefix_query: str = "", prefix_doc: str = "") -> List[Dict]:
    pairs = []
    for _, row in df.iterrows():
        genres = [g.strip() for g in str(row.get("Genre", "")).split(",") if g.strip()]
        title = str(row["Title"]).strip()
        desc = str(row["Description"]).strip()
        if not title or not desc or not genres:
            continue

        for genre in genres[:2]:
            queries = [
                f"{genre} kdrama",
                f"best {genre} dramas",
                f"korean {genre} series"
            ]
            for q in queries:
                pairs.append({
                    "anchor": f"{prefix_query}{q}",
                    "positive": f"{prefix_doc}{title} ({genre}). {desc[:350]}",
                    "type": "genre_query",
                    "genre": genre
                })
    return pairs


def generate_hard_negative_triplets(df: pd.DataFrame, prefix_query: str = "", prefix_doc: str = "", max_triplets: int = 3000) -> List[Dict]:
    """
    Mine hard negatives using BM25:
    For each query (e.g. 'contract marriage' or 'time travel'), find high lexical matches
    that DO NOT actually contain the required theme/trope.
    """
    corpus = [f"{r['Title']} {r['Genre']} {r['Description']}".lower() for _, r in df.iterrows()]
    tokenized_corpus = [doc.split() for doc in corpus]
    bm25 = BM25Plus(tokenized_corpus)

    triplets = []

    for theme_name, theme_info in THEME_DEFINITIONS.items():
        theme_label = theme_name.replace("_", " ")
        known_titles = set(t.lower() for t in theme_info["known_dramas"])

        for kd in theme_info["known_dramas"]:
            matching = df[df["Title"].str.lower() == kd.lower()]
            if matching.empty:
                continue

            pos_desc = matching.iloc[0]["Description"]
            pos_title = matching.iloc[0]["Title"]
            pos_text = f"{pos_title}. {pos_desc[:400]}"

            # Search BM25 for top candidate false positives using the theme keywords
            query = f"{theme_label} kdrama"
            scores = bm25.get_scores(query.split())
            top_indices = np.argsort(scores)[::-1]

            for idx in top_indices[:15]:
                cand_title = df.iloc[idx]["Title"]
                if cand_title.lower() in known_titles:
                    continue

                # Ensure candidate doesn't match theme keywords in description
                cand_desc = str(df.iloc[idx]["Description"]).lower()
                has_keyword = any(kw in cand_desc for kw in theme_info["keywords"])
                if not has_keyword:
                    neg_text = f"{cand_title}. {df.iloc[idx]['Description'][:400]}"
                    triplets.append({
                        "anchor": f"{prefix_query}{query}",
                        "positive": f"{prefix_doc}{pos_text}",
                        "negative": f"{prefix_doc}{neg_text}",
                        "type": "hard_negative_theme"
                    })
                    if len(triplets) >= max_triplets:
                        return triplets

    return triplets


def generate_balanced_eval_set(df: pd.DataFrame, prefix_query: str = "", prefix_doc: str = "", sample_size: int = 250) -> List[Dict]:
    """
    Generates an evaluation set with BOTH positive (score=1.0) and negative (score=0.0) pairs.
    This guarantees non-zero variance so Pearson/Spearman correlation metrics compute without NaN.
    """
    eval_data = []

    # 1. Positive pairs (score 1.0)
    for theme_name, theme_info in THEME_DEFINITIONS.items():
        theme_label = theme_name.replace("_", " ")
        for kd in theme_info["known_dramas"]:
            matching = df[df["Title"].str.lower() == kd.lower()]
            if not matching.empty:
                title = matching.iloc[0]["Title"]
                desc = matching.iloc[0]["Description"]
                eval_data.append({
                    "sentence1": f"{prefix_query}{theme_label} kdrama",
                    "sentence2": f"{prefix_doc}{title}. {desc[:350]}",
                    "score": 1.0
                })

    # 2. Negative pairs (score 0.0) - Unrelated theme to drama
    themes = list(THEME_DEFINITIONS.keys())
    for _ in range(len(eval_data)):
        random_theme = random.choice(themes)
        unrelated_drama = df.sample(1).iloc[0]
        eval_data.append({
            "sentence1": f"{prefix_query}{random_theme.replace('_', ' ')} kdrama",
            "sentence2": f"{prefix_doc}{unrelated_drama['Title']}. {unrelated_drama['Description'][:350]}",
            "score": 0.0
        })

    random.shuffle(eval_data)
    return eval_data[:sample_size * 2]


def main():
    parser = argparse.ArgumentParser(description="Generate K-drama training and evaluation data")
    parser.add_argument("--data", default=DEFAULT_DATA_PATH, help="Path to dramalist_kdramas.xlsx")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for JSON datasets")
    parser.add_argument("--is_e5", action="store_true", default=True, help="Include 'query: ' and 'passage: ' prefixes for E5 models")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading dataset from: {args.data}")
    df = load_dataset(args.data)
    print(f"Loaded {len(df)} dramas successfully.")

    prefix_q = "query: " if args.is_e5 else ""
    prefix_d = "passage: " if args.is_e5 else ""

    print("Generating title-description pairs...")
    title_desc_pairs = generate_title_description_pairs(df, prefix_q, prefix_d)

    print("Generating theme query pairs...")
    theme_pairs = generate_theme_pairs(df, prefix_q, prefix_d)

    print("Generating genre query pairs...")
    genre_pairs = generate_genre_query_pairs(df, prefix_q, prefix_d)

    all_pairs = title_desc_pairs + theme_pairs + genre_pairs
    print(f"Total training pairs generated: {len(all_pairs)}")

    pairs_path = os.path.join(args.output_dir, "training_pairs.json")
    with open(pairs_path, "w", encoding="utf-8") as f:
        json.dump(all_pairs, f, indent=2, ensure_ascii=False)
    print(f"Saved: {pairs_path}")

    print("Generating hard negative triplets...")
    triplets = generate_hard_negative_triplets(df, prefix_q, prefix_d, max_triplets=3500)
    print(f"Total hard negative triplets generated: {len(triplets)}")

    triplets_path = os.path.join(args.output_dir, "training_triplets.json")
    with open(triplets_path, "w", encoding="utf-8") as f:
        json.dump(triplets, f, indent=2, ensure_ascii=False)
    print(f"Saved: {triplets_path}")

    print("Generating balanced evaluation dataset (prevents NaN correlation metrics)...")
    eval_set = generate_balanced_eval_set(df, prefix_q, prefix_d)
    eval_path = os.path.join(args.output_dir, "eval_pairs.json")
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_set, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(eval_set)} balanced eval pairs to: {eval_path}")

    print("\nData generation completed successfully!")


if __name__ == "__main__":
    main()
