"""
SeoulMate Cross-Encoder Fine-Tuning

Fine-tunes a sequence-pair cross-encoder reranker (e.g. BAAI/bge-reranker-v2-m3 or mmarco-mMiniLMv2)
on (query, drama_doc, label) pairs.
"""

import os
import argparse
import csv
import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn import MSELoss
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.optim import AdamW

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)

DEFAULT_DATA = os.path.join(TRAINING_ROOT, "reranker_train.csv")
DEFAULT_BASE = "BAAI/bge-reranker-v2-m3"
FALLBACK_BASE = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_OUTPUT = os.path.join(TRAINING_ROOT, "models", "cross-encoder-finetuned")


class PairDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        r = self.rows[idx]
        return r["query"], r["doc_text"], float(r["label"])


def collate_fn(batch, tokenizer, max_length=256):
    queries, docs, labels = zip(*batch)
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
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Fine-tune cross-encoder reranker")
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--model", default=DEFAULT_BASE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max_samples", type=int, default=10000)
    args = parser.parse_args()

    assert os.path.exists(args.data), f"Training CSV not found: {args.data}. Run generate_reranker_data.py first."

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 60)
    print("SEOULMATE CROSS-ENCODER RERANKER FINE-TUNING")
    print("=" * 60)
    print(f"Base model:       {args.model}")
    print(f"Device:           {device}")
    print(f"Epochs:           {args.epochs}")
    print(f"Batch size:       {args.batch_size}")
    print(f"Output directory: {args.output}")
    print("=" * 60)

    rows = read_csv(args.data)
    if args.max_samples and len(rows) > args.max_samples:
        rows = rows[:args.max_samples]
    print(f"Loaded {len(rows)} training pairs.")

    print(f"Loading tokenizer & model: {args.model}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        model = AutoModelForSequenceClassification.from_pretrained(args.model, num_labels=1)
    except Exception as e:
        print(f"Could not load {args.model}: {e}. Falling back to {FALLBACK_BASE}")
        tokenizer = AutoTokenizer.from_pretrained(FALLBACK_BASE)
        model = AutoModelForSequenceClassification.from_pretrained(FALLBACK_BASE, num_labels=1)

    model.to(device)

    dataset = PairDataset(rows)
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer),
    )

    optimizer = AdamW(model.parameters(), lr=args.lr)
    criterion = MSELoss()

    model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for step, (enc, labels) in enumerate(loader):
            enc = {k: v.to(device) for k, v in enc.items()}
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(**enc)
            logits = outputs.logits.squeeze(-1)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            if (step + 1) % 50 == 0:
                print(f"Epoch [{epoch+1}/{args.epochs}] Step [{step+1}/{len(loader)}] Loss: {loss.item():.4f}")

        avg_loss = total_loss / len(loader)
        print(f"--> Epoch {epoch+1} Completed. Avg Loss: {avg_loss:.4f}\n")

    os.makedirs(args.output, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"✓ Cross-encoder model saved to: {args.output}")


if __name__ == "__main__":
    main()
