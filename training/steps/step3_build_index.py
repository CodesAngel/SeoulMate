"""Builds the FAISS index and metadata the live backend actually loads.

Simpler, single-index builder — this (not future_multi_index_builder.py) is
what's actually deployed in production. Promoted to be the pipeline's step 3
as of 2026-09-30; train_pipeline.py calls it with `--mode full`, which this
script accepts but ignores (it only ever does one thing: a full rebuild).
"""

import argparse
import os
import pandas as pd
import pickle
import faiss
from sentence_transformers import SentenceTransformer

# Accepted for train_pipeline.py compatibility; this script always does a
# full rebuild regardless of the value passed.
_parser = argparse.ArgumentParser()
_parser.add_argument(
    "--mode",
    default="full",
    help="Accepted for pipeline compatibility; this script always does a full rebuild.",
)
_parser.parse_args()

# ======================================================
# 1. Config (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "kdrama_dataset.csv")
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
MODEL_DIR = os.path.join(TRAINING_ROOT, "models")
INDEX_DIR = os.path.join(TRAINING_ROOT, "faiss_index")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# If you've fine-tuned a local SBERT model, save it to MODEL_DIR/sbert-finetuned*
# The script will prefer any local fine-tuned model automatically when present.
FINETUNED_PREFIX = "sbert-finetuned"

# ======================================================
# 2. Load and Prepare Dataset
# ======================================================
print("Loading dataset...")
if DATA_PATH.lower().endswith((".xlsx", ".xls")):
    df = pd.read_excel(DATA_PATH)
else:
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
df.fillna("", inplace=True)

# Map column names to standardized format
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


# Normalize text fields
def clean_text(text):
    return " ".join(str(text).replace("\n", " ").replace("\r", " ").split())


for col in df.columns:
    df[col] = df[col].astype(str).apply(clean_text)

# Create unified text field for embeddings
text_features = [
    "Title",
    "Genre",
    "Description",
    "Cast",
    "Director",
    "Also Known As",
    "Network",
    "Release Years",
    "keywords",
]
available_features = [col for col in text_features if col in df.columns]
df["content"] = df[available_features].astype(str).agg(" ".join, axis=1)

# ======================================================
# 3. Load SentenceTransformer Model
# ======================================================
print("Loading SentenceTransformer model...")
# Look for any local fine-tuned folder starting with 'sbert-finetuned'
# Prefer 'sbert-finetuned-full' if exists, else use most recent
selected_local = None
try:
    candidates = [
        name
        for name in os.listdir(MODEL_DIR)
        if name.startswith(FINETUNED_PREFIX)
        and os.path.isdir(os.path.join(MODEL_DIR, name))
    ]

    if candidates:
        # Prefer 'sbert-finetuned-full' if available
        if "sbert-finetuned-full" in candidates:
            selected_local = os.path.join(MODEL_DIR, "sbert-finetuned-full")
            print(f"Found fine-tuned model: sbert-finetuned-full (preferred)")
        else:
            # Sort by modification time (most recent first)
            candidates_with_time = [
                (name, os.path.getmtime(os.path.join(MODEL_DIR, name)))
                for name in candidates
            ]
            candidates_with_time.sort(key=lambda x: x[1], reverse=True)
            most_recent = candidates_with_time[0][0]
            selected_local = os.path.join(MODEL_DIR, most_recent)
            print(f"Found fine-tuned model: {most_recent} (most recent)")
except Exception:
    selected_local = None

if selected_local:
    print(f"Using local fine-tuned model at: {selected_local}")
    model = SentenceTransformer(selected_local)
else:
    # Use pretrained model name from Hugging Face (will download to cache_folder)
    print(
        f"No fine-tuned model found. Using pretrained model '{MODEL_NAME}' (cache folder: {MODEL_DIR})"
    )
    model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_DIR)

print("Model loaded successfully!")

# ======================================================
# 4. Generate Embeddings
# ======================================================
print("Generating embeddings (this may take a few minutes)...")
# Use a smaller batch size by default to be CPU-friendly; increase if you have more RAM/GPUs
batch_size = 16
embeddings = model.encode(
    df["content"].tolist(),
    show_progress_bar=True,
    convert_to_numpy=True,
    batch_size=batch_size,
)

# ======================================================
# 5. Build FAISS Index
# ======================================================
dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity
faiss.normalize_L2(embeddings)
index.add(embeddings)

print(f"FAISS index built successfully with {index.ntotal} items.")

# ======================================================
# 6. Save Index and Metadata
# ======================================================
faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))

# Save relevant metadata (keep it clean for inference)
meta_cols = [
    "Title",
    "Genre",
    "Description",
    "Cast",
    "Director",
    "Network",
    "Release Years",
    "Also Known As",
    "rating_value",
    "episodes",
    "aired",
    "keywords",
]
meta_cols = [c for c in meta_cols if c in df.columns]

metadata = df[meta_cols].to_dict(orient="records")

with open(os.path.join(INDEX_DIR, "meta.pkl"), "wb") as f:
    pickle.dump(metadata, f)

print(f"Index and metadata saved in: {INDEX_DIR}")
print("All done! Your FAISS index is ready for recommendations.")
