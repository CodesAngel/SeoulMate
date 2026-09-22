"""
Generate labeled training data (query, doc_text, label) for cross-encoder reranker fine-tuning.
"""

import os
import argparse
import pickle
import csv
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_INDEX = os.path.join(TRAINING_ROOT, "faiss_index", "index.faiss")
DEFAULT_META = os.path.join(TRAINING_ROOT, "faiss_index", "meta.pkl")
DEFAULT_MODEL = os.path.join(TRAINING_ROOT, "models", "e5-kdrama-finetuned")
FALLBACK_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_OUTPUT = os.path.join(TRAINING_ROOT, "reranker_train.csv")


def main():
    parser = argparse.ArgumentParser(description="Generate labeled dataset for reranker")
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--meta", default=DEFAULT_META)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--topk", type=int, default=30)
    parser.add_argument("--num_queries", type=int, default=600)
    args = parser.parse_args()

    assert os.path.exists(args.index), f"FAISS index not found: {args.index}"
    assert os.path.exists(args.meta), f"Metadata not found: {args.meta}"

    with open(args.meta, "rb") as f:
        metadata = pickle.load(f)

    index = faiss.read_index(args.index)
    model_name = args.model if os.path.exists(args.model) else FALLBACK_MODEL
    print(f"Loading encoder for query retrieval: {model_name}")
    encoder = SentenceTransformer(model_name)

    is_e5 = "e5" in model_name.lower()
    prefix_q = "query: " if is_e5 else ""

    queries = []
    # Use drama titles and genre combinations as search queries
    for idx, item in enumerate(metadata[:args.num_queries]):
        queries.append((idx, f"{prefix_q}{item['Title']}"))
        if item.get("Genre"):
            first_genre = item["Genre"].split(",")[0].strip()
            queries.append((idx, f"{prefix_q}{item['Title']} {first_genre}"))

    queries = queries[:args.num_queries]
    print(f"Processing {len(queries)} query variations against FAISS index...")

    rows = []
    for true_id, q_text in queries:
        clean_query = q_text.replace("query: ", "")
        q_emb = encoder.encode([q_text], normalize_embeddings=True).astype("float32")
        scores, indices = index.search(q_emb, args.topk)

        for rank, cand_id in enumerate(indices[0]):
            if cand_id < 0 or cand_id >= len(metadata):
                continue

            cand = metadata[cand_id]
            doc_text = f"{cand['Title']}. {cand.get('Genre', '')}. {cand.get('Description', '')[:350]} Cast: {cand.get('Cast', '')}"
            label = 1.0 if cand_id == true_id else 0.0

            rows.append({
                "query": clean_query,
                "doc_text": doc_text,
                "label": label,
                "true_id": true_id,
                "candidate_id": cand_id
            })

    print(f"Generated {len(rows)} labeled pairs. Writing to {args.output}...")
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["query", "doc_text", "label", "true_id", "candidate_id"])
        writer.writeheader()
        writer.writerows(rows)

    print("Reranker training data generated successfully!")


if __name__ == "__main__":
    main()
