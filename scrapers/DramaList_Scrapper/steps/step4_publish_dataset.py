# Merge the scraper's cleaned K-drama CSV into data/final/kdrama_dataset.csv.
#
# A drama is identified by MyDramaList's permanent numeric ID, the number at the start of
# its `url` (https://mydramalist.com/100-my-fair-lady -> 100). Rows without a matching ID
# (the live file had no `url` column before 2026-10-21) fall back to the poster image ID
# (https://i.mydramalist.com/9oX6Gf.jpg -> 9oX6Gf, the database source_key in
# scripts/import_catalog.py), then to normalised (title, aired), then to title alone (see
# merge()), so a changed poster URL or air date is still recognised as the same drama.
#
# If the scraped CSV has a `url` column and the live file doesn't, the column is added once.
#
# Merge rules:
#   - Existing rows keep their order; new dramas are appended at the end.
#   - Dramas missing from the scrape are kept, never deleted.
#   - A field that comes back blank keeps its old value.
#   - A changed poster URL is held back (old `image` kept): changing it would change the
#     drama's database identity. Held-back posters are listed in the report.
#
# The merged file is written as a candidate next to the live file and validated. Only if
# every check passes is the live file copied to kdrama_dataset.prev.csv and replaced.
# A JSON report records what changed and whether the index needs rebuilding.
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[3]
SCRAPER_DIR = PROJECT_DIR / "scrapers" / "DramaList_Scrapper"
DEFAULT_SOURCE = SCRAPER_DIR / "output" / "by_country" / "cleaned" / "kdrama_dataset.csv"
DEFAULT_TARGET = PROJECT_DIR / "data" / "final" / "kdrama_dataset.csv"
DEFAULT_REPORT = PROJECT_DIR / "data" / "reports" / "dataset_publish_report.json"

# Columns that go into the embedding text (training/steps/step3_build_index.py). A change
# here means the FAISS index must be rebuilt; a change elsewhere only affects metadata.
EMBEDDING_COLUMNS = [
    "title",
    "genres",
    "description",
    "actors",
    "directors",
    "alternate_names",
    "publisher",
    "aired",
    "keywords",
]
# `aired` may be blank (dramas without a confirmed air date), so it isn't required.
REQUIRED_COLUMNS = ["title", "description", "image"]

PKT = timezone(timedelta(hours=5), "PKT")


def image_id(url):
    return os.path.splitext(os.path.basename(urlparse(str(url).strip()).path))[0]


def mdl_id(url):
    """'https://mydramalist.com/100-my-fair-lady' -> '100'; '' when there is no URL."""
    slug = str(url or "").strip().rstrip("/").split("/")[-1]
    number = slug.split("-", 1)[0]
    return number if number.isdigit() else ""


def title_key(title, aired):
    clean = lambda value: re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return clean(title), clean(aired)


def is_blank(value):
    return str(value).strip() == ""


def read_dataset(path):
    return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)


def merge(current, scraped):
    """Return (merged rows, stats). `current` keeps its order; new rows go last."""
    by_mdl = {mdl_id(row.get("url")): i for i, row in enumerate(current) if mdl_id(row.get("url"))}
    by_id = {image_id(row["image"]): i for i, row in enumerate(current)}
    by_key = {title_key(row["title"], row["aired"]): i for i, row in enumerate(current)}

    merged = [dict(row) for row in current]
    matched, new_ids = set(), set()
    stats = {
        "new": [],
        "updated": [],
        "matched_by_title_only": [],
        "poster_held_back": [],
        "duplicates_in_scrape": [],
    }

    # Pass 1: match on MyDramaList ID, then image ID, then (title, aired).
    leftovers = []
    for row in scraped:
        index = by_mdl.get(mdl_id(row.get("url")))
        if index is None:
            index = by_id.get(image_id(row["image"]))
        if index is None:
            index = by_key.get(title_key(row["title"], row["aired"]))
        if index is None:
            leftovers.append(row)
        elif index in matched:
            stats["duplicates_in_scrape"].append(row["title"])
        else:
            matched.add(index)
            update_row(merged[index], row, stats)

    # Pass 2: a drama whose poster and air date both changed (typical once an upcoming
    # drama is confirmed) matches neither key. Match it on title alone, but only when
    # exactly one existing drama with that title is still unmatched; a different drama
    # sharing the title would already have matched by its own image ID in pass 1.
    unmatched_by_title = {}
    for i, row in enumerate(current):
        if i not in matched:
            unmatched_by_title.setdefault(title_key(row["title"], "")[0], []).append(i)

    for row in leftovers:
        pid = image_id(row["image"])
        candidates = unmatched_by_title.get(title_key(row["title"], "")[0], [])
        if len(candidates) == 1 and candidates[0] not in matched:
            index = candidates[0]
            matched.add(index)
            stats["matched_by_title_only"].append(
                {"title": row["title"], "old_aired": current[index]["aired"], "new_aired": row["aired"]}
            )
            update_row(merged[index], row, stats)
        elif pid in new_ids:
            stats["duplicates_in_scrape"].append(row["title"])
        else:
            new_ids.add(pid)
            merged.append(dict(row))
            stats["new"].append({"title": row["title"], "aired": row["aired"], "image_id": pid})

    stats["missing_from_scrape"] = len(current) - len(matched)
    return merged, stats


def update_row(old, row, stats):
    """Copy non-blank changed fields from `row` into `old`, holding back poster changes."""
    changed = []
    for column, value in row.items():
        if is_blank(value) or value == old[column]:
            continue
        if column == "image":
            stats["poster_held_back"].append({"title": old["title"], "old": old["image"], "new": value})
            continue
        old[column] = value
        changed.append(column)
    if changed:
        stats["updated"].append({"title": old["title"], "image_id": image_id(old["image"]), "fields": changed})


def validate(merged, current_count, columns, max_new):
    errors = []
    df = pd.DataFrame(merged, columns=columns)

    for column in REQUIRED_COLUMNS:
        blank = df[column].map(is_blank)
        if blank.any():
            errors.append(f"{blank.sum()} rows with an empty '{column}'")

    ids = df["image"].map(image_id)
    duplicate_ids = sorted(ids[ids.duplicated() & (ids != "")].unique())
    if duplicate_ids:
        errors.append(f"duplicate image IDs: {duplicate_ids[:10]}")

    if "url" in df.columns:
        mdl_ids = Counter(mdl_id(url) for url in df["url"] if mdl_id(url))
        duplicate_mdl = sorted(i for i, count in mdl_ids.items() if count > 1)
        if duplicate_mdl:
            errors.append(f"duplicate MyDramaList IDs: {duplicate_mdl[:10]}")

    keys = Counter(title_key(t, a) for t, a in zip(df["title"], df["aired"]))
    duplicate_keys = sorted(k for k, count in keys.items() if count > 1)
    if duplicate_keys:
        errors.append(f"duplicate (title, aired): {duplicate_keys[:10]}")

    if len(df) < current_count:
        errors.append(f"row count dropped: {current_count} -> {len(df)}")
    if len(df) - current_count > max_new:
        errors.append(
            f"{len(df) - current_count} new dramas exceeds --max-new {max_new}; "
            "check the scrape, then re-run with a higher limit"
        )
    return errors


def write_csv(rows, columns, path, line_ending):
    pd.DataFrame(rows, columns=columns).to_csv(
        path, index=False, encoding="utf-8-sig", lineterminator=line_ending
    )


def publish_dataset(source, target, report_path, max_new=300, dry_run=False):
    """Merge `source` into `target`. Returns the report dict; raises on failed validation."""
    source, target, report_path = Path(source), Path(target), Path(report_path)
    current_df = read_dataset(target)
    scraped_df = read_dataset(source)
    columns = list(current_df.columns)
    scraped_columns = list(scraped_df.columns)

    added_columns = []
    if (
        "url" in scraped_columns
        and "url" not in columns
        and [c for c in scraped_columns if c != "url"] == columns
    ):
        # One-time migration: the live file gains the `url` column, in the scraper's order.
        current_df.insert(scraped_columns.index("url"), "url", "")
        columns, added_columns = scraped_columns, ["url"]
    if scraped_columns != columns:
        raise ValueError(f"Column mismatch.\n  {target.name}: {columns}\n  {source}: {scraped_columns}")

    merged, stats = merge(current_df.to_dict("records"), scraped_df.to_dict("records"))
    errors = validate(merged, len(current_df), columns, max_new)

    changed_fields = {f for item in stats["updated"] for f in item["fields"]}
    report = {
        "run_at": datetime.now(PKT).isoformat(timespec="seconds"),
        "source": str(source),
        "target": str(target),
        "dry_run": dry_run,
        "rows_before": len(current_df),
        "rows_after": len(merged),
        "scraped_rows": len(scraped_df),
        "new_count": len(stats["new"]),
        "updated_count": len(stats["updated"]),
        "missing_from_scrape": stats["missing_from_scrape"],
        "embedding_text_changed": bool(stats["new"]) or bool(changed_fields & set(EMBEDDING_COLUMNS)),
        "metadata_changed": bool(stats["new"]) or bool(changed_fields) or bool(added_columns),
        "added_columns": added_columns,
        "changed_fields": sorted(changed_fields),
        "errors": errors,
        "published": False,
        **{
            key: stats[key]
            for key in ("new", "updated", "matched_by_title_only", "poster_held_back", "duplicates_in_scrape")
        },
    }

    if not errors and report["metadata_changed"] and not dry_run:
        line_ending = "\r\n" if b"\r\n" in target.read_bytes()[:65536] else "\n"
        candidate = target.with_name(target.stem + ".candidate.csv")
        write_csv(merged, columns, candidate, line_ending)
        shutil.copy2(target, target.with_name(target.stem + ".prev.csv"))
        os.replace(candidate, target)
        report["published"] = True

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Rows: {report['rows_before']} -> {report['rows_after']} | new {report['new_count']} | "
          f"updated {report['updated_count']} | missing from scrape {report['missing_from_scrape']} | "
          f"posters held back {len(stats['poster_held_back'])}")
    print(f"Embedding text changed: {report['embedding_text_changed']} | "
          f"metadata changed: {report['metadata_changed']}")
    print(f"Report: {report_path}")
    if errors:
        raise ValueError("Validation failed, data/final left unchanged:\n  - " + "\n  - ".join(errors))
    if report["published"]:
        print(f"Published {target} (previous copy: {target.stem}.prev.csv)")
    elif dry_run:
        print("Dry run: nothing written.")
    else:
        print("No changes: nothing written.")
    return report


def parse_args():
    parser = argparse.ArgumentParser(description="Merge the scraped K-drama CSV into data/final.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Cleaned scraper CSV (Step 2e output)")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Live dataset CSV to update")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="JSON report path")
    parser.add_argument("--max-new", type=int, default=300, help="Fail if more new dramas than this")
    parser.add_argument("--dry-run", action="store_true", help="Merge and validate, but write only the report")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        publish_dataset(args.source, args.target, args.report, args.max_new, args.dry_run)
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
