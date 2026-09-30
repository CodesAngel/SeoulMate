# SeoulMate Training Pipeline

Trains the production SBERT embedding model, FAISS indices, cross-encoder reranker, and
learning-to-rank model. Run via `train_pipeline.py`, which orchestrates the numbered scripts in
`steps/`.

## Quick start

```bash
python train_pipeline.py              # interactive menu
python train_pipeline.py --mode full  # full pipeline, all steps
python train_pipeline.py --mode quick # generate data + rebuild index only, skip fine-tuning
python train_pipeline.py --mode build-index   # just one step
```

## Pipeline (in order)

| Step | Script | What it does |
| --- | --- | --- |
| 1 | `steps/step1_generate_training_data.py` | Generates K-drama specific training pairs/triplets from `data/final/kdrama_dataset.csv` |
| 2 | `steps/step2_fine_tune_sbert.py` | Fine-tunes SBERT on the generated training data |
| 3 | `steps/step3_build_index.py` | Builds FAISS indices (main, genre, actor, theme) from the fine-tuned model |
| 4 | `steps/step4_generate_reranker_data.py` | Generates labeled (query, doc, label) pairs for reranker training |
| 5 | `steps/step5_fine_tune_cross_encoder.py` | Fine-tunes the cross-encoder reranker |
| 6 | `steps/step6_train_ltr.py` | Trains the learning-to-rank model (run twice: `generate-data` then `train` mode) |

## Standalone / legacy scripts (NOT called by `train_pipeline.py`)

These exist in `steps/` but aren't part of the numbered pipeline — kept for manual/ad-hoc use,
not deleted, since removing them wasn't asked for:

- **`steps/legacy_build_index.py`** — ⚠️ a simpler, older FAISS index builder. As of 2026-09-30,
  this is the script that actually produced the `meta.pkl` the **live backend currently loads** —
  not `step3_build_index.py`, the one the numbered pipeline calls. Before trusting
  `step3_build_index.py`'s output in production, verify which one you actually want to deploy;
  don't assume the numbered step is what's live.
- **`steps/standalone_fine_tune_sbert.py`** — a separate, simpler SBERT fine-tuner, distinct from
  `step2_fine_tune_sbert.py`.
- **`steps/standalone_eval_retrieval.py`** — a manual retrieval evaluation/debug tool (Recall@K,
  NDCG@K), not part of the pipeline.

## Notes

- All step scripts can be run individually — see each file's docstring for its own `--` flags.
- `train_pipeline.py`'s `SCRIPTS` dict maps its internal step keys to these file paths; if you
  rename a step script again, update that dict too.
