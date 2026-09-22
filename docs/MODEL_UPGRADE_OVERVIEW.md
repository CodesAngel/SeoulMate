# SeoulMate Model Upgrade Overview

A quick reference guide outlining the current model architecture, recommended drop-in replacements, and expected accuracy improvements.

---

## 1. At a Glance: Current vs. Proposed Stack

| Component | Current Model (Baseline) | Proposed Upgrade | Why Upgrade? |
| :--- | :--- | :--- | :--- |
| **Bi-Encoder (Dense Retrieval)** | **`sbert-finetuned-full`**<br>(`paraphrase-multilingual-mpnet-base-v2`) | **`intfloat/multilingual-e5-base`**<br>(Fine-tuned with Hard Negatives) | • **Exact 768-d match**: Drops directly into the existing FAISS index structure.<br>• **Asymmetric prefixing** (`query:` vs `passage:`) stops search queries from confusing document text.<br>• Higher MTEB multilingual ranking than MPNet. |
| **FAISS Index** | 768-dimensional index (`training/faiss_index/index.faiss`) | 768-dimensional index (Re-encoded) | Maintains high speed and zero architecture changes in FAISS handling. |
| **Cross-Encoder (Reranker)** | **`cross-enc-excellent`**<br>(`ms-marco-MiniLM-L-6-v2`) | **`BAAI/bge-reranker-v2-m3`** | • Replaces English web-search BERT with a **native multilingual** cross-encoder.<br>• Understands Korean Hangul, romanized actor names, and complex K-drama tropes. |

---

## 2. Expected Performance & Accuracy Gains

| Metric | Current Baseline | After Proposed Upgrade | Expected Gain | Real-World Impact |
| :--- | :---: | :---: | :---: | :--- |
| **Overall Accuracy** | `88.50%` | **`93.5% – 95.0%`** | **+5.0% to +6.5%** | Far fewer failed or irrelevant query outcomes. |
| **Precision@3** *(Top 3 spots)* | `63.58%` | **`75.0% – 78.0%`** | **+11.4% to +14.4%** 🚀 | Top 3 recommendations are significantly tighter and on-topic; stops generic romance bleed. |
| **Recall@10** | `98.46%` | **`99.2% – 99.5%`** | **+0.8% to +1.0%** | The target drama is almost guaranteed to be in the top 10 returned candidates. |
| **MRR (Mean Reciprocal Rank)** | `0.963` | **`0.980+`** | **+0.017+** | Relevant matches sit directly at rank 1 or 2. |
| **Multilingual & Hangul Handling** | Moderate / Keyword reliant | **State of the Art** | **High** | Search seamlessly with Hangul (`눈물의 여왕`), Romanized names (`Kim Ji Won`), and English titles (`Queen of Tears`). |

---

## 3. Why This Specific Upgrade Pair?

1. **Zero FAISS Re-architecting (768-d):**
   Many modern models output 1024 dimensions (like `bge-m3`), which would require rewriting vector dimensions across calibration scripts. **`multilingual-e5-base` outputs 768 dimensions**, keeping complete structural compatibility.
2. **True Multilingual Cross-Attention:**
   The current reranker (`ms-marco-MiniLM-L-6-v2`) was trained on English Bing searches. **`bge-reranker-v2-m3`** handles cross-lingual queries out of the box, accurately matching English queries to mixed English/Korean drama metadata.
3. **Hard Negative Mining:**
   Fine-tuning `multilingual-e5-base` with hard negative mining (contrasting true contract marriage dramas against general romance dramas) directly solves the model's biggest historical weakness: semantic trope confusion.

---

## 4. Implementation Steps (When Ready)

1. **Step 1: Mine Hard Negatives**
   - Update `training/steps/generate_training_data.py` to use BM25/current SBERT to fetch top false positives for each query as negative training triplets.
2. **Step 2: Fine-Tune `intfloat/multilingual-e5-base`**
   - Train on the hard negative dataset using `MultipleNegativesRankingLoss` (with effective batch size $\ge 32$ via gradient accumulation).
3. **Step 3: Rebuild 768-d FAISS Index**
   - Run `training/steps/enhanced_index_builder.py` with the new fine-tuned model to populate `training/faiss_index/`.
4. **Step 4: Swap the Reranker**
   - Point `CROSS_ENCODER_MODEL` in `backend/app.py` to `BAAI/bge-reranker-v2-m3`.
5. **Step 5: Run Evaluation Benchmark**
   - Execute `tests/evaluation/evaluate_accuracy.py` to measure the new accuracy scores.
