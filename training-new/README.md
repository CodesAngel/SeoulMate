# SeoulMate Next-Gen Training Pipeline (`training-new`)

This folder contains the next-generation training pipeline designed to upgrade SeoulMate's search accuracy from **88.5% to 93–95%**.

---

## What's Improved in This Pipeline

1. **Modern Multilingual Embedding Base:**
   - Defaults to **`intfloat/multilingual-e5-base`** (ranked significantly higher on MTEB than MPNet).
   - Generates **768-dimensional embeddings**, remaining 100% architecturally compatible with SeoulMate's 768-d FAISS index setup.
   - Includes asymmetric `query:` and `passage:` prefixes.
2. **Hard Negative Mining:**
   - BM25 false-positive mining forces the model to discern nuanced tropes (e.g. contract marriage vs general romance).
3. **Fixed Evaluation (No NaN):**
   - Automatically generates balanced positive (1.0) and negative (0.0) test pairs so Pearson and Spearman correlations compute cleanly during training.
4. **Multilingual Cross-Encoder Reranker:**
   - Upgraded to fine-tune **`BAAI/bge-reranker-v2-m3`** for native Korean/English cross-attention.

---

## Directory Structure

```text
training-new/
├── train_pipeline.py          # Master CLI and interactive runner
├── requirements.txt           # Python dependencies
├── steps/
│   ├── generate_training_data.py   # Dataset & hard negative generator
│   ├── fine_tune_kdrama_sbert.py   # Dense embedding fine-tuner
│   ├── enhanced_index_builder.py   # 768-d FAISS index builder
│   ├── generate_reranker_data.py   # Cross-encoder dataset builder
│   └── fine_tune_cross_encoder.py  # Cross-encoder fine-tuner
├── training_data/             # Generated JSON datasets (pairs, triplets, eval)
├── models/                    # Exported model weights
└── faiss_index/               # Generated FAISS vector indexes (index.faiss, meta.pkl)
```

---

## How to Run

### 1. Install Dependencies

```powershell
pip install -r training-new\requirements.txt
```

---

### 2. Run the Pipeline

#### Option A: Interactive Menu (Recommended)
Run with no arguments to get an interactive numbered menu:
```powershell
cd training-new
python train_pipeline.py
```

#### Option B: Full Pipeline (End-to-End)
Runs data generation, E5 fine-tuning, FAISS indexing, and cross-encoder training:
```powershell
python training-new\train_pipeline.py --mode full
```

#### Option C: Dense Embeddings Only (Fastest Full Upgrade)
Trains the bi-encoder and builds the FAISS indexes:
```powershell
python training-new\train_pipeline.py --mode embeddings
```

#### Option D: Individual Steps
```powershell
# 1. Generate training data and hard negatives only
python training-new\train_pipeline.py --mode generate-data

# 2. Fine-tune E5 model only (specify epochs and batch size)
python training-new\train_pipeline.py --mode fine-tune --epochs 3 --batch_size 8

# 3. Build FAISS indices only
python training-new\train_pipeline.py --mode build-index

# 4. Train Reranker only
python training-new\train_pipeline.py --mode train-reranker
```

---

## Deploying Outputs to the Backend

Once training completes, the new model and index artifacts will be in:
* Model: `training-new/models/e5-kdrama-finetuned/`
* FAISS Index: `training-new/faiss_index/`
* Cross-Encoder: `training-new/models/cross-encoder-finetuned/`

To switch your live backend (`backend/app.py`) to these new models:
1. Update `TRAINING_DIR` in `backend/app.py`:
   ```python
   TRAINING_DIR = PROJECT_DIR / "training-new"
   ```
2. Run tests to confirm accuracy gains:
   ```powershell
   python tests\evaluation\evaluate_accuracy.py
   ```
