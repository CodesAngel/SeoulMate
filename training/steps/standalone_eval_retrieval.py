r"""
STANDALONE — not called by train_pipeline.py. A manual evaluation/debug tool,
not part of the numbered pipeline.

Evaluate retrieval performance (Recall@K, NDCG@K) for a FAISS index and encoder.

Usage examples:
  python standalone_eval_retrieval.py --model d:\Projects\SeoulMate\training\models\sbert-finetuned --index d:\Projects\SeoulMate\training\faiss_index\index.faiss

If --test_csv is not provided, the script will create a simple test set using the first N rows of metadata (query=Title).
"""

import argparse
import os
import pickle
import numpy as np
import faiss
import csv
from sentence_transformers import SentenceTransformer
from sklearn.metrics import ndcg_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)


def load_metadata(meta_path):
    with open(meta_path, "rb") as f:
        return pickle.load(f)


def build_default_testset(metadata, n=100):
    queries = []
    true_ids = []
    for i, m in enumerate(metadata[:n]):
        title = m.get("Title") or m.get("title") or ""
        if not title:
            continue
        queries.append(title)
        true_ids.append(i)
    return queries, true_ids


def read_csv_testset(path):
    queries = []
    true_ids = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            queries.append(r["query"])
            true_ids.append(int(r["true_id"]))
    return queries, true_ids


def recall_at_k(I, true_ids, k):
    hits = 0
    for ids, t in zip(I, true_ids):
        hits += int(t in ids[:k])
    return hits / len(true_ids)


def ndcg_at_k(I, D, true_ids, k):
    # Build per-query y_true (one-hot over returned candidates) and scores
    y_true = []
    y_score = []
    for ids, scores, t in zip(I, D, true_ids):
        topk_ids = ids[:k]
        rel = [1 if tid == t else 0 for tid in topk_ids]
        y_true.append(rel)
        y_score.append(scores[:k])
    # sklearn expects arrays
    return ndcg_score(np.array(y_true), np.array(y_score))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", default=None, help="Path to SBERT model (folder) or HF model name"
    )
    parser.add_argument(
        "--index",
        default=os.path.join(TRAINING_ROOT, "faiss_index", "index.faiss"),
    )
    parser.add_argument(
        "--meta", default=os.path.join(TRAINING_ROOT, "faiss_index", "meta.pkl")
    )
    parser.add_argument(
        "--test_csv",
        default=None,
        help="Optional CSV of test queries with columns: query,true_id",
    )
    parser.add_argument("--topk", type=int, default=10)
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="If building default testset, number of examples to use",
    )
    args = parser.parse_args()

    assert os.path.exists(args.index), f"Index not found: {args.index}"
    assert os.path.exists(args.meta), f"Meta not found: {args.meta}"

    metadata = load_metadata(args.meta)
    print(f"Loaded metadata with {len(metadata)} items")

    if args.test_csv and os.path.exists(args.test_csv):
        queries, true_ids = read_csv_testset(args.test_csv)
    else:
        queries, true_ids = build_default_testset(metadata, n=args.limit)
        print(f"Built default testset with {len(queries)} examples")

    # Load model
    if args.model:
        print(f"Loading encoder model: {args.model}")
        encoder = SentenceTransformer(args.model)
    else:
        # try to reuse model used to build index
        print(
            "No model provided, attempting to use the index-sized model name from local cache"
        )
        encoder = None

    # Load FAISS index
    index = faiss.read_index(args.index)

    # Encode queries
    if encoder is not None:
        q_emb = encoder.encode(queries, convert_to_numpy=True, show_progress_bar=True)
        faiss.normalize_L2(q_emb)
    else:
        raise SystemExit("Encoder model path is required (--model) for this evaluation")

    D, I = index.search(q_emb, args.topk)

    # Metrics
    print("Computing metrics...")
    r1 = recall_at_k(I, true_ids, 1)
    r5 = recall_at_k(I, true_ids, 5)
    r10 = recall_at_k(I, true_ids, args.topk)
    ndcg10 = ndcg_at_k(I, D, true_ids, args.topk)

    print(f"Recall@1: {r1:.4f}")
    print(f"Recall@5: {r5:.4f}")
    print(f"Recall@{args.topk}: {r10:.4f}")
    print(f"NDCG@{args.topk}: {ndcg10:.4f}")


if __name__ == "__main__":
    main()
