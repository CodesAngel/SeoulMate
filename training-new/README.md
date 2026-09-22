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
├── train.py                   # 1-Click automated master training script
├── train_pipeline.py          # Modular CLI and interactive runner
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

#### 🚀 The 1-Click Complete Run (Zero Prompts, Full Pipeline)
Just run this one file and everything is done automatically:
```powershell
python training-new\train.py
```

---

## Execution Order Followed by `train.py`

When you run `python training-new\train.py`, it executes the following 6 stages sequentially without requiring any user input:

```text
[Dataset: dramalist_kdramas.xlsx]
               │
               ▼
   [Step 1] Generate Training Data & Hard Negatives
               │
               ▼
   [Step 2] Fine-Tune Bi-Encoder Model (E5 / SBERT)
               │
               ▼
   [Step 3] Build FAISS Vector Indices (Main, Genre, Actor, Theme)
               │
               ▼
   [Step 4] Generate Labeled Reranker Dataset
               │
               ▼
   [Step 5] Fine-Tune Cross-Encoder Reranker
               │
               ▼
   [Step 6] Verification & Artifact Health Smoke-Test
```

### Stage Details:
1. **Step 1: Data Generation & Hard Negative Mining** (`steps/generate_training_data.py`)
   - Reads `data/final/dramalist_kdramas.xlsx`.
   - Generates title-description, genre, actor, and theme pairs.
   - Mines BM25 false positives as hard negative triplets (e.g. separating true contract marriage from general romance).
   - Generates a balanced validation split (scores 1.0 vs 0.0) so correlation metrics compute cleanly without `NaN`.
   - Outputs: `training_data/training_pairs.json`, `training_data/training_triplets.json`, `training_data/eval_pairs.json`.
2. **Step 2: Bi-Encoder Fine-Tuning** (`steps/fine_tune_kdrama_sbert.py`)
   - Fine-tunes `intfloat/multilingual-e5-base` using **both** `MultipleNegativesRankingLoss` (on pairs) and `TripletLoss` (on hard negatives) for 3 epochs.
   - Uses gradient accumulation for an effective batch size of 32.
   - Outputs: `models/e5-kdrama-finetuned/model.safetensors` and tokenizer configs.
3. **Step 3: FAISS Vector Index Building** (`steps/enhanced_index_builder.py`)
   - Encodes all dramas into normalized vector embeddings using the model trained in Step 2.
   - Builds 4 specialized FAISS indices: `index.faiss` (main), `genre_index.faiss`, `actor_index.faiss`, `theme_index.faiss`, plus `meta.pkl` and `index_manifest.json`.
4. **Step 4: Reranker Dataset Generation** (`steps/generate_reranker_data.py`)
   - Uses the FAISS index from Step 3 to retrieve candidate dramas for sample queries, creating labeled `(query, document_text, label)` pairs.
   - Outputs: `reranker_train.csv`.
5. **Step 5: Cross-Encoder Reranker Fine-Tuning** (`steps/fine_tune_cross_encoder.py`)
   - Fine-tunes `BAAI/bge-reranker-v2-m3` using sequence-pair regression for 2 epochs.
   - Outputs: `models/cross-encoder-finetuned/model.safetensors`.
6. **Step 6: Verification Smoke-Test**
   - Automatically inspects the filesystem to verify all 8 model weights, FAISS vector indices, and metadata files exist and have non-zero file sizes, printing a final summary report.

---

## Difference Between `train.py` and `train_pipeline.py`

| Feature | `train.py` (1-Click Automated) | `train_pipeline.py` (Modular & Interactive) |
| :--- | :--- | :--- |
| **Philosophy** | **"Just run everything automatically"** | **"Let me choose what to run and configure"** |
| **User Prompts** | **Zero prompts.** Starts immediately. | Shows an interactive terminal menu if run without flags. |
| **CLI Arguments** | None needed. | Supports CLI flags (`--mode`, `--epochs`, `--base_model`, etc.). |
| **Execution Scope** | Always runs the **full 6-step pipeline** from data generation to artifact verification. | Can run **individual steps** (e.g., only FAISS index, only reranker, or full). |
| **How to Configure** | Edit the variables directly at the top of `train.py`. | Pass flags on the command line or choose from the interactive menu. |
| **Verification Step** | Includes an automatic **file size & health smoke-test** at the end. | Exits after running the requested steps. |

---

### Alternative Ways to Run (`train_pipeline.py`)

#### Option A: Interactive Menu
If you want to pick specific individual stages or tweak epochs interactively:
```powershell
python training-new\train_pipeline.py
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

---

## Verified Training Run Results (Colab T4 GPU)

The complete 1-click pipeline (`train.py`) was executed and fully verified on a Google Colab T4 GPU instance:

| Metric | Result | Notes |
| :--- | :--- | :--- |
| **Total Pipeline Duration** | **`45.7 minutes`** | All 6 stages executed end-to-end automatically |
| **Hardware Used** | NVIDIA Tesla T4 GPU (16 GB VRAM) | PyTorch CUDA accelerated |
| **Bi-Encoder Model** | `intfloat/multilingual-e5-base` | 768 dimensions (1,060.67 MB `model.safetensors`) |
| **Bi-Encoder Eval Spearman** | **`0.6045`** | Solid semantic correlation (zero-shot trope evaluation) |
| **Bi-Encoder Eval Pearson** | **`0.5092`** | Clean linear correlation (balanced positive/negative set, No `NaN`) |
| **Bi-Encoder Final Train Loss** | **`2.819`** | MultipleNegativesRankingLoss + TripletLoss (Epoch 3) |
| **Cross-Encoder Model** | `BAAI/bge-reranker-v2-m3` | Sequence classification regressor (2,165.86 MB) |
| **Reranker Loss Progression** | **`0.0582` $\to$ `0.0064`** | Superb convergence (~10× loss reduction in 2 epochs; final step loss: `0.0031`) |
| **FAISS Indices Generated** | 4 indices (768-d) | `index.faiss`, `genre_index.faiss`, `actor_index.faiss`, `theme_index.faiss` (5.34 MB each) |

### Stage-by-Stage Telemetry:
* **Step 1 (Data Generation):** `6.4s` | 14,776 training pairs, 176 hard negative triplets, 70 balanced eval pairs.
* **Step 2 (Bi-Encoder Fine-Tuning):** `137.3s` (~2.3 min) | 1,385 optimizer steps, 138 warmup steps.
* **Step 3 (FAISS Index Building):** `83.2s` | 1,823 dramas encoded across 4 vector indices + `meta.pkl`.
* **Step 4 (Reranker Data Generation):** `27.3s` | 600 query variations against FAISS, 18,000 candidate labeled pairs.
* **Step 5 (Cross-Encoder Fine-Tuning):** `2485.2s` (~41.4 min) | 10,000 training pairs, 2 epochs (1,250 steps/epoch).
* **Step 6 (Verification):** All 8 model and index artifacts validated with healthy file sizes.

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
   CROSS_ENCODER_MODEL = str(TRAINING_DIR / "models" / "cross-encoder-finetuned")
   ```
2. Run tests to confirm accuracy gains:
   ```powershell
   python tests\evaluation\evaluate_accuracy.py
   ```
