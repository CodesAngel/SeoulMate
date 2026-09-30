r"""
STANDALONE — not called by train_pipeline.py. The pipeline's SBERT fine-tuner
is step2_fine_tune_sbert.py; this is a separate, simpler alternative kept for
manual/ad-hoc use.

Fine-tune SentenceTransformer on SeoulMate dataset.

Usage:
    python standalone_fine_tune_sbert.py --data d:\Projects\SeoulMate\data\final\kdrama_dataset.csv \
        --model paraphrase-multilingual-mpnet-base-v2 --output d:\Projects\SeoulMate\training\models\sbert-finetuned

Notes:
- Preferably run on a GPU.
- This script creates (Title, Content) pairs where Content = Title + Genre + Description + Cast.
- Uses MultipleNegativesRankingLoss which works well for retrieval tasks.
"""

import argparse
import os
import pandas as pd
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader


def build_examples(df, max_examples=None):
    examples = []
    for _, row in df.iterrows():
        title = str(row.get("title") or row.get("Title") or "")
        # Build a content string with relevant fields
        parts = []
        for c in [
            "title",
            "Title",
            "genres",
            "Genre",
            "description",
            "Description",
            "actors",
            "Cast",
            "directors",
            "Director",
        ]:
            if c in row:
                parts.append(str(row[c]))
        content = " ".join([p for p in parts if p and p != "nan"])
        if not title or not content:
            continue
        examples.append(InputExample(texts=[title, content]))
        if max_examples and len(examples) >= max_examples:
            break
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Path to dataset (csv or xlsx)")
    parser.add_argument("--model", default="paraphrase-multilingual-mpnet-base-v2")
    parser.add_argument(
        "--output", required=True, help="Output folder to save fine-tuned model"
    )
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument(
        "--max_examples", type=int, default=None, help="Limit examples for quick runs"
    )
    args = parser.parse_args()

    # Load data
    if args.data.lower().endswith(".xlsx") or args.data.lower().endswith(".xls"):
        df = pd.read_excel(args.data)
    else:
        df = pd.read_csv(args.data)

    print(f"Loaded {len(df)} rows from {args.data}")

    examples = build_examples(df, max_examples=args.max_examples)
    print(f"Built {len(examples)} training examples (title, content pairs)")

    if len(examples) == 0:
        raise SystemExit("No training examples found. Check your dataset columns.")

    model = SentenceTransformer(args.model)

    train_dataloader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    warmup_steps = max(100, int(len(train_dataloader) * args.epochs * 0.1))

    os.makedirs(args.output, exist_ok=True)
    print("Starting training...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        output_path=args.output,
        show_progress_bar=True,
    )

    print(f"Fine-tuned model saved to {args.output}")


if __name__ == "__main__":
    main()
