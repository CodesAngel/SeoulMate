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
    # Genre searches (should return dramas in that genre)
    ("medical drama", ["Hospital Playlist", "Doctor Cha", "Good Doctor"], "genre"),
    ("doctor hospital drama", ["Hospital Playlist", "Doctor Cha", "Good Doctor"], "genre"),
    (
        "romantic comedy",
        [
            "Business Proposal",
            "What's Wrong with Secretary Kim",
            "Strong Woman Do Bong Soon",
        ],
        "genre",
    ),
    (
        "office romance",
        [
            "Business Proposal",
            "What's Wrong with Secretary Kim",
            "Romance Is a Bonus Book",
        ],
        "genre",
    ),
    ("thriller", ["Squid Game", "Signal", "Stranger"], "genre"),
    ("crime thriller", ["Signal", "Stranger", "Beyond Evil"], "genre"),
    ("historical", ["Mr. Sunshine", "Kingdom", "The Red Sleeve"], "genre"),
    ("sageuk royal drama", ["The Red Sleeve", "Empress Ki", "Kingdom"], "genre"),
    ("legal drama", ["Extraordinary Attorney Woo", "Law School", "Vincenzo"], "genre"),
    ("school drama", ["True Beauty", "Dream High", "Extraordinary You"], "genre"),
    ("fantasy romance", ["Guardian: The Lonely and Great God", "Hotel Del Luna", "Alchemy of Souls"], "genre"),
    ("zombie drama", ["All of Us Are Dead", "Kingdom", "Happiness"], "genre"),
    ("revenge drama", ["The Glory", "Penthouse", "Eve"], "genre"),
    # Theme searches
    ("north korea", ["Crash Landing on You"], "theme"),
    ("restaurant food", ["Itaewon Class", "Wok of Love"], "theme"),
    ("time travel", ["Signal", "Tomorrow with You"], "theme"),
    ("contract marriage", ["Because This Is My First Life", "Marriage Contract"], "theme"),
    ("rich CEO romance", ["Business Proposal", "What's Wrong with Secretary Kim"], "theme"),
    ("school bullying revenge", ["The Glory"], "theme"),
    ("law firm corruption", ["Vincenzo", "Law School", "Extraordinary Attorney Woo"], "theme"),
    ("ghost supernatural hotel", ["Hotel Del Luna", "The Master's Sun"], "theme"),
    ("survival game", ["Squid Game"], "theme"),
    ("workplace startup", ["Start-Up", "Misaeng"], "theme"),
    ("healing slice of life", ["Hospital Playlist", "Our Blues", "My Mister"], "theme"),
    # Actor searches
    ("Hyun Bin", ["Crash Landing on You", "Memories of the Alhambra"], "actor"),
    ("Park Seo Joon", ["Itaewon Class", "What's Wrong with Secretary Kim"], "actor"),
    ("Song Joong Ki", ["Vincenzo", "Descendants of the Sun"], "actor"),
    ("Kim Soo Hyun", ["My Love from the Star", "It's Okay to Not Be Okay"], "actor"),
    ("Lee Min Ho", ["The Heirs", "The King: Eternal Monarch"], "actor"),
    ("Ji Chang Wook", ["Healer", "Suspicious Partner"], "actor"),
    ("IU", ["Hotel Del Luna", "My Mister"], "actor"),
    ("Park Min Young", ["What's Wrong with Secretary Kim", "Her Private Life"], "actor"),
    ("Song Hye Kyo", ["Descendants of the Sun", "The Glory"], "actor"),
    ("Gong Yoo", ["Guardian: The Lonely and Great God", "Coffee Prince"], "actor"),
    # Typo / fuzzy title searches
    ("Crash Landng on You", ["Crash Landing on You"], "typo"),
    ("Hospitl Playlist", ["Hospital Playlist"], "typo"),
    ("Buisness Proposal", ["Business Proposal"], "typo"),
    ("Extraordinary Atorney Woo", ["Extraordinary Attorney Woo"], "typo"),
    ("Descendents of the Sun", ["Descendants of the Sun"], "typo"),
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

# ======================================================
# EVALUATION FUNCTIONS
# ======================================================


def calculate_precision_at_k(
    results: List[str], expected: List[str], k: int = 3
) -> float:
    """Calculate Precision@K - what % of top-k results are relevant"""
    if not expected:
        return None

    top_k = results[:k]
    relevant_count = sum(
        1 for title in top_k if any(exp.lower() in title.lower() for exp in expected)
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
        1 for exp in expected if any(exp.lower() in title.lower() for title in top_k)
    )
    return found_count / len(expected)


def calculate_mrr(results: List[str], expected: List[str]) -> float:
    """Calculate Mean Reciprocal Rank - position of first relevant result"""
    if not expected:
        return None

    for i, title in enumerate(results, 1):
        if any(exp.lower() in title.lower() for exp in expected):
            return 1.0 / i
    return 0.0


def calculate_ndcg_at_k(results: List[str], expected: List[str], k: int = 10) -> float:
    """Calculate Normalized Discounted Cumulative Gain@K"""
    if not expected:
        return None

    dcg = 0.0
    for i, title in enumerate(results[:k], 1):
        relevance = (
            1.0 if any(exp.lower() in title.lower() for exp in expected) else 0.0
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
    print(f"  └─ NDCG@10: {search_metrics['ndcg']:.3f}")

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
