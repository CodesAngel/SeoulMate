"""Match every SeoulMate drama to its TMDB TV show id.

Only the ids are saved (frontend-web/src/data/tmdb-ids.json). The drama page
asks TMDB for the poster list at render time and caches it for a week, so no
TMDB images or text are stored here (TMDB terms: no caching past 6 months).

Key: TMDB_API_KEY (v3 key) from the environment or frontend-web/.env.local.

    .venv/Scripts/python.exe scripts/match_tmdb.py            # all dramas
    .venv/Scripts/python.exe scripts/match_tmdb.py --limit 40 # quick trial

Writes a review report to data/tmdb/tmdb_matches.csv (gitignored data/).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from rapidfuzz import fuzz

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "final" / "kdrama_dataset.csv"
IDS_OUT = ROOT / "frontend-web" / "src" / "data" / "tmdb-ids.json"
REPORT_OUT = ROOT / "data" / "tmdb" / "tmdb_matches.csv"
API = "https://api.themoviedb.org/3"
HANGUL = re.compile(r"[가-힣]")


def load_key() -> str:
    key = os.environ.get("TMDB_API_KEY", "").strip()
    env_file = ROOT / "frontend-web" / ".env.local"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("TMDB_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit("TMDB_API_KEY not found (environment or frontend-web/.env.local)")
    return key


def first_year(aired) -> int | None:
    m = re.search(r"\b(?:19|20)\d{2}\b", str(aired or ""))
    return int(m.group(0)) if m else None


def norm(s: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", s.lower())


class Tmdb:
    def __init__(self, key: str):
        self.key = key
        self.local = threading.local()

    def get(self, path: str, **params) -> dict:
        s = getattr(self.local, "s", None)
        if s is None:
            s = self.local.s = requests.Session()
        params["api_key"] = self.key
        for attempt in range(5):
            r = s.get(f"{API}{path}", params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"rate limited: {path}")


def candidates(tmdb: Tmdb, names: list[str], year: int | None) -> dict[int, dict]:
    found: dict[int, dict] = {}
    queries = [(n, year) for n in names[:3]] + [(names[0], None)]
    for query, y in queries:
        params = {"query": query, "include_adult": "false"}
        if y:
            params["first_air_date_year"] = y
        for c in tmdb.get("/search/tv", **params).get("results", [])[:10]:
            korean = "KR" in (c.get("origin_country") or []) or c.get("original_language") == "ko"
            if korean:
                found.setdefault(c["id"], c)
        if found and y:
            break
    return found


def score(c: dict, names: list[str], year: int | None) -> tuple[float, float, int | None]:
    theirs = [norm(c.get("name", "")), norm(c.get("original_name", ""))]
    sim = max((fuzz.ratio(norm(n), t) for n in names for t in theirs if t and norm(n)), default=0)
    cy = first_year(c.get("first_air_date"))
    if year and cy:
        bonus = 20 if cy == year else 5 if abs(cy - year) == 1 else -40
    else:
        bonus = -10
    return sim + bonus, sim, cy


def match_one(tmdb: Tmdb, row) -> dict:
    title = str(row.title)
    alts = [a.strip() for a in str(row.alternate_names or "").split(",") if a.strip()]
    korean = [a for a in alts if HANGUL.search(a)]
    names = [title] + korean + [a for a in alts if a not in korean]
    year = first_year(row.aired)
    out = {"key": f"{title}|{year or ''}", "title": title, "year": year or "",
           "tmdb_id": "", "tmdb_name": "", "tmdb_year": "", "name_sim": 0,
           "episodes": row.episodes, "tmdb_episodes": "", "posters": 0, "confidence": "none"}
    try:
        cands = candidates(tmdb, [title] + korean, year)
        if not cands:
            return out
        best = max(cands.values(), key=lambda c: score(c, names, year)[0])
        total, sim, cy = score(best, names, year)
        detail = tmdb.get(f"/tv/{best['id']}", append_to_response="images",
                          include_image_language="ko,en,null")
        eps = detail.get("number_of_episodes")
        ours = int(row.episodes) if str(row.episodes).isdigit() else None
        eps_ok = not (eps and ours) or abs(eps - ours) <= max(2, round(0.15 * ours))
        year_exact = bool(year and cy == year)
        year_near = bool(year and cy and abs(cy - year) <= 1)
        if sim >= 90 and year_exact and eps_ok:
            conf = "high"
        # Same name + same year is enough even if TMDB counts episodes differently
        # (split broadcasts); a year off by one also needs the episode count to agree.
        elif (sim >= 75 and year_near and eps_ok) or (sim >= 90 and year_exact):
            conf = "medium"
        else:
            conf = "low"
        out.update(tmdb_id=best["id"], tmdb_name=best.get("name", ""), tmdb_year=cy or "",
                   name_sim=round(sim), tmdb_episodes=eps or "",
                   posters=len((detail.get("images") or {}).get("posters") or []),
                   confidence=conf)
    except Exception as exc:  # keep going; the report shows the error
        out["confidence"] = f"error: {exc}"[:120]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    tmdb = Tmdb(load_key())
    df = pd.read_csv(DATASET)
    if args.limit:
        df = df.sample(n=min(args.limit, len(df)), random_state=7)
    rows = list(df.itertuples(index=False))

    results = []
    with ThreadPoolExecutor(args.workers) as pool:
        for i, res in enumerate(pool.map(lambda r: match_one(tmdb, r), rows), 1):
            results.append(res)
            if i % 100 == 0:
                print(f"  {i}/{len(rows)}", flush=True)

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0]))
        w.writeheader()
        w.writerows(sorted(results, key=lambda r: (r["confidence"], r["title"])))

    counts: dict[str, int] = {}
    for r in results:
        counts[r["confidence"].split(":")[0]] = counts.get(r["confidence"].split(":")[0], 0) + 1
    print("confidence:", counts)
    good = [r for r in results if r["confidence"] in ("high", "medium")]
    print(f"with 2+ posters: {sum(1 for r in good if r['posters'] >= 2)} of {len(good)} matched")

    if args.limit:
        print(f"trial run: report only -> {REPORT_OUT}")
        return
    ids = {r["key"]: int(r["tmdb_id"]) for r in sorted(good, key=lambda r: r["key"])}
    IDS_OUT.parent.mkdir(parents=True, exist_ok=True)
    IDS_OUT.write_text(json.dumps(ids, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"wrote {len(ids)} ids -> {IDS_OUT}")


if __name__ == "__main__":
    main()
