"""
SeoulMate Enhanced FAISS Index Builder

Encodes drama metadata into specialized 768-dimensional FAISS vector indexes:
1. Main index: Title + Genre + Description + Cast
2. Genre index: Genre-focused weighted representations
3. Actor index: Actor/Cast-focused representations
4. Theme index: Thematic & trope-focused representations
"""

import os
import argparse
import pandas as pd
import numpy as np
import pickle
import faiss
import json
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "dramalist_kdramas.xlsx")
DEFAULT_MODEL_DIR = os.path.join(TRAINING_ROOT, "models", "e5-kdrama-finetuned")
FALLBACK_BASE_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_INDEX_DIR = os.path.join(TRAINING_ROOT, "faiss_index")

THEME_KEYWORDS = {
    "time_travel": ["time travel", "time slip", "time loop", "past life", "future"],
    "north_korea": ["north korea", "north korean", "defector", "dmz"],
    "food_cooking": ["restaurant", "chef", "cooking", "food", "culinary", "kitchen"],
    "medical": ["doctor", "hospital", "medical", "surgery", "nurse"],
    "legal": ["lawyer", "attorney", "court", "legal", "prosecutor", "judge"],
    "supernatural": ["ghost", "supernatural", "spirit", "demon", "goblin", "magic"],
    "revenge": ["revenge", "vengeance", "payback", "betrayal"],
    "contract_marriage": ["contract marriage", "fake marriage", "pretend couple", "arranged marriage"],
    "enemies_to_lovers": ["enemies to lovers", "hate to love", "bickering couple"]
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


def build_faiss_l2_norm(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Builds an Inner Product index on L2-normalized vectors (equivalent to Cosine Similarity)."""
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norm[norm == 0] = 1e-12
    normalized = (embeddings / norm).astype("float32")
    dim = normalized.shape[1]
    idx = faiss.IndexFlatIP(dim)
    idx.add(normalized)
    return idx


def main():
    parser = argparse.ArgumentParser(description="Build FAISS vector indexes")
    parser.add_argument("--data", default=DEFAULT_DATA_PATH, help="Path to dramalist_kdramas.xlsx")
    parser.add_argument("--model", default=DEFAULT_MODEL_DIR, help="Path to fine-tuned model (or base model name)")
    parser.add_argument("--output_dir", default=DEFAULT_INDEX_DIR, help="Output index directory")
    parser.add_argument("--batch_size", type=int, default=64, help="Inference batch size")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Load Model
    model_to_load = args.model if os.path.exists(args.model) else FALLBACK_BASE_MODEL
    print(f"Loading encoder model from: {model_to_load}")
    model = SentenceTransformer(model_to_load)

    # Check prefix requirement
    is_e5 = "e5" in model_to_load.lower()
    doc_prefix = "passage: " if is_e5 else ""

    # 2. Load Dataset
    print(f"Loading dataset: {args.data}")
    df = load_dataset(args.data)
    num_dramas = len(df)
    print(f"Loaded {num_dramas} dramas.")

    # 3. Prepare Texts
    print("Preparing documents for vector encoding...")
    main_texts = [
        f"{doc_prefix}{r['Title']} {r['Genre']}. {r['Description']} Cast: {r['Cast']}"
        for _, r in df.iterrows()
    ]
    genre_texts = [
        f"{doc_prefix}{r['Title']}. Genres: {r['Genre']}. {r['Description'][:300]}"
        for _, r in df.iterrows()
    ]
    actor_texts = [
        f"{doc_prefix}{r['Title']} starring {r['Cast']}. {r['Genre']}"
        for _, r in df.iterrows()
    ]
    theme_texts = []
    for _, r in df.iterrows():
        desc_lower = str(r["Description"]).lower()
        matched_themes = [k for k, kws in THEME_KEYWORDS.items() if any(w in desc_lower for w in kws)]
        theme_str = ", ".join(matched_themes).replace("_", " ")
        theme_texts.append(f"{doc_prefix}{r['Title']}. Themes: {theme_str}. {r['Description'][:350]}")

    # 4. Compute Embeddings
    print("\nEncoding Main Index...")
    main_embeds = model.encode(main_texts, batch_size=args.batch_size, show_progress_bar=True)
    main_idx = build_faiss_l2_norm(main_embeds)
    faiss.write_index(main_idx, os.path.join(args.output_dir, "index.faiss"))
    print("✓ Main index saved.")

    print("\nEncoding Genre Index...")
    genre_embeds = model.encode(genre_texts, batch_size=args.batch_size, show_progress_bar=True)
    genre_idx = build_faiss_l2_norm(genre_embeds)
    faiss.write_index(genre_idx, os.path.join(args.output_dir, "genre_index.faiss"))
    print("✓ Genre index saved.")

    print("\nEncoding Actor Index...")
    actor_embeds = model.encode(actor_texts, batch_size=args.batch_size, show_progress_bar=True)
    actor_idx = build_faiss_l2_norm(actor_embeds)
    faiss.write_index(actor_idx, os.path.join(args.output_dir, "actor_index.faiss"))
    print("✓ Actor index saved.")

    print("\nEncoding Theme Index...")
    theme_embeds = model.encode(theme_texts, batch_size=args.batch_size, show_progress_bar=True)
    theme_idx = build_faiss_l2_norm(theme_embeds)
    faiss.write_index(theme_idx, os.path.join(args.output_dir, "theme_index.faiss"))
    print("✓ Theme index saved.")

    # 5. Save Metadata
    metadata = df.to_dict(orient="records")
    meta_path = os.path.join(args.output_dir, "meta.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)
    print(f"✓ Metadata saved to: {meta_path}")

    # 6. Save Manifest
    manifest = {
        "indices": {
            "main": "index.faiss",
            "genre": "genre_index.faiss",
            "actor": "actor_index.faiss",
            "theme": "theme_index.faiss"
        },
        "embedding_dim": int(main_embeds.shape[1]),
        "num_dramas": num_dramas,
        "model_used": model_to_load
    }
    manifest_path = os.path.join(args.output_dir, "index_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"✓ Manifest saved to: {manifest_path}")

    print("\nIndex building complete!")


if __name__ == "__main__":
    main()
