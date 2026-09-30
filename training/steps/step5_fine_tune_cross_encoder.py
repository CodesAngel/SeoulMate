"""
Fine-tune a cross-encoder (sequence-pair regression) using a CSV of (query, doc_text, label).

The script trains a sequence-pair regressor with MSE loss (labels can be 0/1 or graded relevance).
Designed to work on CPU (small batches) but will use GPU if available.

Usage:
  python step5_fine_tune_cross_encoder.py --data reranker_train.csv --model cross-encoder/ms-marco-MiniLM-L-6-v2 --output models/cross-enc-small --epochs 2 --batch_size 8

"""

import argparse
import os
import csv
import math
from typing import List, Dict

import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn import MSELoss
from transformers import AutoTokenizer, AutoModelForSequenceClassification

try:
    from transformers import AdamW
except ImportError:
    from torch.optim import AdamW

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)


class PairDataset(Dataset):
    def __init__(self, rows: List[Dict]):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        r = self.rows[idx]
        return r["query"], r["doc_text"], float(r["label"])


def collate_fn(batch, tokenizer, max_length=256):
    queries, docs, labels = zip(*batch)
    # tokenizer supports encoding pairs: (query, doc)
    enc = tokenizer(
        list(queries),
        list(docs),
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )
    labels = torch.tensor(labels, dtype=torch.float32)
    return enc, labels


def read_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if "query" not in r or "doc_text" not in r or "label" not in r:
                continue
            rows.append(
                {
                    "query": r["query"],
                    "doc_text": r["doc_text"],
                    "label": float(r["label"]),
                }
            )
    return rows


def train(args):
    assert os.path.exists(args.data), f"Data file not found: {args.data}"
    rows = read_csv(args.data)
    if len(rows) == 0:
        raise SystemExit("No training rows found in CSV")

    # optionally limit for quick CPU runs
    if args.max_examples and args.max_examples > 0:
        rows = rows[: args.max_examples]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=1)

    device = torch.device(
        "cuda" if torch.cuda.is_available() and not args.force_cpu else "cpu"
    )
    model.to(device)

    dataset = PairDataset(rows)
    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer, max_length=args.max_length),
    )

    optimizer = AdamW(model.parameters(), lr=args.lr)
    loss_fn = MSELoss()

    model.train()
    steps_per_epoch = math.ceil(len(dataset) / args.batch_size)
    print(
        f"Training on {len(dataset)} samples, {steps_per_epoch} steps/epoch, device={device}"
    )

    for epoch in range(args.epochs):
        running_loss = 0.0
        for step, (enc, labels) in enumerate(dataloader):
            enc = {k: v.to(device) for k, v in enc.items()}
            labels = labels.to(device)

            outputs = model(**enc)
            logits = outputs.logits.view(-1)
            loss = loss_fn(logits, labels)

            loss.backward()
            optimizer.step()
            optimizer.zero_grad()

            running_loss += loss.item()
            if (step + 1) % args.log_every == 0:
                avg = running_loss / args.log_every
                print(
                    f"Epoch {epoch+1}/{args.epochs} Step {step+1}/{steps_per_epoch} - avg_loss={avg:.4f}"
                )
                running_loss = 0.0

    # save
    os.makedirs(args.output, exist_ok=True)
    print(f"Saving model to {args.output}")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("Done")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", required=True, help="CSV with columns query,doc_text,label"
    )
    parser.add_argument("--model", default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    parser.add_argument(
        "--output",
        default=os.path.join(TRAINING_ROOT, "models", "cross-enc-finetuned"),
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument(
        "--max_examples",
        type=int,
        default=0,
        help="If >0, limit training rows (useful for CPU quick runs)",
    )
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--log_every", type=int, default=50)
    parser.add_argument(
        "--force_cpu", action="store_true", help="Force CPU even if CUDA available"
    )
    args = parser.parse_args()

    train(args)


if __name__ == "__main__":
    main()
