"""
SeoulMate Model Training Pipeline

This is the master script that runs the complete training pipeline:
1. Generate K-drama specific training data
2. Fine-tune SBERT on K-drama data
3. Build enhanced FAISS indices
4. Generate reranker training data
5. Fine-tune cross-encoder reranker
6. Train learning-to-rank model

Usage:
    # Interactive menu
    python train_pipeline.py

    # Full pipeline (takes ~1-2 hours on GPU)
    python train_pipeline.py --mode full

    # Quick mode (skip fine-tuning, use existing model)
    python train_pipeline.py --mode quick

    # Individual steps
    python train_pipeline.py --mode generate-data
    python train_pipeline.py --mode fine-tune
    python train_pipeline.py --mode build-index
    python train_pipeline.py --mode train-reranker
    python train_pipeline.py --mode train-ltr
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime

# ======================================================
# Configuration
# ======================================================
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
STEPS_DIR = os.path.join(SCRIPTS_DIR, "steps")

SCRIPTS = {
    "generate_data": os.path.join(STEPS_DIR, "step1_generate_training_data.py"),
    "fine_tune": os.path.join(STEPS_DIR, "step2_fine_tune_sbert.py"),
    "build_index": os.path.join(STEPS_DIR, "step3_build_index.py"),
    "generate_reranker_data": os.path.join(STEPS_DIR, "step4_generate_reranker_data.py"),
    "fine_tune_reranker": os.path.join(STEPS_DIR, "step5_fine_tune_cross_encoder.py"),
    "train_ltr": os.path.join(STEPS_DIR, "step6_train_ltr.py"),
}

RERANKER_TRAIN_PATH = os.path.join(SCRIPTS_DIR, "reranker_train.csv")
RERANKER_OUTPUT_DIR = os.path.join(SCRIPTS_DIR, "models", "cross-enc-finetuned")


def prompt_int(prompt: str, default: int) -> int:
    """Prompt for an integer, falling back to a default on blank input."""
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        print(f"Invalid number, using {default}.")
        return default


def confirm_run(args) -> bool:
    """Show selected settings and ask before starting long-running work."""
    print("\nSelected pipeline:")
    print(f"  Mode: {args.mode}")

    if args.mode in ["full", "fine-tune"]:
        print(f"  SBERT epochs: {args.epochs}")

    if args.mode in ["full", "train-reranker"] and not args.skip_reranker:
        print(f"  Cross-encoder epochs: {args.reranker_epochs}")

    if args.mode == "full":
        print(f"  Reranker stage: {'skipped' if args.skip_reranker else 'included'}")
        print(f"  LTR stage: {'skipped' if args.skip_ltr else 'included'}")

    answer = input("\nStart this run? [y/N]: ").strip().lower()
    return answer in ["y", "yes"]


def show_interactive_menu(args):
    """Show a simple menu when the script is run without CLI arguments."""
    print("=" * 60)
    print("SEOULMATE TRAINING PIPELINE")
    print("=" * 60)
    print("Choose what you want to run:\n")
    print("1. Full training: SBERT + FAISS + reranker + LTR")
    print("   asks for SBERT epochs and cross-encoder epochs")
    print("2. Full training without reranker: SBERT + FAISS + LTR")
    print("   asks for SBERT epochs only")
    print("3. Quick rebuild: generate data + rebuild FAISS only")
    print("4. Generate training data only")
    print("5. Fine-tune SBERT only")
    print("   asks for SBERT epochs")
    print("6. Build FAISS index only")
    print("7. Train reranker only: generate reranker data + cross-encoder")
    print("   asks for cross-encoder epochs")
    print("8. Train LTR only")
    print("9. Exit")

    choice = input("\nEnter choice [1]: ").strip() or "1"

    if choice == "1":
        args.mode = "full"
        args.skip_reranker = False
        args.skip_ltr = False
        args.epochs = prompt_int("SBERT epochs", args.epochs)
        args.reranker_epochs = prompt_int(
            "Cross-encoder epochs", args.reranker_epochs
        )
    elif choice == "2":
        args.mode = "full"
        args.skip_reranker = True
        args.skip_ltr = False
        args.epochs = prompt_int("SBERT epochs", args.epochs)
    elif choice == "3":
        args.mode = "quick"
    elif choice == "4":
        args.mode = "generate-data"
    elif choice == "5":
        args.mode = "fine-tune"
        args.epochs = prompt_int("SBERT epochs", args.epochs)
    elif choice == "6":
        args.mode = "build-index"
    elif choice == "7":
        args.mode = "train-reranker"
        args.reranker_epochs = prompt_int(
            "Cross-encoder epochs", args.reranker_epochs
        )
    elif choice == "8":
        args.mode = "train-ltr"
    elif choice == "9":
        print("Exiting.")
        sys.exit(0)
    else:
        print("Invalid choice, using full training.")
        args.mode = "full"
        args.skip_reranker = False
        args.skip_ltr = False

    if not confirm_run(args):
        print("Cancelled.")
        sys.exit(0)

    return args


def run_script(script_path: str, args: list = None, description: str = ""):
    """Run a Python script and handle errors."""
    args = args or []

    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"Script: {os.path.basename(script_path)}")
    print(f"{'='*60}")

    start_time = time.time()

    cmd = [sys.executable, script_path] + args

    try:
        result = subprocess.run(
            cmd,
            cwd=SCRIPTS_DIR,
            check=True,
            capture_output=False,  # Show output in real-time
        )
        elapsed = time.time() - start_time
        print(f"\n✅ Completed in {elapsed:.1f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed with exit code {e.returncode}")
        return False


def check_requirements():
    """Check that required packages are installed."""
    required = [
        ("sentence_transformers", "sentence-transformers"),
        ("faiss", "faiss-cpu"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("torch", "torch"),
    ]

    missing = []
    for module, package in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("Missing required packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="SeoulMate Model Training Pipeline")
    parser.add_argument(
        "--mode",
        choices=[
            "full",
            "quick",
            "generate-data",
            "fine-tune",
            "build-index",
            "train-reranker",
            "train-ltr",
        ],
        default="full",
        help="Pipeline mode",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Fine-tuning epochs")
    parser.add_argument(
        "--reranker-epochs",
        type=int,
        default=1,
        help="Cross-encoder reranker fine-tuning epochs",
    )
    parser.add_argument(
        "--skip-reranker",
        action="store_true",
        help="Skip reranker data generation and cross-encoder fine-tuning",
    )
    parser.add_argument("--skip-ltr", action="store_true", help="Skip LTR training")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        args = show_interactive_menu(args)

    print("=" * 60)
    print("SEOULMATE MODEL TRAINING PIPELINE")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    success = True

    if args.mode == "full":
        # Full pipeline
        steps = [
            ("generate_data", [], "Generate K-drama training data"),
            (
                "fine_tune",
                ["--epochs", str(args.epochs)],
                "Fine-tune SBERT on K-drama data",
            ),
            ("build_index", ["--mode", "full"], "Build enhanced FAISS indices"),
        ]

        if not args.skip_reranker:
            steps.append(
                (
                    "generate_reranker_data",
                    ["--output", RERANKER_TRAIN_PATH],
                    "Generate reranker training data",
                )
            )
            steps.append(
                (
                    "fine_tune_reranker",
                    [
                        "--data",
                        RERANKER_TRAIN_PATH,
                        "--output",
                        RERANKER_OUTPUT_DIR,
                        "--epochs",
                        str(args.reranker_epochs),
                    ],
                    "Fine-tune cross-encoder reranker",
                )
            )

        if not args.skip_ltr:
            steps.append(
                ("train_ltr", ["--mode", "generate-data"], "Generate LTR training data")
            )
            steps.append(
                ("train_ltr", ["--mode", "train"], "Train learning-to-rank model")
            )

        for script_key, script_args, description in steps:
            if not run_script(SCRIPTS[script_key], script_args, description):
                success = False
                print(f"\n⚠️ Pipeline stopped at: {description}")
                break

    elif args.mode == "quick":
        # Quick mode - skip fine-tuning
        steps = [
            ("generate_data", [], "Generate K-drama training data"),
            ("build_index", ["--mode", "full"], "Build enhanced FAISS indices"),
        ]

        for script_key, script_args, description in steps:
            if not run_script(SCRIPTS[script_key], script_args, description):
                success = False
                break

    elif args.mode == "generate-data":
        success = run_script(SCRIPTS["generate_data"], [], "Generate training data")

    elif args.mode == "fine-tune":
        success = run_script(
            SCRIPTS["fine_tune"], ["--epochs", str(args.epochs)], "Fine-tune SBERT"
        )

    elif args.mode == "build-index":
        success = run_script(
            SCRIPTS["build_index"], ["--mode", "full"], "Build FAISS indices"
        )

    elif args.mode == "train-reranker":
        success = run_script(
            SCRIPTS["generate_reranker_data"],
            ["--output", RERANKER_TRAIN_PATH],
            "Generate reranker training data",
        )
        if success:
            success = run_script(
                SCRIPTS["fine_tune_reranker"],
                [
                    "--data",
                    RERANKER_TRAIN_PATH,
                    "--output",
                    RERANKER_OUTPUT_DIR,
                    "--epochs",
                    str(args.reranker_epochs),
                ],
                "Fine-tune cross-encoder reranker",
            )

    elif args.mode == "train-ltr":
        success = run_script(
            SCRIPTS["train_ltr"], ["--mode", "generate-data"], "Generate LTR data"
        )
        if success:
            success = run_script(
                SCRIPTS["train_ltr"], ["--mode", "train"], "Train LTR model"
            )

    print("\n" + "=" * 60)
    if success:
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart the backend server:")
        print("   cd backend && python app.py")
        print("2. Run evaluation:")
        print("   cd tests && python evaluate_accuracy.py")
    else:
        print("❌ PIPELINE FAILED")
        print("=" * 60)
        print("Check the error messages above and fix the issues.")

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
