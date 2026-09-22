"""
=============================================================================
SEOULMATE 1-CLICK COMPLETE TRAINING PIPELINE
=============================================================================
Just run:
    python training-new/train.py

This single file runs the complete end-to-end training process automatically:
  1. Generates training pairs + hard negative triplets + balanced validation set
  2. Fine-tunes the dense multilingual embedding model with hard negatives
  3. Builds all enhanced FAISS vector indices (main, genre, actor, theme)
  4. Generates labeled reranker training data
  5. Fine-tunes the multilingual cross-encoder reranker
  6. Performs a verification smoke-test on the new models and indices
=============================================================================
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# =============================================================================
# DEFAULT CONFIGURATION (Customize here if desired)
# =============================================================================
# Base Models:
# - Option A: "intfloat/multilingual-e5-base" (768-d, exact match for current FAISS structure)
# - Option B: "BAAI/bge-m3" (1024-d, ultimate state-of-the-art multilingual model)
BASE_BI_ENCODER = "intfloat/multilingual-e5-base"
BASE_RERANKER   = "BAAI/bge-reranker-v2-m3"

# Training hyperparameters:
BI_ENCODER_EPOCHS = 3
BI_ENCODER_BATCH  = 8
RERANKER_EPOCHS   = 2
RERANKER_BATCH    = 8
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
STEPS_DIR = SCRIPT_DIR / "steps"
PYTHON_EXE = sys.executable


def banner(title: str, step_num: int, total_steps: int = 6):
    print("\n" + "=" * 70)
    print(f"[{step_num}/{total_steps}] {title.upper()}")
    print("=" * 70)


def run_command(cmd: list, step_title: str):
    start = time.time()
    print(f"Running: {' '.join(str(c) for c in cmd)}\n")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"\n❌ Pipeline failed during: {step_title} (exit code: {proc.returncode})")
        sys.exit(proc.returncode)
    elapsed = time.time() - start
    print(f"\n✓ {step_title} completed in {elapsed:.1f}s")


def verify_artifacts():
    banner("Verifying Generated Artifacts", 6)
    models_dir = SCRIPT_DIR / "models"
    faiss_dir = SCRIPT_DIR / "faiss_index"

    expected_files = [
        faiss_dir / "index.faiss",
        faiss_dir / "genre_index.faiss",
        faiss_dir / "actor_index.faiss",
        faiss_dir / "theme_index.faiss",
        faiss_dir / "meta.pkl",
        faiss_dir / "index_manifest.json",
        models_dir / "e5-kdrama-finetuned" / "model.safetensors",
        models_dir / "cross-encoder-finetuned" / "model.safetensors",
    ]

    all_good = True
    for f in expected_files:
        if f.exists():
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  • Found: {f.name} ({size_mb:.2f} MB)")
        else:
            print(f"  • ⚠️ Warning: Missing {f.name}")
            all_good = False

    return all_good


def main():
    total_start = time.time()

    print("=" * 70)
    print("   SEOULMATE 1-CLICK AUTOMATIC MODEL TRAINING SYSTEM")
    print("=" * 70)
    print(f"Bi-Encoder Model:      {BASE_BI_ENCODER}")
    print(f"Reranker Model:        {BASE_RERANKER}")
    print(f"Bi-Encoder Epochs:     {BI_ENCODER_EPOCHS} (Batch: {BI_ENCODER_BATCH})")
    print(f"Reranker Epochs:       {RERANKER_EPOCHS} (Batch: {RERANKER_BATCH})")
    print("=" * 70)

    # Step 1: Generate Training Data & Hard Negatives
    banner("Generating Training Data & Hard Negatives", 1)
    run_command([
        PYTHON_EXE,
        str(STEPS_DIR / "generate_training_data.py"),
        "--is_e5"
    ], "Data Generation")

    # Step 2: Fine-Tune Bi-Encoder
    banner("Fine-Tuning Multilingual Dense Bi-Encoder", 2)
    run_command([
        PYTHON_EXE,
        str(STEPS_DIR / "fine_tune_kdrama_sbert.py"),
        "--base_model", BASE_BI_ENCODER,
        "--epochs", str(BI_ENCODER_EPOCHS),
        "--batch_size", str(BI_ENCODER_BATCH)
    ], "Bi-Encoder Fine-Tuning")

    # Step 3: Build Enhanced FAISS Indices
    banner("Building Enhanced FAISS Vector Indices", 3)
    run_command([
        PYTHON_EXE,
        str(STEPS_DIR / "enhanced_index_builder.py")
    ], "FAISS Index Building")

    # Step 4: Generate Reranker Training Data
    banner("Generating Reranker Labeled Dataset", 4)
    run_command([
        PYTHON_EXE,
        str(STEPS_DIR / "generate_reranker_data.py")
    ], "Reranker Data Generation")

    # Step 5: Fine-Tune Cross-Encoder Reranker
    banner("Fine-Tuning Cross-Encoder Reranker", 5)
    run_command([
        PYTHON_EXE,
        str(STEPS_DIR / "fine_tune_cross_encoder.py"),
        "--model", BASE_RERANKER,
        "--epochs", str(RERANKER_EPOCHS),
        "--batch_size", str(RERANKER_BATCH)
    ], "Cross-Encoder Fine-Tuning")

    # Step 6: Verification
    success = verify_artifacts()

    total_time = (time.time() - total_start) / 60
    print("\n" + "=" * 70)
    if success:
        print(f"🎉 1-CLICK TRAINING COMPLETED SUCCESSFULLY IN {total_time:.1f} MINUTES!")
        print("\nAll models and indices are ready to deploy in 'training-new/':")
        print(f"  • Models: {SCRIPT_DIR / 'models'}")
        print(f"  • FAISS:  {SCRIPT_DIR / 'faiss_index'}")
    else:
        print(f"⚠️ Training completed in {total_time:.1f} minutes with some warnings.")
    print("=" * 70)


if __name__ == "__main__":
    main()
