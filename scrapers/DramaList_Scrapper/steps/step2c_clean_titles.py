"""Cleans up drama titles in the deduped dataset.

Reads output/dramalist_all_dramas.deduped.csv (Step 2b's output) and:
  1. Fixes HTML entities in the 'title' column (e.g. &amp; -> &, &quot; -> ").
  2. Drops rows where the title contains "Special" or "BTS" (case-insensitive) —
     bonus/behind-the-scenes entries, not real dramas.

Writes the result to a separate file rather than overwriting the input.
"""

import html

import pandas as pd

INPUT_CSV = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.deduped.csv"
OUTPUT_CSV = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.deduped.cleantitle.csv"


def clean_titles(input_csv=INPUT_CSV, output_csv=OUTPUT_CSV):
    df = pd.read_csv(input_csv, encoding="utf-8-sig")

    df["title"] = df["title"].apply(lambda x: html.unescape(x) if isinstance(x, str) else x)

    before = len(df)
    cleaned_df = df[~df["title"].str.contains("Special|BTS", case=False, na=False)]
    after = len(cleaned_df)

    print(f"Read {before} rows, removed {before - after} Special/BTS rows, {after} rows remain.")

    try:
        cleaned_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(f"Saved: {output_csv}")
    except PermissionError:
        print(f"\n[!] Permission Error: '{output_csv}' is currently open in another program.")
        print("Close the file and run the script again to overwrite it.")


if __name__ == "__main__":
    clean_titles()
