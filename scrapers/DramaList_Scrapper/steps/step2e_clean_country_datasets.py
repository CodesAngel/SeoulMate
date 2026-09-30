"""Cleans every per-country dataset produced by Step 2d.

Applies the same cleanup logic developed for data/final/kdrama_dataset.csv to
every file in output/by_country/ (kdrama_dataset.csv, cdrama_dataset.csv, etc.):

  - Drops low-value/redundant columns: url, country (constant within a
    single-country file), media_type, date_published, content_rating, ranked,
    score, popularity. Unlike data/final's copy, 'image' is KEPT here — Step 3
    (image downloader) reads it from this file's output.
  - Cleans 'description': strips MyDramaList's "Edit Translation" UI text,
    strips "(Source: ...)" attribution tags, collapses repeated whitespace.
    Drops rows with an empty/missing description entirely.
  - 'watchers': strips comma thousands-separators, converts to integer.
  - 'rating_count': converted to nullable integer (no trailing .0).
  - 'aired': fixes the double-space bug before single-digit days.

Each cleaned file is written to output/by_country/cleaned/, same filename as
the input — the folder itself signals it's the cleaned version.
"""

import glob
import os
import re

import pandas as pd

INPUT_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\by_country"
OUTPUT_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\by_country\cleaned"

COLUMNS_TO_DROP = [
    "url",
    "country",
    "media_type",
    "date_published",
    "content_rating",
    "ranked",
    "score",
    "popularity",
]

# Handles the real variants found in the data: "(Source: X)", "(Sources: X, Y)",
# "(Source X)" (no colon), "(Source : X)" (space before colon), and rows with a
# missing/mismatched closing bracket (e.g. "(Source: X]" or no closing bracket
# at all) — the closing ")" is optional so those still get fully stripped.
SOURCE_TAG_RE = re.compile(r"\(Sources?\s*:?\s*[^)]*\)?", re.IGNORECASE)


def clean_description(text):
    if not isinstance(text, str):
        return text
    # "Edit Translation" is always a trailing suffix (followed by a language
    # list), never part of the actual synopsis — drop it and everything after.
    text = text.split("Edit Translation")[0]
    text = SOURCE_TAG_RE.sub("", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def clean_watchers(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False), errors="coerce"
    ).astype("Int64")


def clean_aired(text):
    if not isinstance(text, str):
        return text
    return re.sub(r" {2,}", " ", text).strip()


def clean_dataset(df):
    present = [c for c in COLUMNS_TO_DROP if c in df.columns]
    cleaned_df = df.drop(columns=present)

    if "description" in cleaned_df.columns:
        cleaned_df["description"] = cleaned_df["description"].apply(clean_description)
        cleaned_df = cleaned_df[cleaned_df["description"].str.strip().fillna("") != ""]

    if "watchers" in cleaned_df.columns:
        cleaned_df["watchers"] = clean_watchers(cleaned_df["watchers"])

    if "rating_count" in cleaned_df.columns:
        cleaned_df["rating_count"] = cleaned_df["rating_count"].astype("Int64")

    if "aired" in cleaned_df.columns:
        cleaned_df["aired"] = cleaned_df["aired"].apply(clean_aired)

    return cleaned_df


def clean_country_datasets(input_dir=INPUT_DIR, output_dir=OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    csv_files = sorted(glob.glob(os.path.join(input_dir, "*.csv")))
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return

    for input_path in csv_files:
        filename = os.path.basename(input_path)
        output_path = os.path.join(output_dir, filename)

        df = pd.read_csv(input_path, encoding="utf-8-sig")
        cleaned_df = clean_dataset(df)

        cleaned_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"{filename}: {len(df)} -> {len(cleaned_df)} rows -> {output_path}")


if __name__ == "__main__":
    clean_country_datasets()
