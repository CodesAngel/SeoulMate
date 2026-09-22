"""
SeoulMate Next-Gen Model Training Pipeline

Master orchestrator for training the updated recommendation models:
1. Generate K-drama training pairs, hard negatives, and balanced validation data
2. Fine-tune modern multilingual dense embeddings (intfloat/multilingual-e5-base)
3. Build enhanced 768-d FAISS indices (main, genre, actor, theme)
4. Generate reranker training data
5. Fine-tune multilingual cross-encoder reranker (BAAI/bge-reranker-v2-m3)

Usage:
    python train_pipeline.py                     # Interactive menu
    python train_pipeline.py --mode full         # Full end-to-end pipeline
    python train_pipeline.py --mode quick        # Data generation + FAISS indexing only
    python train_pipeline.py --mode fine-tune    # SBERT/E5 fine-tuning only
    python train_pipeline.py --mode build-index  # Build FAISS index only
    python train_pipeline.py --mode train-reranker # Train cross-encoder only
"""

import os
import sys
import argparse
import subprocess
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
STEPS_DIR = os.path.join(SCRIPTS_DIR, "steps")

SCRIPTS = {
    "generate_data": os.path.join(STEPS_DIR, "generate_training_data.py"),
    "fine_tune": os.path.join(STEPS_DIR, "fine_tune_kdrama_sbert.py"),
    "build_index": os.path.join(STEPS_DIR, "enhanced_index_builder.py"),
    "generate_reranker_data": os.path.join(STEPS_DIR, "generate_reranker_data.py"),
    "fine_tune_reranker": os.path.join(STEPS_DIR, "fine_tune_cross_encoder.py"),
}


def run_step(script_path: str, args: list = None, title: str = ""):
    args = args or []
    print("\n" + "=" * 65)
    print(f"STEP: {title}")
    print(f"Executing: {os.path.basename(script_path)} {' '.join(args)}")
    print("=" * 65)

    start_time = time.time()
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(cmd)

    elapsed = time.time() - start_time
    if result.returncode != 0:
        print(f"\n❌ Error: Step '{title}' failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"✓ Step completed in {elapsed:.1f}s")


def show_menu():
    print("=" * 65)
    print("SEOULMATE NEXT-GEN MODEL TRAINING PIPELINE")
    print("=" * 65)
    print("Select a pipeline option:")
    print("  1. Full Pipeline (Data -> E5 Fine-Tuning -> FAISS -> Reranker)")
    print("  2. Dense Embedding Only (Data -> E5 Fine-Tuning -> FAISS)")
    print("  3. Quick Rebuild (Data -> FAISS Indexing using existing model)")
    print("  4. Generate Training Data only")
    print("  5. Fine-Tune E5 Embeddings only")
    print("  6. Build FAISS Index only")
    print("  7. Train Cross-Encoder Reranker only")
    print("  8. Exit")
    choice = input("\nEnter choice [1]: ").strip() or "1"
    return choice


def main():
    parser = argparse.ArgumentParser(description="SeoulMate Model Training Master Pipeline")
    parser.add_argument(
        "--mode",
        choices=["full", "embeddings", "quick", "generate-data", "fine-tune", "build-index", "train-reranker", "interactive"],
        default="interactive",
        help="Pipeline execution mode"
    )
    parser.add_argument("--epochs", type=int, default=3, help="SBERT / E5 training epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size per step")
    parser.add_argument("--base_model", default="intfloat/multilingual-e5-base", help="Base bi-encoder model")
    parser.add_argument("--reranker_model", default="BAAI/bge-reranker-v2-m3", help="Base cross-encoder model")
    parser.add_argument("--reranker_epochs", type=int, default=2, help="Cross-encoder epochs")
    args = parser.parse_args()

    mode = args.mode
    if mode == "interactive":
        choice = show_menu()
        if choice == "1":
            mode = "full"
        elif choice == "2":
            mode = "embeddings"
        elif choice == "3":
            mode = "quick"
        elif choice == "4":
            mode = "generate-data"
        elif choice == "5":
            mode = "fine-tune"
        elif choice == "6":
            mode = "build-index"
        elif choice == "7":
            mode = "train-reranker"
        else:
            print("Exiting.")
            sys.exit(0)

    total_start = time.time()

    # Step 1: Generate Data
    if mode in ["full", "embeddings", "quick", "generate-data"]:
        run_step(
            SCRIPTS["generate_data"],
            [],
            "1. Generating K-Drama Training Data & Hard Negatives"
        )

    # Step 2: Fine-Tune Bi-Encoder
    if mode in ["full", "embeddings", "fine-tune"]:
        run_step(
            SCRIPTS["fine_tune"],
            [
                "--base_model", args.base_model,
                "--epochs", str(args.epochs),
                "--batch_size", str(args.batch_size)
            ],
            f"2. Fine-Tuning Multilingual Dense Model ({args.base_model})"
        )

    # Step 3: Build FAISS Indices
    if mode in ["full", "embeddings", "quick", "build-index"]:
        run_step(
            SCRIPTS["build_index"],
            [],
            "3. Building 768-d FAISS Vector Indices (Main, Genre, Actor, Theme)"
        )

    # Step 4 & 5: Reranker
    if mode in ["full", "train-reranker"]:
        run_step(
            SCRIPTS["generate_reranker_data"],
            [],
            "4. Generating Labeled Reranker Dataset"
        )
        run_step(
            SCRIPTS["fine_tune_reranker"],
            [
                "--model", args.reranker_model,
                "--epochs", str(args.reranker_epochs)
            ],
            f"5. Fine-Tuning Cross-Encoder Reranker ({args.reranker_model})"
        )

    total_time = time.time() - total_start
    print("\n" + "=" * 65)
    print(f"🎉 PIPELINE COMPLETED SUCCESSFULLY IN {total_time/60:.1f} MINUTES!")
    print("Artifacts saved to:")
    print(f"  • Models: {os.path.join(SCRIPTS_DIR, 'models')}")
    print(f"  • FAISS Indices: {os.path.join(SCRIPTS_DIR, 'faiss_index')}")
    print("=" * 65)


if __name__ == "__main__":
    main()
