"""
K-Drama Specific SBERT Fine-Tuning

Fine-tunes a sentence transformer model on K-drama specific data
using multiple loss functions:
1. MultipleNegativesRankingLoss (for pairs)
2. TripletLoss (for hard negatives)
3. CosineSimilarityLoss (for similarity scores)

This produces embeddings that understand:
- K-drama titles, genres, themes
- Actor-drama relationships
- Theme-based queries

Usage:
    python step2_fine_tune_sbert.py --epochs 3 --batch_size 8
    python step2_fine_tune_sbert.py --epochs 1 --batch_size 4 --max_examples 2000  # Quick test
"""

import os
import argparse
import json
import gc
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from torch.utils.data import DataLoader
from typing import List
import random

# Memory management for CPU training
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# ======================================================
# Configuration
# ======================================================
# Configuration (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)

# Use a smaller model for CPU training - still multilingual but faster
BASE_MODEL = (
    "paraphrase-multilingual-MiniLM-L12-v2"  # Smaller than mpnet, faster on CPU
)
# Alternative: "paraphrase-multilingual-mpnet-base-v2" for higher quality (needs more RAM)
TRAINING_DATA_DIR = os.path.join(TRAINING_ROOT, "training_data")
OUTPUT_DIR = os.path.join(TRAINING_ROOT, "models", "sbert-kdrama-finetuned")


def load_training_pairs(data_dir: str) -> List[InputExample]:
    """Load training pairs and convert to InputExample format."""
    pairs_path = os.path.join(data_dir, "training_pairs.json")

    if not os.path.exists(pairs_path):
        raise FileNotFoundError(
            f"Training data not found at {pairs_path}. "
            "Run step1_generate_training_data.py first."
        )

    with open(pairs_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    examples = []
    for p in pairs:
        examples.append(InputExample(texts=[p["anchor"], p["positive"]]))

    print(f"Loaded {len(examples)} training pairs")
    return examples


def load_training_triplets(data_dir: str) -> List[InputExample]:
    """Load training triplets with hard negatives."""
    triplets_path = os.path.join(data_dir, "training_triplets.json")

    if not os.path.exists(triplets_path):
        print("No triplets found, skipping triplet loss")
        return []

    with open(triplets_path, "r", encoding="utf-8") as f:
        triplets = json.load(f)

    examples = []
    for t in triplets:
        examples.append(InputExample(texts=[t["anchor"], t["positive"], t["negative"]]))

    print(f"Loaded {len(examples)} training triplets")
    return examples


def create_evaluator(data_dir: str, model: SentenceTransformer):
    """Create an evaluator for monitoring training progress."""
    # Use a subset of genre query pairs for evaluation
    pairs_path = os.path.join(data_dir, "training_pairs.json")

    with open(pairs_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    # Filter to genre_query and theme_query for evaluation
    eval_pairs = [p for p in pairs if p["type"] in ["genre_query", "theme_query"]]

    if len(eval_pairs) < 10:
        return None

    # Take a sample for evaluation
    eval_sample = random.sample(eval_pairs, min(200, len(eval_pairs)))

    sentences1 = [p["anchor"] for p in eval_sample]
    sentences2 = [p["positive"] for p in eval_sample]
    scores = [1.0] * len(eval_sample)  # All positive pairs

    evaluator = evaluation.EmbeddingSimilarityEvaluator(
        sentences1, sentences2, scores, name="kdrama_eval"
    )

    return evaluator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base_model", default=BASE_MODEL, help="Base model to fine-tune"
    )
    parser.add_argument(
        "--data_dir", default=TRAINING_DATA_DIR, help="Training data directory"
    )
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output model directory")
    parser.add_argument(
        "--epochs", type=int, default=1, help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size", type=int, default=4, help="Batch size (4-8 for CPU)"
    )
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Warmup ratio")
    parser.add_argument(
        "--use_triplets",
        action="store_true",
        help="Use triplet loss in addition to MNR loss",
    )
    parser.add_argument(
        "--max_examples", type=int, default=3000, help="Max training examples"
    )
    args = parser.parse_args()

    # Memory cleanup
    gc.collect()

    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    if device == "cpu":
        print("⚠️  Running on CPU - using smaller model and limited examples")

    # Load model
    print(f"\nLoading base model: {args.base_model}")
    model = SentenceTransformer(args.base_model, device=device)

    # Load training data
    print(f"\nLoading training data from {args.data_dir}")
    pair_examples = load_training_pairs(args.data_dir)

    # Limit examples for memory
    if len(pair_examples) > args.max_examples:
        print(f"Sampling {args.max_examples} examples from {len(pair_examples)}")
        pair_examples = random.sample(pair_examples, args.max_examples)

    triplet_examples = []
    if args.use_triplets:
        triplet_examples = load_training_triplets(args.data_dir)
        max_triplets = args.max_examples // 2
        if len(triplet_examples) > max_triplets:
            triplet_examples = random.sample(triplet_examples, max_triplets)

    # Create data loaders
    pair_dataloader = DataLoader(
        pair_examples, shuffle=True, batch_size=args.batch_size
    )

    # Define losses
    train_objectives = []

    # Loss 1: MultipleNegativesRankingLoss for pairs
    mnr_loss = losses.MultipleNegativesRankingLoss(model)
    train_objectives.append((pair_dataloader, mnr_loss))
    print(f"Added MNR loss with {len(pair_examples)} examples")

    # Loss 2: TripletLoss for hard negatives (optional)
    if triplet_examples:
        triplet_dataloader = DataLoader(
            triplet_examples, shuffle=True, batch_size=args.batch_size
        )
        triplet_loss = losses.TripletLoss(
            model, distance_metric=losses.TripletDistanceMetric.COSINE
        )
        train_objectives.append((triplet_dataloader, triplet_loss))
        print(f"Added Triplet loss with {len(triplet_examples)} examples")

    # Calculate warmup steps
    total_steps = len(pair_dataloader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)

    # Create evaluator
    evaluator = create_evaluator(args.data_dir, model)

    # Prepare output directory
    os.makedirs(args.output, exist_ok=True)

    print(f"\n{'='*60}")
    print("STARTING FINE-TUNING")
    print(f"{'='*60}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Total steps: {total_steps}")
    print(f"Warmup steps: {warmup_steps}")
    print(f"Output: {args.output}")
    print(f"{'='*60}\n")

    # Train
    model.fit(
        train_objectives=train_objectives,
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        evaluator=evaluator,
        evaluation_steps=500,
        output_path=args.output,
        show_progress_bar=True,
        checkpoint_path=os.path.join(args.output, "checkpoints"),
        checkpoint_save_steps=1000,
        checkpoint_save_total_limit=3,
    )

    print(f"\n✅ Fine-tuned model saved to {args.output}")
    print("\nNext steps:")
    print("1. Rebuild FAISS index with new model:")
    print(f"   python step3_build_index.py --mode full")
    print("2. Update backend/app.py to use new model")
    print("3. Run evaluation: python tests/evaluate_accuracy.py")


if __name__ == "__main__":
    main()
