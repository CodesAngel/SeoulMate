"""
Held-out search evaluation: searches whose expected answers come from the
dataset's own MyDramaList tags, genres and cast billing, not from search results.

Never tune ranking against these queries; use them to check that a change that
helps evaluate_accuracy.py also helps searches it wasn't tuned on.

Metrics per case:
- P@5: share of the top 5 results that are relevant (match the case's tags/genres,
  or the actor in a lead role).
- R@10: share of the 10 most-watched relevant dramas (fewer if the pool is
  smaller) that appear in the top 10.
- Hit@1: the first result is relevant.

Run after starting the backend:
    SEOULMATE_API_URL=http://127.0.0.1:8001 python tests/evaluation/evaluate_heldout.py
"""

import csv
import json
import os
import sys
from pathlib import Path

import requests

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_DIR = Path(__file__).resolve().parents[2]
BASE_URL = os.environ.get("SEOULMATE_API_URL", "http://127.0.0.1:8001")
CASES_PATH = Path(__file__).with_name("heldout_queries.json")
DATASET_PATH = Path(
    os.environ.get("SEOULMATE_EVAL_DATASET", PROJECT_DIR / "training" / "faiss_index" / "dataset.csv")
)


def split_terms(value):
    return {part.strip().lower() for part in str(value or "").split(",") if part.strip()}


def name_key(name):
    return " ".join(str(name).lower().split())


def load_dramas():
    with open(DATASET_PATH, encoding="utf-8-sig", newline="") as handle:
        dramas = []
        for row in csv.DictReader(handle):
            dramas.append(
                {
                    "title": row["title"].strip(),
                    "tags": split_terms(row.get("keywords")),
                    "genres": split_terms(row.get("genres")),
                    "cast": [name_key(c) for c in str(row.get("actors") or "").split(",")],
                    "watchers": float(str(row.get("watchers") or 0).replace(",", "") or 0),
                }
            )
    return dramas


def is_relevant(drama, case):
    if "actor" in case:
        return name_key(case["actor"]) in drama["cast"][:2]
    for group in case["match"]:
        tags = {t.lower() for t in group.get("tags", [])}
        genres = {g.lower() for g in group.get("genres", [])}
        if not (drama["tags"] & tags or drama["genres"] & genres):
            return False
    return True


def evaluate_case(case, dramas_by_title, dramas):
    pool = sorted(
        (d for d in dramas if is_relevant(d, case)), key=lambda d: d["watchers"], reverse=True
    )
    target = {d["title"].lower() for d in pool[:10]}
    response = requests.get(
        f"{BASE_URL}/recommend", params={"title": case["query"], "top_n": 10}, timeout=120
    )
    response.raise_for_status()
    titles = [r.get("Title", "") for r in response.json().get("recommendations", [])]

    def relevant_title(title):
        # Duplicate titles exist; any matching row counts.
        return any(is_relevant(d, case) for d in dramas_by_title.get(title.lower(), []))

    top5 = titles[:5]
    p5 = sum(relevant_title(t) for t in top5) / 5 if top5 else 0.0
    r10 = (
        len({t.lower() for t in titles[:10]} & target) / len(target) if target else None
    )
    hit1 = bool(titles) and relevant_title(titles[0])
    return {
        "id": case["id"],
        "query": case["query"],
        "kind": "actor" if "actor" in case else "topic",
        "pool": len(pool),
        "p5": p5,
        "r10": r10,
        "hit1": hit1,
        "top5": top5,
        "missed_popular": [d["title"] for d in pool[:10] if d["title"] not in titles[:10]][:5],
    }


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def main():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    dramas = load_dramas()
    dramas_by_title = {}
    for drama in dramas:
        dramas_by_title.setdefault(drama["title"].lower(), []).append(drama)

    results = [evaluate_case(case, dramas_by_title, dramas) for case in cases]
    for r in results:
        r10 = f"{r['r10']:.0%}" if r["r10"] is not None else "-"
        print(f"{r['id']:24} P@5 {r['p5']:>4.0%}  R@10 {r10:>4}  pool {r['pool']:>3}  top5={r['top5']}")
        if r["missed_popular"]:
            print(f"{'':24} missed popular: {r['missed_popular']}")

    print("\n" + "=" * 60)
    print("HELD-OUT EVALUATION SUMMARY")
    print("=" * 60)
    for kind in ("topic", "actor"):
        group = [r for r in results if r["kind"] == kind]
        print(
            f"{kind:6} ({len(group)} cases): P@5 {mean(r['p5'] for r in group):.1%} | "
            f"R@10 {mean(r['r10'] for r in group):.1%} | Hit@1 {mean(r['hit1'] for r in group):.1%}"
        )
    print(
        f"ALL    ({len(results)} cases): P@5 {mean(r['p5'] for r in results):.1%} | "
        f"R@10 {mean(r['r10'] for r in results):.1%} | Hit@1 {mean(r['hit1'] for r in results):.1%}"
    )


if __name__ == "__main__":
    main()
