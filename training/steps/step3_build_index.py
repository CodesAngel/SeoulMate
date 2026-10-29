"""Builds the FAISS index and metadata the live backend actually loads.

Simpler, single-index builder — this (not future_multi_index_builder.py) is
what's actually deployed in production. Promoted to be the pipeline's step 3
as of 2026-09-30; train_pipeline.py calls it with `--mode full`, which this
script accepts but ignores.

With --reuse <index dir> (an earlier build with its dataset.csv, e.g. the live
release), dramas whose embedding text is unchanged keep their old vector and only
new or changed dramas are encoded. A sample of reused vectors is re-encoded and
compared first; any mismatch (or a different model) falls back to encoding all.
"""

import argparse
import hashlib
import json
import os
from datetime import datetime
import numpy as np
import pandas as pd
import pickle
from urllib.parse import urlparse
import faiss
from sentence_transformers import SentenceTransformer

# --mode is accepted for train_pipeline.py compatibility; this script always does a
# full rebuild regardless of the value passed. --data/--out-dir/--model let an
# unattended update (scripts/update_catalog.py) build a candidate index next to the
# live one and pin the exact bi-encoder the backend loads.
_parser = argparse.ArgumentParser()
_parser.add_argument(
    "--mode",
    default="full",
    help="Accepted for pipeline compatibility; this script always does a full rebuild.",
)
_parser.add_argument("--data", help="Dataset CSV (default: data/final/kdrama_dataset.csv)")
_parser.add_argument("--out-dir", help="Where to write index.faiss and meta.pkl (default: training/faiss_index)")
_parser.add_argument("--model", help="Bi-encoder folder to use (default: auto-select under training/models)")
_parser.add_argument("--reuse", help="Earlier index folder (with dataset.csv) whose vectors are reused for unchanged dramas")
_args = _parser.parse_args()

# Reused vectors must match a fresh encoding at least this closely (cosine).
REUSE_CHECK_SAMPLES = 8
REUSE_MIN_COSINE = 0.9999

# ======================================================
# 1. Config (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DATA_PATH = _args.data or os.path.join(PROJECT_ROOT, "data", "final", "kdrama_dataset.csv")
MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
MODEL_DIR = os.path.join(TRAINING_ROOT, "models")
INDEX_DIR = _args.out_dir or os.path.join(TRAINING_ROOT, "faiss_index")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# If you've fine-tuned a local SBERT model, save it to MODEL_DIR/sbert-finetuned*
# The script will prefer any local fine-tuned model automatically when present.
FINETUNED_PREFIX = "sbert-finetuned"

# ======================================================
# 2. Load and Prepare Dataset
# ======================================================
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

# Fields joined into the text that is embedded
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


# Normalize text fields
def clean_text(text):
    return " ".join(str(text).replace("\n", " ").replace("\r", " ").split())


def load_dataset(path):
    """Read a dataset file and add the 'content' column that gets embedded."""
    if path.lower().endswith((".xlsx", ".xls")):
        frame = pd.read_excel(path)
    else:
        frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.fillna("", inplace=True)
    frame.rename(columns=column_mapping, inplace=True)

    # Ensure required columns exist
    for col in ["Title", "Genre", "Description", "Cast"]:
        if col not in frame.columns:
            frame[col] = ""

    for col in frame.columns:
        frame[col] = frame[col].astype(str).apply(clean_text)

    available_features = [col for col in text_features if col in frame.columns]
    frame["content"] = frame[available_features].astype(str).agg(" ".join, axis=1)
    return frame


print("Loading dataset...")
df = load_dataset(DATA_PATH)

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

if _args.model:
    # An explicit --model overrides the auto-selection above.
    if not os.path.isfile(os.path.join(_args.model, "config.json")):
        raise SystemExit(f"--model is not a SentenceTransformer folder: {_args.model}")
    selected_local = _args.model

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
# Use a smaller batch size by default to be CPU-friendly; increase if you have more RAM/GPUs
batch_size = 16
model_id = os.path.abspath(selected_local) if selected_local else MODEL_NAME


def encode(texts, progress=True):
    vectors = model.encode(
        texts,
        show_progress_bar=progress,
        convert_to_numpy=True,
        batch_size=batch_size,
    ).astype("float32")
    faiss.normalize_L2(vectors)
    return vectors


def load_reusable_vectors(reuse_dir):
    """Map embedding text -> vector from an earlier build, or {} if it can't be trusted."""
    paths = {name: os.path.join(reuse_dir, name) for name in ("index.faiss", "build_info.json", "dataset.csv")}
    missing = [name for name, path in paths.items() if not os.path.isfile(path)]
    if missing:
        print(f"Reuse: {reuse_dir} has no {', '.join(missing)}; encoding everything.")
        return {}
    with open(paths["build_info.json"], encoding="utf-8") as f:
        previous_info = json.load(f)
    if os.path.abspath(previous_info.get("model", "")) != os.path.abspath(model_id):
        print(f"Reuse: earlier index used another model ({previous_info.get('model')}); encoding everything.")
        return {}
    previous_index = faiss.read_index(paths["index.faiss"])
    previous_content = load_dataset(paths["dataset.csv"])["content"].tolist()
    if previous_index.ntotal != len(previous_content):
        print("Reuse: earlier index and its dataset.csv differ in length; encoding everything.")
        return {}
    previous_vectors = previous_index.reconstruct_n(0, previous_index.ntotal)
    reusable = {}
    for text, vector in zip(previous_content, previous_vectors):
        reusable.setdefault(text, vector)
    return reusable


contents = df["content"].tolist()
reusable = load_reusable_vectors(_args.reuse) if _args.reuse else {}
reuse_rows = [i for i, text in enumerate(contents) if text in reusable]

if reuse_rows:
    # Spot-check: reused vectors must match what this model produces now.
    check_rows = [reuse_rows[i] for i in np.linspace(0, len(reuse_rows) - 1, num=min(REUSE_CHECK_SAMPLES, len(reuse_rows)), dtype=int)]
    fresh = encode([contents[i] for i in check_rows], progress=False)
    cosines = [float(np.dot(fresh[k], reusable[contents[i]])) for k, i in enumerate(check_rows)]
    if min(cosines) < REUSE_MIN_COSINE:
        print(f"Reuse: spot-check failed (min cosine {min(cosines):.6f}); encoding everything.")
        reuse_rows = []
    else:
        print(f"Reuse: spot-check passed on {len(check_rows)} dramas (min cosine {min(cosines):.6f}).")

reused = set(reuse_rows)
encode_rows = [i for i in range(len(contents)) if i not in reused]
print(f"Generating embeddings: {len(encode_rows)} to encode, {len(reuse_rows)} reused...")
fresh_vectors = encode([contents[i] for i in encode_rows]) if encode_rows else None

dim = (getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension)()
embeddings = np.empty((len(contents), dim), dtype="float32")
for i in reuse_rows:
    embeddings[i] = reusable[contents[i]]
for k, i in enumerate(encode_rows):
    embeddings[i] = fresh_vectors[k]

# ======================================================
# 5. Build FAISS Index
# ======================================================
index = faiss.IndexFlatIP(dim)  # Inner product for cosine similarity
index.add(embeddings)

print(f"FAISS index built successfully with {index.ntotal} items.")

# ======================================================
# 6. Save Index and Metadata
# ======================================================
faiss.write_index(index, os.path.join(INDEX_DIR, "index.faiss"))

# Poster URL and its ID ('https://i.mydramalist.com/9oX6Gf.jpg' -> '9oX6Gf'). The backend
# finds the local poster "<Title> (<Year>) [<ID>].jpg" by this ID, so same-title dramas
# keep their own posters; without these fields it joins the dataset CSV on title + aired.
if "image" in df.columns:
    df["image_url"] = df["image"].astype(str).str.strip()
    df["image_id"] = df["image_url"].map(
        lambda url: os.path.splitext(os.path.basename(urlparse(url).path))[0] if url else ""
    )
if "watchers" in df.columns:
    df["watchers"] = pd.to_numeric(
        df["watchers"].astype(str).str.replace(",", ""), errors="coerce"
    ).fillna(0.0)

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
    "image_url",
    "image_id",
    "watchers",
]
meta_cols = [c for c in meta_cols if c in df.columns]

metadata = df[meta_cols].to_dict(orient="records")

with open(os.path.join(INDEX_DIR, "meta.pkl"), "wb") as f:
    pickle.dump(metadata, f)

# Record what this index was built from, so a later check can confirm the backend
# loads the same model and the index matches its dataset.
with open(DATA_PATH, "rb") as f:
    data_sha256 = hashlib.sha256(f.read()).hexdigest()
build_info = {
    "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "data_path": os.path.abspath(DATA_PATH),
    "data_sha256": data_sha256,
    "model": model_id,
    "rows": int(index.ntotal),
    "dimension": int(dim),
    "encoded": len(encode_rows),
    "reused": len(reuse_rows),
}
with open(os.path.join(INDEX_DIR, "build_info.json"), "w", encoding="utf-8") as f:
    json.dump(build_info, f, indent=2)

print(f"Index and metadata saved in: {INDEX_DIR}")
print("All done! Your FAISS index is ready for recommendations.")
