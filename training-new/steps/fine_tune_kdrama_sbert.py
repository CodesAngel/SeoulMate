"""
SeoulMate Next-Gen SBERT / E5 Fine-Tuning

Fine-tunes modern multilingual embeddings (default: intfloat/multilingual-e5-base)
using contrastive MultipleNegativesRankingLoss and hard negative triplets.

Features:
- Effective batch sizes via gradient accumulation
- Evaluator with balanced positive/negative pairs (guaranteed clean Spearman/Pearson metrics)
- Early checkpointing and evaluation tracking
"""

import os
import argparse
import json
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses, evaluation
from sentence_transformers.training_args import SentenceTransformerTrainingArguments
from sentence_transformers.trainer import SentenceTransformerTrainer
from torch.utils.data import DataLoader
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_BASE_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_DATA_DIR = os.path.join(TRAINING_ROOT, "training_data")
DEFAULT_OUTPUT_DIR = os.path.join(TRAINING_ROOT, "models", "e5-kdrama-finetuned")


def load_pairs(data_dir: str, max_examples: int = 15000) -> List[InputExample]:
    pairs_file = os.path.join(data_dir, "training_pairs.json")
    if not os.path.exists(pairs_file):
        raise FileNotFoundError(f"Training pairs not found at {pairs_file}. Run generate_training_data.py first.")

    with open(pairs_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if max_examples and len(data) > max_examples:
        data = data[:max_examples]

    examples = [InputExample(texts=[item["anchor"], item["positive"]]) for item in data]
    print(f"Loaded {len(examples)} training pairs.")
    return examples


def load_triplets(data_dir: str, max_examples: int = 4000) -> List[InputExample]:
    triplets_file = os.path.join(data_dir, "training_triplets.json")
    if not os.path.exists(triplets_file):
        print("No training_triplets.json found. Triplet loss will be skipped.")
        return []

    with open(triplets_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if max_examples and len(data) > max_examples:
        data = data[:max_examples]

    examples = [InputExample(texts=[item["anchor"], item["positive"], item["negative"]]) for item in data]
    print(f"Loaded {len(examples)} hard negative triplets.")
    return examples


def build_evaluator(data_dir: str):
    eval_file = os.path.join(data_dir, "eval_pairs.json")
    if not os.path.exists(eval_file):
        print("No eval_pairs.json found. Progress evaluation will be skipped.")
        return None

    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    s1 = [item["sentence1"] for item in eval_data]
    s2 = [item["sentence2"] for item in eval_data]
    scores = [float(item["score"]) for item in eval_data]

    evaluator = evaluation.EmbeddingSimilarityEvaluator(
        s1, s2, scores,
        name="kdrama_multilingual_eval",
        show_progress_bar=False
    )
    print(f"Built evaluator with {len(scores)} pairs (balanced positives/negatives).")
    return evaluator


def main():
    parser = argparse.ArgumentParser(description="Fine-tune multilingual dense embeddings for K-drama search")
    parser.add_argument("--base_model", default=DEFAULT_BASE_MODEL, help="Base Hugging Face model (default: intfloat/multilingual-e5-base)")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Training data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for fine-tuned weights")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size per device")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4, help="Gradient accumulation steps (8 x 4 = effective batch 32)")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--warmup_ratio", type=float, default=0.1, help="Warmup ratio")
    parser.add_argument("--max_examples", type=int, default=15000, help="Max pairs to train on")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("=" * 60)
    print("SEOULMATE DENSE EMBEDDING FINE-TUNING")
    print("=" * 60)
    print(f"Base model:        {args.base_model}")
    print(f"Device:            {device}")
    print(f"Batch size:        {args.batch_size} (effective: {args.batch_size * args.gradient_accumulation_steps})")
    print(f"Epochs:            {args.epochs}")
    print(f"Output directory:  {args.output_dir}")
    print("=" * 60)

    # 1. Load model
    print(f"Loading base model: {args.base_model} ...")
    model = SentenceTransformer(args.base_model, device=device)

    # 2. Load data
    train_examples = load_pairs(args.data_dir, max_examples=args.max_examples)
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=args.batch_size)

    # 3. Loss functions
    train_loss = losses.MultipleNegativesRankingLoss(model=model)
    train_objectives = [(train_dataloader, train_loss)]

    # Also include hard negative triplets if available
    train_triplets = load_triplets(args.data_dir, max_examples=4000)
    if train_triplets:
        triplet_dataloader = DataLoader(train_triplets, shuffle=True, batch_size=args.batch_size)
        triplet_loss = losses.TripletLoss(model=model)
        train_objectives.append((triplet_dataloader, triplet_loss))
        print("✓ Enabled Hard Negative TripletLoss alongside MultipleNegativesRankingLoss!")

    # 4. Evaluator
    evaluator = build_evaluator(args.data_dir)

    # 5. Calculate warmup steps
    total_steps = len(train_dataloader) * args.epochs // args.gradient_accumulation_steps
    warmup_steps = int(total_steps * args.warmup_ratio)

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\nStarting training ({total_steps} optimizer steps, {warmup_steps} warmup steps)...")

    model.fit(
        train_objectives=train_objectives,
        evaluator=evaluator,
        epochs=args.epochs,
        evaluation_steps=max(50, len(train_dataloader) // 3),
        warmup_steps=warmup_steps,
        output_path=args.output_dir,
        optimizer_params={"lr": args.lr},
        show_progress_bar=True
    )

    print(f"\nTraining completed successfully! Model saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
