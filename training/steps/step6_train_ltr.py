"""
Learning-to-Rank (LTR) Model for SeoulMate

This implements a neural ranking model that learns to rank K-drama
recommendations based on multiple features:

1. Semantic similarity (from FAISS)
2. Lexical similarity (from BM25)
3. Genre match score
4. Rating score
5. Popularity score
6. Recency score
7. Actor match score
8. Theme match score

The model is trained on user interaction data (clicks, ratings) to learn
optimal feature weights for ranking.

Usage:
    # Generate training data from logs
    python step6_train_ltr.py --mode generate-data

    # Train the model
    python step6_train_ltr.py --mode train --epochs 50

    # Evaluate
    python step6_train_ltr.py --mode evaluate
"""

import os
import argparse
import json
import pickle
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

# For neural ranking
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader

    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("Warning: PyTorch not found. Using LightGBM-based LTR instead.")

try:
    import lightgbm as lgb

    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

# ======================================================
# Configuration (using relative paths)
# ======================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(TRAINING_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "final", "kdrama_dataset.csv")
MODEL_DIR = os.path.join(TRAINING_ROOT, "models")
LTR_DIR = os.path.join(TRAINING_ROOT, "ltr_model")

# Feature names for the ranking model
FEATURE_NAMES = [
    "semantic_score",  # FAISS cosine similarity
    "lexical_score",  # BM25 score
    "genre_match_count",  # Number of matching genres
    "genre_match_ratio",  # Ratio of matched genres
    "rating_value",  # Drama rating (0-10)
    "rating_count",  # Number of ratings (popularity)
    "recency_score",  # How recent the drama is
    "actor_match",  # Does drama have searched actor
    "theme_match",  # Does drama match searched theme
    "title_exact_match",  # Exact title match bonus
    "title_partial_match",  # Partial title match
    "keyword_match",  # Keywords match count
]


@dataclass
class RankingExample:
    """A training example for learning-to-rank."""

    query: str
    doc_id: int
    features: np.ndarray
    label: float  # Relevance score (0-4, or click/no-click binary)


# ======================================================
# Feature Extraction
# ======================================================
class FeatureExtractor:
    """Extract ranking features from query-document pairs."""

    def __init__(self, metadata: List[Dict]):
        self.metadata = metadata
        self.title_to_idx = {m["Title"].lower(): i for i, m in enumerate(metadata)}

        # Pre-compute some global statistics
        self.max_rating_count = max(
            float(m.get("rating_count", 0) or 0) for m in metadata
        )
        self.current_year = 2026  # For recency calculation

    def extract_features(
        self,
        query: str,
        doc_idx: int,
        semantic_score: float = 0.0,
        lexical_score: float = 0.0,
        detected_genres: List[str] = None,
        detected_actors: List[str] = None,
        detected_themes: List[str] = None,
    ) -> np.ndarray:
        """Extract all features for a query-document pair."""

        doc = self.metadata[doc_idx]
        features = np.zeros(len(FEATURE_NAMES), dtype=np.float32)

        # 1. Semantic score (from FAISS)
        features[0] = semantic_score

        # 2. Lexical score (from BM25)
        features[1] = lexical_score

        # 3-4. Genre match scores
        doc_genres = str(doc.get("Genre", "")).lower().split(",")
        doc_genres = [g.strip() for g in doc_genres if g.strip()]

        if detected_genres:
            genre_matches = sum(
                1
                for g in detected_genres
                if g.lower() in str(doc.get("Genre", "")).lower()
            )
            features[2] = genre_matches
            features[3] = genre_matches / len(detected_genres) if detected_genres else 0

        # 5. Rating value
        try:
            features[4] = float(doc.get("rating_value", 0) or 0) / 10.0
        except:
            features[4] = 0.0

        # 6. Rating count (popularity)
        try:
            rating_count = float(doc.get("rating_count", 0) or 0)
            features[5] = (
                rating_count / self.max_rating_count if self.max_rating_count > 0 else 0
            )
        except:
            features[5] = 0.0

        # 7. Recency score
        try:
            year_str = str(doc.get("Release Years", "") or doc.get("year", ""))
            if year_str:
                year = int(year_str[:4])
                features[6] = max(
                    0, 1 - (self.current_year - year) / 20
                )  # Decay over 20 years
        except:
            features[6] = 0.5  # Default for unknown years

        # 8. Actor match
        if detected_actors:
            doc_cast = str(doc.get("Cast", "")).lower()
            features[7] = (
                1.0
                if any(actor.lower() in doc_cast for actor in detected_actors)
                else 0.0
            )

        # 9. Theme match
        if detected_themes:
            doc_desc = str(doc.get("Description", "")).lower()
            doc_keywords = str(doc.get("keywords", "")).lower()
            combined = f"{doc_desc} {doc_keywords}"

            theme_keywords = {
                "time_travel": ["time travel", "time slip", "past", "future"],
                "north_korea": ["north korea", "defector", "soldier"],
                "food": ["restaurant", "chef", "cooking", "food"],
                "medical": ["doctor", "hospital", "medical"],
                "legal": ["lawyer", "court", "legal"],
            }

            for theme in detected_themes:
                if theme in theme_keywords:
                    if any(kw in combined for kw in theme_keywords[theme]):
                        features[8] = 1.0
                        break

        # 10. Title exact match
        doc_title = str(doc.get("Title", "")).lower()
        query_lower = query.lower()
        features[9] = 1.0 if query_lower == doc_title else 0.0

        # 11. Title partial match
        if query_lower in doc_title or doc_title in query_lower:
            features[10] = 0.5
        elif any(word in doc_title for word in query_lower.split()):
            features[10] = 0.25

        # 12. Keyword match
        doc_keywords = str(doc.get("keywords", "")).lower()
        keyword_matches = sum(1 for word in query_lower.split() if word in doc_keywords)
        features[11] = min(1.0, keyword_matches / 3)  # Normalize

        return features


# ======================================================
# Neural Ranking Model (PyTorch)
# ======================================================
if HAS_TORCH:

    class NeuralRanker(nn.Module):
        """
        A neural network for learning-to-rank.

        Architecture: MLP with feature interactions
        """

        def __init__(self, num_features: int, hidden_dims: List[int] = [64, 32]):
            super().__init__()

            layers = []
            prev_dim = num_features

            for hidden_dim in hidden_dims:
                layers.extend(
                    [
                        nn.Linear(prev_dim, hidden_dim),
                        nn.ReLU(),
                        nn.Dropout(0.2),
                    ]
                )
                prev_dim = hidden_dim

            layers.append(nn.Linear(prev_dim, 1))

            self.model = nn.Sequential(*layers)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.model(x).squeeze(-1)

    class RankingDataset(Dataset):
        """Dataset for ranking examples."""

        def __init__(self, examples: List[RankingExample]):
            self.features = np.array([ex.features for ex in examples])
            self.labels = np.array([ex.label for ex in examples])

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            return (
                torch.FloatTensor(self.features[idx]),
                torch.FloatTensor([self.labels[idx]]),
            )

    class PairwiseRankingLoss(nn.Module):
        """
        Pairwise ranking loss (similar to RankNet).

        For each query, we compare pairs of documents and learn
        that higher-labeled docs should rank higher.
        """

        def __init__(self, margin: float = 1.0):
            super().__init__()
            self.margin = margin

        def forward(
            self, pred_pos: torch.Tensor, pred_neg: torch.Tensor
        ) -> torch.Tensor:
            # We want pred_pos > pred_neg
            return torch.clamp(self.margin - pred_pos + pred_neg, min=0).mean()


# ======================================================
# LightGBM Ranking Model (Alternative)
# ======================================================
class LightGBMRanker:
    """
    LightGBM-based learning-to-rank model.

    Uses LambdaRank objective which directly optimizes NDCG.
    """

    def __init__(self, params: Dict = None):
        self.model = None
        self.params = params or {
            "objective": "lambdarank",
            "metric": "ndcg",
            "ndcg_eval_at": [5, 10],
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
        }

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        groups_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
        groups_val: np.ndarray = None,
        num_rounds: int = 100,
    ):
        """Train the ranking model."""
        train_data = lgb.Dataset(
            X_train, y_train, group=groups_train, feature_name=FEATURE_NAMES
        )

        valid_sets = [train_data]
        if X_val is not None:
            val_data = lgb.Dataset(
                X_val,
                y_val,
                group=groups_val,
                feature_name=FEATURE_NAMES,
                reference=train_data,
            )
            valid_sets.append(val_data)

        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_rounds,
            valid_sets=valid_sets,
            callbacks=[
                lgb.early_stopping(stopping_rounds=10),
                lgb.log_evaluation(period=10),
            ],
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict relevance scores."""
        if self.model is None:
            raise ValueError("Model not trained yet")
        return self.model.predict(X)

    def save(self, path: str):
        """Save model to file."""
        self.model.save_model(path)

    def load(self, path: str):
        """Load model from file."""
        self.model = lgb.Booster(model_file=path)

    def feature_importance(self) -> Dict[str, float]:
        """Get feature importance."""
        if self.model is None:
            return {}

        importance = self.model.feature_importance(importance_type="gain")
        return dict(zip(FEATURE_NAMES, importance))


# ======================================================
# Training Data Generation
# ======================================================
def generate_synthetic_training_data(
    metadata: List[Dict], num_queries: int = 500
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic training data for LTR.

    Since we don't have real user clicks, we create synthetic
    training data based on heuristics:
    - Exact title match = label 4 (highly relevant)
    - Same genre + high rating = label 3
    - Same genre = label 2
    - Partial match = label 1
    - No match = label 0
    """

    extractor = FeatureExtractor(metadata)

    all_features = []
    all_labels = []
    all_groups = []

    # Sample queries from titles and genres
    queries = []

    # Title queries
    for m in metadata[: num_queries // 2]:
        queries.append({"query": m["Title"], "type": "title"})

    # Genre queries
    genre_queries = [
        "romantic comedy",
        "medical drama",
        "thriller",
        "historical",
        "action",
        "fantasy",
        "school drama",
        "legal drama",
    ]
    for gq in genre_queries:
        queries.append({"query": gq, "type": "genre", "genres": gq.split()})

    for query_info in queries:
        query = query_info["query"]
        query_lower = query.lower()

        group_size = 0

        for doc_idx, doc in enumerate(metadata):
            # Calculate features
            features = extractor.extract_features(
                query=query,
                doc_idx=doc_idx,
                semantic_score=np.random.uniform(0.3, 0.9),  # Simulated
                lexical_score=np.random.uniform(0.1, 0.8),
                detected_genres=query_info.get("genres", []),
            )

            # Assign label based on relevance heuristics
            doc_title = str(doc.get("Title", "")).lower()
            doc_genres = str(doc.get("Genre", "")).lower()

            if query_lower == doc_title:
                label = 4  # Exact match
            elif query_lower in doc_title:
                label = 3  # Partial title match
            elif query_info["type"] == "genre":
                genre_words = query_info.get("genres", [])
                if all(g in doc_genres for g in genre_words):
                    # Bonus for high rating
                    try:
                        rating = float(doc.get("rating_value", 0) or 0)
                        label = 3 if rating >= 8.5 else 2
                    except:
                        label = 2
                elif any(g in doc_genres for g in genre_words):
                    label = 1
                else:
                    label = 0
            else:
                label = 0

            all_features.append(features)
            all_labels.append(label)
            group_size += 1

        all_groups.append(group_size)

    return (np.array(all_features), np.array(all_labels), np.array(all_groups))


# ======================================================
# Main Pipeline
# ======================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["generate-data", "train", "evaluate"], required=True
    )
    parser.add_argument("--data", default=DATA_PATH, help="Path to dataset")
    parser.add_argument("--output", default=LTR_DIR, help="Output directory")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs/rounds")
    parser.add_argument(
        "--model_type", choices=["lightgbm", "neural"], default="lightgbm"
    )
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    # Load metadata
    if args.data.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(args.data)
    else:
        df = pd.read_csv(args.data, encoding="utf-8-sig")
    df.fillna("", inplace=True)

    # Standardize columns
    column_mapping = {"title": "Title", "genres": "Genre", "description": "Description"}
    df.rename(columns=column_mapping, inplace=True)

    metadata = df.to_dict("records")
    print(f"Loaded {len(metadata)} dramas")

    if args.mode == "generate-data":
        print("\n=== Generating Training Data ===")

        X, y, groups = generate_synthetic_training_data(metadata, num_queries=300)

        # Save training data
        np.save(os.path.join(args.output, "X_train.npy"), X)
        np.save(os.path.join(args.output, "y_train.npy"), y)
        np.save(os.path.join(args.output, "groups_train.npy"), groups)

        print(f"Generated {len(X)} training examples")
        print(f"Label distribution: {dict(zip(*np.unique(y, return_counts=True)))}")
        print(f"Saved to {args.output}")

    elif args.mode == "train":
        print("\n=== Training LTR Model ===")

        # Load training data
        X = np.load(os.path.join(args.output, "X_train.npy"))
        y = np.load(os.path.join(args.output, "y_train.npy"))
        groups = np.load(os.path.join(args.output, "groups_train.npy"))

        print(f"Loaded {len(X)} training examples")

        # Split into train/val
        split_idx = int(len(groups) * 0.8)
        cumsum = np.cumsum(groups)
        train_end = cumsum[split_idx - 1] if split_idx > 0 else 0

        X_train, X_val = X[:train_end], X[train_end:]
        y_train, y_val = y[:train_end], y[train_end:]
        groups_train, groups_val = groups[:split_idx], groups[split_idx:]

        if args.model_type == "lightgbm" and HAS_LIGHTGBM:
            model = LightGBMRanker()
            model.train(
                X_train, y_train, groups_train, X_val, y_val, groups_val, args.epochs
            )

            # Save model
            model.save(os.path.join(args.output, "ltr_model.txt"))

            # Print feature importance
            print("\nFeature Importance:")
            for name, importance in sorted(
                model.feature_importance().items(), key=lambda x: -x[1]
            ):
                print(f"  {name}: {importance:.2f}")

        elif args.model_type == "neural" and HAS_TORCH:
            # Neural ranking training
            print("Training neural ranker...")
            # Implementation would go here
            raise NotImplementedError("Neural ranker training not yet implemented")

        else:
            print(f"\n⚠️ Model type '{args.model_type}' not available.")
            print("LightGBM is not installed. Install with: pip install lightgbm")
            print("Skipping LTR training - system will use default scoring.")

            # Save a simple weights file as fallback
            fallback_weights = dict(zip(FEATURE_NAMES, [1.0] * len(FEATURE_NAMES)))
            with open(os.path.join(args.output, "fallback_weights.json"), "w") as f:
                json.dump(fallback_weights, f, indent=2)
            print(f"Saved fallback weights to {args.output}/fallback_weights.json")

    elif args.mode == "evaluate":
        print("\n=== Evaluating LTR Model ===")

        if not HAS_LIGHTGBM:
            raise ImportError("LightGBM required for evaluation")

        # Load model and test data
        model = LightGBMRanker()
        model.load(os.path.join(args.output, "ltr_model.txt"))

        X = np.load(os.path.join(args.output, "X_train.npy"))
        y = np.load(os.path.join(args.output, "y_train.npy"))

        # Predict scores
        scores = model.predict(X)

        # Simple evaluation: correlation between predicted scores and labels
        from scipy.stats import spearmanr

        correlation, pvalue = spearmanr(scores, y)

        print(f"Spearman correlation: {correlation:.4f} (p={pvalue:.4e})")

    print("\n" + "=" * 60)
    print("LEARNING-TO-RANK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
