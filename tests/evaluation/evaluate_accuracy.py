"""
Comprehensive Accuracy Evaluation for SeoulMate Recommendation System

This script evaluates:
1. Search accuracy (FAISS + BM25)
2. Cross-encoder reranker performance
3. Query intelligence accuracy
4. Personalization effectiveness
5. Filter accuracy
6. Overall system performance
"""

import sys
import os

# Fix Windows terminal encoding issues
if sys.platform == "win32":
    import codecs

    sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import re
import requests
import time
from typing import List, Dict, Tuple
import numpy as np
from collections import defaultdict

# API endpoint. Override when testing a separate backend instance:
#   $env:SEOULMATE_API_URL='http://127.0.0.1:8002'
BASE_URL = os.environ.get("SEOULMATE_API_URL", "http://localhost:8001")

# ======================================================
# TEST DATA - Ground Truth
# ======================================================

# Format: (query, expected_top_results, category)
SEARCH_TEST_CASES = [
    # Specific title searches (should return exact match first)
    ("Crash Landing on You", ["Crash Landing on You"], "specific_title"),
    ("Itaewon Class", ["Itaewon Class"], "specific_title"),
    ("Hospital Playlist", ["Hospital Playlist"], "specific_title"),
    ("Squid Game", ["Squid Game"], "specific_title"),
    ("Business Proposal", ["Business Proposal"], "specific_title"),
    ("Goblin", ["Guardian: The Lonely and Great God"], "specific_title"),  # Goblin's official English title in the dataset
    ("Descendants of the Sun", ["Descendants of the Sun"], "specific_title"),
    ("Vincenzo", ["Vincenzo"], "specific_title"),
    ("Extraordinary Attorney Woo", ["Extraordinary Attorney Woo"], "specific_title"),
    ("True Beauty", ["True Beauty"], "specific_title"),
    ("The Glory", ["The Glory"], "specific_title"),
    ("Mr. Sunshine", ["Mr. Sunshine"], "specific_title"),
    ("Reply 1988", ["Reply 1988"], "specific_title"),
    ("Flower of Evil", ["Flower of Evil"], "specific_title"),
    ("Alchemy of Souls", ["Alchemy of Souls"], "specific_title"),
    # Dramas added with the 2,081-drama index (2026 releases)
    ("Teach You a Lesson", ["Teach You a Lesson"], "specific_title"),
    ("Agent Kim Reactivated", ["Agent Kim Reactivated"], "specific_title"),
    ("Yumi's Cells Season 3", ["Yumi's Cells Season 3"], "specific_title"),
    ("The Legend of Kitchen Soldier", ["The Legend of Kitchen Soldier"], "specific_title"),
    ("Phantom Lawyer", ["Phantom Lawyer"], "specific_title"),
    # Genre searches (should return dramas in that genre).
    # Each list holds 4-5 well-known dramas whose dataset genre/keywords fit the query.
    ("medical drama", ["Hospital Playlist", "Doctor Cha", "Good Doctor", "Dr. Romantic", "Doctors"], "genre"),
    ("doctor hospital drama", ["Hospital Playlist", "Doctor Cha", "Good Doctor", "Dr. Romantic", "Doctors"], "genre"),
    (
        "romantic comedy",
        [
            "Business Proposal",
            "What's Wrong with Secretary Kim",
            "Strong Woman Do Bong Soon",
            "Fight for My Way",
            "Her Private Life",
        ],
        "genre",
    ),
    (
        "office romance",
        [
            "Business Proposal",
            "What's Wrong with Secretary Kim",
            "Romance Is a Bonus Book",
            "Her Private Life",
            "King the Land",
        ],
        "genre",
    ),
    ("thriller", ["Squid Game", "Signal", "Stranger", "Beyond Evil", "Mouse"], "genre"),
    ("crime thriller", ["Signal", "Stranger", "Beyond Evil", "Mouse", "Tunnel"], "genre"),
    ("historical", ["Mr. Sunshine", "Kingdom", "The Red Sleeve", "Empress Ki", "Moon Lovers: Scarlet Heart Ryeo"], "genre"),
    ("sageuk royal drama", ["The Red Sleeve", "Empress Ki", "Kingdom", "Moon Embracing the Sun", "Under the Queen's Umbrella"], "genre"),
    ("legal drama", ["Extraordinary Attorney Woo", "Law School", "Vincenzo", "Lawless Lawyer", "Juvenile Justice"], "genre"),
    ("school drama", ["True Beauty", "Dream High", "Extraordinary You", "Weak Hero Class 1", "School 2013"], "genre"),
    (
        "fantasy romance",
        [
            "Guardian: The Lonely and Great God",
            "Hotel Del Luna",
            "Alchemy of Souls",
            "My Love from the Star",
            "Tale of the Nine-Tailed",
        ],
        "genre",
    ),
    ("zombie drama", ["All of Us Are Dead", "Kingdom", "Happiness"], "genre"),
    ("revenge drama", ["The Glory", "Penthouse", "Eve", "Revenge of Others", "My Name"], "genre"),
    # Theme searches
    ("north korea", ["Crash Landing on You", "King2Hearts", "Snowdrop"], "theme"),
    ("restaurant food", ["Itaewon Class", "Wok of Love", "Pasta", "Let's Eat"], "theme"),
    ("time travel", ["Signal", "Tomorrow with You", "Nine: Nine Times Time Travel", "Rooftop Prince"], "theme"),
    ("contract marriage", ["Because This Is My First Life", "Marriage Contract", "Love in Contract", "Full House"], "theme"),
    ("rich CEO romance", ["Business Proposal", "What's Wrong with Secretary Kim", "Her Private Life", "King the Land"], "theme"),
    ("school bullying revenge", ["The Glory", "Weak Hero Class 1", "Revenge of Others"], "theme"),
    ("law firm corruption", ["Vincenzo", "Law School", "Extraordinary Attorney Woo", "Lawless Lawyer", "Hyena"], "theme"),
    ("ghost supernatural hotel", ["Hotel Del Luna", "The Master's Sun"], "theme"),
    ("survival game", ["Squid Game"], "theme"),
    ("workplace startup", ["Start-Up", "Misaeng"], "theme"),
    ("healing slice of life", ["Hospital Playlist", "Our Blues", "My Mister", "Welcome to Samdal-ri", "Hometown Cha-Cha-Cha"], "theme"),
    # Actor searches
    ("Hyun Bin", ["Crash Landing on You", "Memories of the Alhambra", "Secret Garden"], "actor"),
    ("Park Seo Joon", ["Itaewon Class", "What's Wrong with Secretary Kim", "Fight for My Way"], "actor"),
    ("Song Joong Ki", ["Vincenzo", "Descendants of the Sun", "Reborn Rich"], "actor"),
    ("Kim Soo Hyun", ["My Love from the Star", "It's Okay to Not Be Okay", "Queen of Tears"], "actor"),
    ("Lee Min Ho", ["The Heirs", "The King: Eternal Monarch", "Boys over Flowers"], "actor"),
    ("Ji Chang Wook", ["Healer", "Suspicious Partner", "The K2"], "actor"),
    ("IU", ["Hotel Del Luna", "My Mister", "Moon Lovers: Scarlet Heart Ryeo"], "actor"),
    ("Park Min Young", ["What's Wrong with Secretary Kim", "Her Private Life", "Marry My Husband"], "actor"),
    ("Song Hye Kyo", ["Descendants of the Sun", "The Glory", "Encounter"], "actor"),
    ("Gong Yoo", ["Guardian: The Lonely and Great God", "Coffee Prince", "Big"], "actor"),
    # Typo / fuzzy title searches
    ("Crash Landng on You", ["Crash Landing on You"], "typo"),
    ("Hospitl Playlist", ["Hospital Playlist"], "typo"),
    ("Buisness Proposal", ["Business Proposal"], "typo"),
    ("Extraordinary Atorney Woo", ["Extraordinary Attorney Woo"], "typo"),
    ("Descendents of the Sun", ["Descendants of the Sun"], "typo"),
    ("Agent Kim Reactivatd", ["Agent Kim Reactivated"], "typo"),
    ("Phantom Lawer", ["Phantom Lawyer"], "typo"),
    # Vague queries (should return popular/relevant results)
    ("good drama", None, "vague"),  # Should return high-rated dramas
    ("best korean series", None, "vague"),
    ("something funny and light", None, "vague"),
    ("sad emotional drama", None, "vague"),
    ("popular kdrama to binge", None, "vague"),
]

# Genre detection test cases
GENRE_DETECTION_TESTS = [
    ("romantic comedy with strong female lead", ["Romance", "Comedy"]),
    ("thriller about serial killer", ["Thriller", "Crime"]),
    ("historical drama about king", ["Historical", "Drama"]),
    ("medical drama with surgery", ["Medical", "Drama"]),
    ("action packed spy thriller", ["Action", "Thriller"]),
    ("legal courtroom drama", ["Law", "Drama"]),
    ("school romance drama", ["Youth", "Romance", "Drama"]),
    ("fantasy supernatural romance", ["Fantasy", "Supernatural", "Romance"]),
    ("office workplace romance", ["Business", "Romance"]),
    ("revenge thriller", ["Revenge", "Thriller"]),
    ("zombie survival horror", ["Thriller", "Horror"]),
    ("food restaurant cooking drama", ["Food", "Drama"]),
    ("sports youth drama", ["Sports", "Youth", "Drama"]),
    ("music idol romance", ["Music", "Romance"]),
    ("sad melodrama", ["Melodrama"]),
]

# Filter test cases
FILTER_TEST_CASES = [
    {"genre": "Romance", "expected_all_match": True},
    {"genre": "Medical", "expected_all_match": True},
    {"rating_value": "8.5", "expected_min_rating": 8.5},
    {"year": "2020", "expected_year": 2020},
]

# Franchise ordering: a title search for one season must list the franchise's other
# seasons first (oldest first). Pass/fail check, not part of the overall score.
# Format: (query, expected_first_results)
FRANCHISE_TEST_CASES = [
    ("Yumi's Cells Season 3", ["Yumi's Cells", "Yumi's Cells Season 2"]),
    ("Yumi's Cells", ["Yumi's Cells Season 2", "Yumi's Cells Season 3"]),
    ("Dr. Romantic Season 3", ["Dr. Romantic", "Dr. Romantic: APPENDIX, The Beginning of Everything", "Dr. Romantic Season 2"]),
    ("Hospital Playlist", ["Hospital Playlist Season 2"]),
    ("Hospital Playlist Season 2", ["Hospital Playlist"]),
    ("Taxi Driver", ["Taxi Driver Season 2"]),
    ("Taxi Driver Season 2", ["Taxi Driver"]),
    ("dramas like Yumi's Cells Season 3", ["Yumi's Cells", "Yumi's Cells Season 2"]),
    # Same-looking names that are unrelated shows must not be grouped
    ("Family", []),
    ("Search", []),
]

# Similar-drama quality for seeds WITHOUT curated similar-title priors (2026 dramas and
# well-known older ones), so this measures seed_similarity_score itself. Expected titles
# are widely-cited comparable dramas (premise, setting, tone), checked to exist in the
# dataset. Reported separately; not part of the overall score.
# Format: (seed title, comparable dramas)
SIMILAR_TEST_CASES = [
    ("The Legend of Kitchen Soldier", ["Bon Appetit, Your Majesty", "Heo's Diner", "Wok of Love", "Pasta", "Let's Eat"]),
    ("Spring Fever", ["Hometown Cha-Cha-Cha", "Welcome to Samdal-ri", "When the Weather Is Fine", "Crash Course in Romance", "Sold Out on You", "Our Blues"]),
    ("My Royal Nemesis", ["Mr. Queen", "Destined with You", "Rooftop Prince", "My Demon", "Bon Appetit, Your Majesty"]),
    ("My Bias, My Boss", ["Her Private Life", "Business Proposal", "What's Wrong with Secretary Kim", "King the Land", "Touch Your Heart", "Kiss Sixth Sense"]),
    ("Filing for Love", ["Business Proposal", "What's Wrong with Secretary Kim", "Her Private Life", "King the Land", "Touch Your Heart", "Kiss Sixth Sense"]),
    ("Teach You a Lesson", ["Weak Hero Class 1", "Study Group", "The Glory", "Revenge of Others", "Duty after School: Part 1", "High School Return of a Gangster"]),
    ("Agent Kim Reactivated", ["Vagabond", "Healer", "The K2", "Taxi Driver", "Fifties Professionals"]),
    ("To My Beloved Thief", ["Mr. Queen", "The Tale of Nokdu", "Love in the Moonlight", "Rookie Historian Goo Hae Ryung", "Under the Queen's Umbrella", "Captivating the King"]),
    ("Four Hands, Two Sonatas", ["Do You Like Brahms?", "Heartstrings", "Beethoven Virus", "Twinkling Watermelon"]),
    ("Phantom Lawyer", ["The Uncanny Counter", "Bring It On, Ghost", "Hotel del Luna", "The Master's Sun"]),
    ("Signal", ["Tunnel", "Life on Mars", "Stranger", "Beyond Evil", "Voice"]),
    ("Hotel del Luna", ["Guardian: The Lonely and Great God", "Tale of the Nine-Tailed", "The Master's Sun", "My Demon", "Bring It On, Ghost"]),
    ("Vincenzo", ["Taxi Driver", "Big Mouth", "The Fiery Priest", "Lawless Lawyer", "Reborn Rich"]),
    ("Mr. Queen", ["Rooftop Prince", "The Crowned Clown", "Moon Lovers: Scarlet Heart Ryeo", "Bon Appetit, Your Majesty", "The Tale of Nokdu", "Love in the Moonlight"]),
    ("Kingdom", ["Joseon Exorcist", "The Haunted Palace", "Gyeongseong Creature", "All of Us Are Dead", "Happiness", "Sweet Home"]),
]

# Harder theme searches: trope phrasing fans use, often not literally in the metadata
# ("chaebol", "second lead" appear in no keyword). Expected dramas are well-known examples,
# preferring ones that carry the matching dataset tag (Found Family, Enemies to Lovers,
# Older Woman/Younger Man, Body Swap, Friends to Lovers, Contract/Fake Relationship).
# Reported separately; not part of the overall score.
# Format: (query, expected dramas)
HARD_THEME_TEST_CASES = [
    ("chaebol family", ["Reborn Rich", "Queen of Tears", "The Heirs", "Mine", "Graceful Family", "The Penthouse: War in Life", "High Society"]),
    ("second lead syndrome", ["Start-Up", "Reply 1988", "Moon Lovers: Scarlet Heart Ryeo", "True Beauty", "Boys over Flowers", "Love Alarm", "Record of Youth"]),
    ("found family", ["The Uncanny Counter", "Itaewon Class", "Prison Playbook", "Hospital Playlist", "Reply 1988", "Summer Strike"]),
    ("enemies to lovers", ["Love to Hate You", "Destined with You", "Cheese in the Trap", "So I Married an Anti-Fan", "King2Hearts", "When the Phone Rings"]),
    ("noona romance", ["Something in the Rain", "Encounter", "Romance Is a Bonus Book", "Crash Course in Romance", "Forecasting Love and Weather", "I Hear Your Voice"]),
    ("body swap", ["Secret Garden", "Alchemy of Souls", "The Heavenly Idol", "Big", "High School Return of a Gangster", "Mr. Queen"]),
    ("childhood friends to lovers", ["Fight for My Way", "Weightlifting Fairy Kim Bok Joo", "Love Next Door", "Reply 1988", "Welcome to Samdal-ri", "Reply 1997"]),
    ("fake dating", ["Business Proposal", "Love in Contract", "Marriage, Not Dating", "Full House", "Fated to Love You", "Because This Is My First Life", "When the Phone Rings"]),
    ("time slip romance", ["Lovely Runner", "Mr. Queen", "Moon Lovers: Scarlet Heart Ryeo", "Rooftop Prince", "Twinkling Watermelon", "A Time Called You", "Tomorrow with You"]),
    ("amnesia romance", ["100 Days My Prince", "Queen and I", "Extraordinary You", "Our Sticky Love", "Big", "Who Are You: School 2015"]),
    # "hidden identity" is also an exact drama title, so it stays a title search; test the trope via an alias
    ("secret identity", ["Healer", "Business Proposal", "True Beauty", "The Legend of the Blue Sea", "I'm Not a Robot", "Pinocchio"]),
    ("living together romance", ["Because This Is My First Life", "Full House", "Suspicious Partner", "My Roommate Is a Gumiho", "Romance Is a Bonus Book", "Playful Kiss"]),
    ("reincarnation", ["Tale of the Nine-Tailed", "See You in My 19th Life", "Rooftop Prince", "Death's Game", "Chicago Typewriter", "Bulgasal: Immortal Souls"]),
    ("cross dressing", ["Coffee Prince", "Love in the Moonlight", "You're Beautiful", "The Tale of Nokdu", "Sungkyunkwan Scandal", "The King's Affection"]),
    ("second chance romance", ["Queen of Tears", "Our Beloved Summer", "Go Back Couple", "Familiar Wife", "Melo Movie"]),
    ("cinderella story", ["Boys over Flowers", "Business Proposal", "The Heirs", "Secret Garden", "Coffee Prince", "Strong Woman Do Bong Soon"]),
    ("secret relationship", ["Something in the Rain", "Forecasting Love and Weather", "She Would Never Know", "Pasta", "My Dearest Nemesis"]),
    ("arranged marriage", ["Because This Is My First Life", "Mr. Queen", "100 Days My Prince", "Goong", "When the Phone Rings", "Love in Contract"]),
]

# ======================================================
# EVALUATION FUNCTIONS
# ======================================================


def is_relevant(title: str, expected: List[str]) -> bool:
    """Exact (case-insensitive) title match. Substring matching counted sequels
    like 'Hospital Playlist Season 2' as hits for 'Hospital Playlist'."""
    return title.strip().lower() in {exp.strip().lower() for exp in expected}


def calculate_precision_at_k(
    results: List[str], expected: List[str], k: int = 3
) -> float:
    """Calculate Precision@K - what % of top-k results are relevant"""
    if not expected:
        return None

    top_k = results[:k]
    relevant_count = sum(
        1 for title in top_k if is_relevant(title, expected)
    )
    return relevant_count / k


def calculate_recall_at_k(
    results: List[str], expected: List[str], k: int = 10
) -> float:
    """Calculate Recall@K - what % of expected results are in top-k"""
    if not expected:
        return None

    top_k = results[:k]
    found_count = sum(
        1 for exp in expected if any(is_relevant(title, [exp]) for title in top_k)
    )
    return found_count / len(expected)


def calculate_mrr(results: List[str], expected: List[str]) -> float:
    """Calculate Mean Reciprocal Rank - position of first relevant result"""
    if not expected:
        return None

    for i, title in enumerate(results, 1):
        if is_relevant(title, expected):
            return 1.0 / i
    return 0.0


def calculate_ndcg_at_k(results: List[str], expected: List[str], k: int = 10) -> float:
    """Calculate Normalized Discounted Cumulative Gain@K"""
    if not expected:
        return None

    dcg = 0.0
    for i, title in enumerate(results[:k], 1):
        relevance = (
            1.0 if is_relevant(title, expected) else 0.0
        )
        dcg += relevance / np.log2(i + 1)

    # Ideal DCG (all relevant results at top)
    idcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(expected), k)))

    return dcg / idcg if idcg > 0 else 0.0


# ======================================================
# TEST 1: SEARCH ACCURACY
# ======================================================


def evaluate_search_accuracy():
    """Evaluate search accuracy across different query types"""
    print("\n" + "=" * 60)
    print("TEST 1: SEARCH ACCURACY EVALUATION")
    print("=" * 60)

    results_by_category = defaultdict(
        lambda: {"precision": [], "recall": [], "mrr": [], "ndcg": []}
    )
    # Regression check: a title search lists *similar* dramas, so the searched drama
    # itself must never appear in its own results.
    self_listing_checked = 0
    self_listed = []

    for query, expected, category in SEARCH_TEST_CASES:
        try:
            params = {"title": query, "top_n": 10}
            if category in ("specific_title", "typo"):
                # Title searches (including misspelled ones) run in title_similarity mode: the backend resolves the
                # searched drama and lists *similar* dramas, excluding the drama itself.
                # debug exposes the resolved title so we can score the lookup.
                params["debug"] = "true"
            response = requests.get(f"{BASE_URL}/recommend", params=params)
            if response.status_code == 200:
                data = response.json()

                # API returns 'recommendations' not 'results'
                results = data.get("recommendations", data.get("results", []))

                if not results:
                    print(f"\n⚠ Query: '{query}' - Empty results!")
                    print(f"  Response keys: {list(data.keys())}")
                    continue

                titles = [r["Title"] for r in results]

                if category in ("specific_title", "typo"):
                    resolved =(data.get("debug") or {}).get("resolved_title")
                    if resolved:
                        self_listing_checked += 1
                        if resolved in titles:
                            self_listed.append(query)
                            print(f"\n✗ Query: '{query}' lists the searched drama '{resolved}' among its own similar results")
                        # Treat the resolved drama as the top hit, similar dramas after it.
                        titles = [resolved] + [t for t in titles if t != resolved]

                if expected:
                    precision = calculate_precision_at_k(titles, expected, k=3)
                    recall = calculate_recall_at_k(titles, expected, k=10)
                    mrr = calculate_mrr(titles, expected)
                    ndcg = calculate_ndcg_at_k(titles, expected, k=10)

                    results_by_category[category]["precision"].append(precision)
                    results_by_category[category]["recall"].append(recall)
                    results_by_category[category]["mrr"].append(mrr)
                    results_by_category[category]["ndcg"].append(ndcg)

                    print(f"\n✓ Query: '{query}' [{category}]")
                    print(f"  Top 3 Results: {titles[:3]}")
                    print(f"  Precision@3: {precision:.2%}")
                    print(f"  Recall@10: {recall:.2%}")
                    print(f"  MRR: {mrr:.3f}")
                    print(f"  NDCG@10: {ndcg:.3f}")
                else:
                    print(f"\n✓ Query: '{query}' [{category}]")
                    print(f"  Top 3 Results: {titles[:3]}")
            else:
                print(f"\n✗ Query: '{query}' - Failed (Status: {response.status_code})")
        except Exception as e:
            print(
                f"\n✗ Query: '{query}' - Error: {e}"
            )  # Calculate average metrics per category
    print("\n" + "-" * 60)
    print(
        f"TITLE SELF-EXCLUSION: {self_listing_checked - len(self_listed)}/{self_listing_checked} "
        "title searches keep the searched drama out of its own similar list"
    )
    if self_listed:
        print(f"  ✗ Self-listed: {self_listed}")
    print("-" * 60)
    print("SEARCH ACCURACY BY CATEGORY:")
    print("-" * 60)

    overall_precision = []
    overall_recall = []
    overall_mrr = []
    overall_ndcg = []

    for category, metrics in results_by_category.items():
        avg_precision = np.mean(metrics["precision"]) if metrics["precision"] else 0
        avg_recall = np.mean(metrics["recall"]) if metrics["recall"] else 0
        avg_mrr = np.mean(metrics["mrr"]) if metrics["mrr"] else 0
        avg_ndcg = np.mean(metrics["ndcg"]) if metrics["ndcg"] else 0

        print(f"\n{category.upper()}:")
        print(f"  Precision@3: {avg_precision:.2%}")
        print(f"  Recall@10: {avg_recall:.2%}")
        print(f"  MRR: {avg_mrr:.3f}")
        print(f"  NDCG@10: {avg_ndcg:.3f}")

        overall_precision.extend(metrics["precision"])
        overall_recall.extend(metrics["recall"])
        overall_mrr.extend(metrics["mrr"])
        overall_ndcg.extend(metrics["ndcg"])

    # Overall metrics
    print("\n" + "-" * 60)
    print("OVERALL SEARCH ACCURACY:")
    print("-" * 60)
    print(f"Precision@3: {np.mean(overall_precision):.2%}")
    print(f"Recall@10: {np.mean(overall_recall):.2%}")
    print(f"MRR: {np.mean(overall_mrr):.3f}")
    print(f"NDCG@10: {np.mean(overall_ndcg):.3f}")

    return {
        "precision": np.mean(overall_precision),
        "recall": np.mean(overall_recall),
        "mrr": np.mean(overall_mrr),
        "ndcg": np.mean(overall_ndcg),
    }


def evaluate_franchise_ordering():
    """Check that other seasons of the searched drama come first, and nothing else is grouped."""
    print("\n" + "-" * 60)
    print("FRANCHISE ORDERING:")
    print("-" * 60)
    passed = 0
    for query, expected in FRANCHISE_TEST_CASES:
        try:
            response = requests.get(
                f"{BASE_URL}/recommend", params={"title": query, "top_n": 10, "debug": "true"}
            )
            data = response.json()
            titles = [r["Title"] for r in data.get("recommendations", [])]
            grouped = (data.get("debug") or {}).get("franchise_titles") or []
            ok = titles[: len(expected)] == expected and grouped == expected
        except Exception as e:
            titles, ok = [f"error: {e}"], False
        passed += ok
        print(f"  {'✓' if ok else '✗'} '{query}' -> {titles[:len(expected) + 1]}")
    print(f"FRANCHISE ORDERING: {passed}/{len(FRANCHISE_TEST_CASES)} passed")
    return passed, len(FRANCHISE_TEST_CASES)


def evaluate_similar_dramas():
    """Similar-drama quality for non-curated seeds. Other seasons of the seed are
    skipped so franchise ordering doesn't count for or against it."""
    print("\n" + "-" * 60)
    print("SIMILAR DRAMAS (non-curated seeds):")
    print("-" * 60)
    hits5, recalls = [], []
    for seed, expected in SIMILAR_TEST_CASES:
        try:
            data = requests.get(
                f"{BASE_URL}/recommend", params={"title": seed, "top_n": 15, "debug": "true"}
            ).json()
            siblings = set((data.get("debug") or {}).get("franchise_titles") or [])
            titles = [r["Title"] for r in data.get("recommendations", []) if r["Title"] not in siblings][:10]
        except Exception as e:
            print(f"  ✗ '{seed}' - Error: {e}")
            hits5.append(0.0); recalls.append(0.0)
            continue
        p5 = sum(is_relevant(t, expected) for t in titles[:5]) / 5
        r10 = calculate_recall_at_k(titles, expected, k=10)
        hits5.append(p5); recalls.append(r10)
        print(f"  {seed:30} P@5 {p5:.0%}  R@10 {r10:.0%}  top5={titles[:5]}")
    p5, r10 = float(np.mean(hits5)), float(np.mean(recalls))
    print(f"SIMILAR DRAMAS: Precision@5 {p5:.2%} | Recall@10 {r10:.2%}")
    return p5, r10


def evaluate_hard_themes():
    """Trope searches whose wording is mostly absent from the metadata."""
    print("\n" + "-" * 60)
    print("HARD THEMES (trope phrasing):")
    print("-" * 60)
    hits5, recalls = [], []
    for query, expected in HARD_THEME_TEST_CASES:
        try:
            data = requests.get(f"{BASE_URL}/recommend", params={"title": query, "top_n": 10}).json()
            titles = [r["Title"] for r in data.get("recommendations", [])]
        except Exception as e:
            print(f"  ✗ '{query}' - Error: {e}")
            titles = []
        p5 = sum(is_relevant(t, expected) for t in titles[:5]) / 5
        r10 = calculate_recall_at_k(titles, expected, k=10)
        hits5.append(p5); recalls.append(r10)
        print(f"  {query:30} P@5 {p5:.0%}  R@10 {r10:.0%}  top5={titles[:5]}")
    p5, r10 = float(np.mean(hits5)), float(np.mean(recalls))
    print(f"HARD THEMES: Precision@5 {p5:.2%} | Recall@10 {r10:.2%}")
    return p5, r10


# ======================================================
# TEST 2: QUERY INTELLIGENCE
# ======================================================


def evaluate_query_intelligence():
    """Evaluate query analyzer and genre detection"""
    print("\n" + "=" * 60)
    print("TEST 2: QUERY INTELLIGENCE EVALUATION")
    print("=" * 60)

    correct_detections = 0
    total_tests = len(GENRE_DETECTION_TESTS)

    for query, expected_genres in GENRE_DETECTION_TESTS:
        try:
            response = requests.get(f"{BASE_URL}/analyze", params={"query": query})
            if response.status_code == 200:
                data = response.json()
                detected_genres = data.get("detected_genres", [])

                # Check if at least one expected genre was detected
                matches = [g for g in expected_genres if g in detected_genres]
                accuracy = len(matches) / len(expected_genres)

                if accuracy >= 0.5:  # At least 50% of expected genres detected
                    correct_detections += 1
                    status = "✓"
                else:
                    status = "✗"

                print(f"\n{status} Query: '{query}'")
                print(f"  Expected: {expected_genres}")
                print(f"  Detected: {detected_genres}")
                print(f"  Intent: {data.get('intent', 'unknown')}")
                print(f"  Accuracy: {accuracy:.1%}")
            else:
                print(f"\n✗ Query: '{query}' - Failed")
        except Exception as e:
            print(f"\n✗ Query: '{query}' - Error: {e}")

    accuracy = correct_detections / total_tests
    print("\n" + "-" * 60)
    print(f"QUERY INTELLIGENCE ACCURACY: {accuracy:.2%}")
    print("-" * 60)

    return accuracy


# ======================================================
# TEST 3: FILTER ACCURACY
# ======================================================


def evaluate_filter_accuracy():
    """Evaluate filtering accuracy"""
    print("\n" + "=" * 60)
    print("TEST 3: FILTER ACCURACY EVALUATION")
    print("=" * 60)

    passed_tests = 0
    total_tests = len(FILTER_TEST_CASES)

    for test_case in FILTER_TEST_CASES:
        filter_params = {
            k: v for k, v in test_case.items() if not k.startswith("expected_")
        }
        filter_params["title"] = "drama"  # Generic query
        filter_params["top_n"] = 20

        try:
            response = requests.get(f"{BASE_URL}/recommend", params=filter_params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("recommendations", data.get("results", []))

                # Validate filter worked
                test_passed = True

                if (
                    "expected_all_match" in test_case
                    and test_case["expected_all_match"]
                ):
                    genre = test_case.get("genre")
                    if genre:
                        for r in results:
                            if genre.lower() not in r.get("Genre", "").lower():
                                test_passed = False
                                break

                if "expected_min_rating" in test_case:
                    min_rating = test_case["expected_min_rating"]
                    for r in results:
                        rating = float(r.get("rating_value", r.get("score", 0)))
                        if rating < min_rating:
                            test_passed = False
                            break

                if "expected_year" in test_case:
                    year = test_case["expected_year"]
                    for r in results:
                        # Metadata stores the aired range, e.g. "Dec 10, 2019 - Jan 11, 2020"
                        aired_years = [
                            int(y)
                            for y in re.findall(
                                r"\b(?:19|20)\d{2}\b", str(r.get("Release Years", ""))
                            )
                        ]
                        if not aired_years or not (
                            min(aired_years) <= year <= max(aired_years)
                        ):
                            test_passed = False
                            break

                if test_passed:
                    passed_tests += 1
                    status = "✓"
                else:
                    status = "✗"

                print(f"\n{status} Filter: {filter_params}")
                print(f"  Results: {len(results)}")
                print(f"  Sample: {results[0]['Title'] if results else 'None'}")
            else:
                print(f"\n✗ Filter test failed - Status: {response.status_code}")
        except Exception as e:
            print(f"\n✗ Filter test error: {e}")

    accuracy = passed_tests / total_tests
    print("\n" + "-" * 60)
    print(f"FILTER ACCURACY: {accuracy:.2%}")
    print("-" * 60)

    return accuracy


# ======================================================
# TEST 4: PERSONALIZATION EFFECTIVENESS
# ======================================================


def evaluate_personalization():
    """Evaluate personalization boost effectiveness"""
    print("\n" + "=" * 60)
    print("TEST 4: PERSONALIZATION EFFECTIVENESS")
    print("=" * 60)

    test_user = f"test_user_{int(time.time())}"

    # Rate some medical dramas highly
    medical_dramas = ["Hospital Playlist", "Doctor Cha", "Good Doctor"]

    print(f"\nCreating test user: {test_user}")
    print("Rating medical dramas highly (9.0/10)...")

    for drama in medical_dramas:
        try:
            response = requests.post(
                f"{BASE_URL}/profile/{test_user}/rate",
                params={"drama_title": drama, "rating": 9.0},
            )
            if response.status_code == 200:
                print(f"  ✓ Rated: {drama}")
        except:
            pass

    time.sleep(1)

    # Test 1: Search without personalization
    print("\n1. Search WITHOUT personalization (medical drama):")
    try:
        response = requests.get(
            f"{BASE_URL}/recommend", params={"title": "medical drama", "top_n": 10}
        )
        if response.status_code == 200:
            data = response.json()
            results_no_personal = data.get("recommendations", data.get("results", []))
            medical_count_no_personal = sum(
                1 for r in results_no_personal if "Medical" in r.get("Genre", "")
            )
            print(f"   Medical dramas in top 10: {medical_count_no_personal}")
    except Exception as e:
        print(f"   Error: {e}")
        return 0.0

    # Test 2: Search with personalization
    print("\n2. Search WITH personalization (medical drama):")
    try:
        response = requests.get(
            f"{BASE_URL}/recommend",
            params={"title": "medical drama", "top_n": 10, "user_id": test_user},
        )
        if response.status_code == 200:
            data = response.json()
            results_personal = data.get("recommendations", data.get("results", []))
            medical_count_personal = sum(
                1 for r in results_personal if "Medical" in r.get("Genre", "")
            )
            boost_info = data.get("personalization_info", {})

            print(f"   Medical dramas in top 10: {medical_count_personal}")
            print(f"   Boost applied: {boost_info.get('boost_applied', False)}")
            print(f"   Avg boost: {boost_info.get('average_boost', 1.0):.2f}x")

            # Check for boosted dramas
            boosted_count = sum(
                1 for r in results_personal if r.get("boost_multiplier", 1.0) > 1.05
            )
            print(f"   Boosted dramas: {boosted_count}")
    except Exception as e:
        print(f"   Error: {e}")
        return 0.0

    # Calculate effectiveness
    improvement = medical_count_personal - medical_count_no_personal
    # Effectiveness based on both absolute count and improvement
    baseline_pct = (medical_count_no_personal / 10.0) * 100
    personal_pct = (medical_count_personal / 10.0) * 100

    # If baseline is already high (>60%), check if personalization maintains/improves it
    if baseline_pct >= 60:
        effectiveness = (
            personal_pct if personal_pct >= baseline_pct else baseline_pct * 0.5
        )
    else:
        # For low baseline, measure improvement
        effectiveness = personal_pct

    print("\n" + "-" * 60)
    print(f"PERSONALIZATION EFFECTIVENESS:")
    print(
        f"  Baseline: {medical_count_no_personal} medical dramas ({baseline_pct:.1f}%)"
    )
    print(
        f"  With Personalization: {medical_count_personal} medical dramas ({personal_pct:.1f}%)"
    )
    print(f"  Improvement: +{improvement} dramas")
    print(f"  Effectiveness Score: {effectiveness / 100:.2%}")
    print("-" * 60)

    # Cleanup
    try:
        requests.delete(f"{BASE_URL}/profile/{test_user}")
    except:
        pass

    return effectiveness / 100


# ======================================================
# TEST 5: RESPONSE TIME & PERFORMANCE
# ======================================================


def evaluate_performance():
    """Evaluate system response time"""
    print("\n" + "=" * 60)
    print("TEST 5: PERFORMANCE EVALUATION")
    print("=" * 60)

    test_queries = [
        "Crash Landing on You",
        "medical drama",
        "romantic comedy with strong female lead",
        "best korean series",
    ]

    response_times = []

    for query in test_queries:
        try:
            start = time.time()
            response = requests.get(
                f"{BASE_URL}/recommend", params={"title": query, "top_n": 10}
            )
            end = time.time()

            if response.status_code == 200:
                response_time = (end - start) * 1000  # ms
                response_times.append(response_time)
                print(f"  Query: '{query}' - {response_time:.0f}ms")
        except Exception as e:
            print(f"  Query: '{query}' - Error: {e}")

    if response_times:
        avg_time = np.mean(response_times)
        print("\n" + "-" * 60)
        print(f"AVERAGE RESPONSE TIME: {avg_time:.0f}ms")
        print(f"MIN: {min(response_times):.0f}ms | MAX: {max(response_times):.0f}ms")
        print("-" * 60)

        return avg_time

    return 0


# ======================================================
# MAIN EVALUATION
# ======================================================


def main():
    """Run all evaluations and generate report"""
    print("\n" + "=" * 60)
    print("SEOULMATE RECOMMENDATION SYSTEM - ACCURACY EVALUATION")
    print("=" * 60)
    print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {BASE_URL}")

    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("\n❌ ERROR: API is not running!")
            print("Please start the backend: python backend/app.py")
            return
    except:
        print("\n❌ ERROR: Cannot connect to API!")
        print("Please start the backend: python backend/app.py")
        return

    # Run all tests
    search_metrics = evaluate_search_accuracy()
    franchise_passed, franchise_total = evaluate_franchise_ordering()
    similar_p5, similar_r10 = evaluate_similar_dramas()
    hard_p5, hard_r10 = evaluate_hard_themes()
    query_intelligence = evaluate_query_intelligence()
    filter_accuracy = evaluate_filter_accuracy()
    personalization = evaluate_personalization()
    avg_response_time = evaluate_performance()

    # Generate final report
    print("\n" + "=" * 60)
    print("FINAL ACCURACY REPORT")
    print("=" * 60)

    print(f"\n📊 SEARCH ACCURACY:")
    print(f"  ├─ Precision@3: {search_metrics['precision']:.2%}")
    print(f"  ├─ Recall@10: {search_metrics['recall']:.2%}")
    print(f"  ├─ MRR: {search_metrics['mrr']:.3f}")
    print(f"  ├─ NDCG@10: {search_metrics['ndcg']:.3f}")
    print(f"  ├─ Franchise ordering: {franchise_passed}/{franchise_total}")
    print(f"  ├─ Similar dramas (non-curated): P@5 {similar_p5:.2%}, R@10 {similar_r10:.2%}")
    print(f"  └─ Hard themes (tropes): P@5 {hard_p5:.2%}, R@10 {hard_r10:.2%}")

    print(f"\n🧠 QUERY INTELLIGENCE:")
    print(f"  └─ Genre Detection: {query_intelligence:.2%}")

    print(f"\n🔍 FILTER ACCURACY:")
    print(f"  └─ Filter Success Rate: {filter_accuracy:.2%}")

    print(f"\n👤 PERSONALIZATION:")
    print(f"  └─ Effectiveness: {personalization:.2%}")

    print(f"\n⚡ PERFORMANCE:")
    print(f"  └─ Avg Response Time: {avg_response_time:.0f}ms")

    # Calculate overall score
    overall_score = (
        search_metrics["precision"] * 0.3
        + search_metrics["ndcg"] * 0.2
        + query_intelligence * 0.15
        + filter_accuracy * 0.15
        + personalization * 0.2
    )

    print(f"\n{'='*60}")
    print(f"🎯 OVERALL SYSTEM ACCURACY: {overall_score:.2%}")
    print(f"{'='*60}")

    # Grade
    if overall_score >= 0.90:
        grade = "A+"
    elif overall_score >= 0.85:
        grade = "A"
    elif overall_score >= 0.80:
        grade = "B+"
    elif overall_score >= 0.75:
        grade = "B"
    else:
        grade = "C"

    print(f"\n📈 SYSTEM GRADE: {grade}")

    if overall_score >= 0.90:
        print("✨ Excellent! System is performing at high accuracy.")
    elif overall_score >= 0.80:
        print("👍 Good! System is performing well with room for improvement.")
    else:
        print("⚠️ System needs optimization to improve accuracy.")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
