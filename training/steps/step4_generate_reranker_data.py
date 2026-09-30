"""
Generate labeled data (query, doc_text, label) for cross-encoder fine-tuning.

Heuristics used:
- Queries: take 'Title' fields from metadata (or first N rows)
- For each query, retrieve top_k candidates from FAISS index
- Label = 1 if candidate's Title (from metadata) exactly matches the query (case-insensitive)
  otherwise label = 0. This produces weak supervision; you can refine labels manually.

Output: CSV with columns: query,doc_text,label,true_id,candidate_id

Usage:
  python step4_generate_reranker_data.py --index training/faiss_index/index.faiss --meta training/faiss_index/meta.pkl --output reranker_train.csv --topk 50 --num_queries 500

"""

import argparse
import os
import pickle
import csv
from sentence_transformers import SentenceTransformer
import faiss

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)


def load_metadata(meta_path):
    with open(meta_path, "rb") as f:
        return pickle.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--index",
        default=os.path.join(TRAINING_ROOT, "faiss_index", "index.faiss"),
    )
    parser.add_argument(
        "--meta", default=os.path.join(TRAINING_ROOT, "faiss_index", "meta.pkl")
    )
    parser.add_argument(
        "--model",
        default=os.path.join(TRAINING_ROOT, "models", "sbert-finetuned-full"),
    )
    parser.add_argument("--output", default="reranker_train.csv")
    parser.add_argument("--topk", type=int, default=50)
    parser.add_argument("--num_queries", type=int, default=500)
    args = parser.parse_args()

    assert os.path.exists(args.index), f"Index not found: {args.index}"
    assert os.path.exists(args.meta), f"Meta not found: {args.meta}"

    metadata = load_metadata(args.meta)
    print(f"Loaded metadata: {len(metadata)} items")

    idx = faiss.read_index(args.index)

    # Load encoder for generating query embeddings
    encoder = SentenceTransformer(args.model)

    num_q = min(args.num_queries, len(metadata))
    queries = [
        (i, metadata[i].get("Title") or metadata[i].get("title") or "")
        for i in range(num_q)
        if (metadata[i].get("Title") or metadata[i].get("title") or "")
    ]
    print(f"Using {len(queries)} queries for generation")

    q_texts = [q for _, q in queries]
    q_emb = encoder.encode(q_texts, convert_to_numpy=True, show_progress_bar=True)
    faiss.normalize_L2(q_emb)

    D, I = idx.search(q_emb, args.topk)

    out_rows = []
    for (qid, qtext), ids in zip(queries, I):
        q_title_norm = qtext.strip().lower()
        for cand_id in ids:
            cand_meta = metadata[cand_id]
            cand_title = cand_meta.get("Title") or cand_meta.get("title") or ""
            cand_text = (
                cand_meta.get("content") or cand_meta.get("Content") or cand_title
            )
            label = 1 if cand_title.strip().lower() == q_title_norm else 0
            out_rows.append(
                {
                    "query": qtext,
                    "doc_text": cand_text,
                    "label": label,
                    "true_id": qid,
                    "candidate_id": cand_id,
                }
            )

    print(f"Writing {len(out_rows)} rows to {args.output}")
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["query", "doc_text", "label", "true_id", "candidate_id"]
        )
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    print("Done")


if __name__ == "__main__":
    main()
