"""Removes duplicate rows from dramalist_all_dramas.csv, keeping the first occurrence.

Duplicates are identified by 'url' (the unique per-drama identifier) since Step 0b's
listing sources ('popular' and 'newest') can list the same drama, producing duplicate
Title_URL rows that flow through to Step 2's output.

Writes the deduped result to a new file rather than overwriting the original, so the
original stays available to compare against or fall back to.
"""

import os

import pandas as pd

CSV_PATH = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.csv"


def dedupe(csv_path=CSV_PATH):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    before = len(df)
    df = df.drop_duplicates(subset="url", keep="first")
    after = len(df)

    root, ext = os.path.splitext(csv_path)
    output_path = f"{root}.deduped{ext}"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Read {before} rows, removed {before - after} duplicates, {after} rows remain.")
    print(f"Original left untouched: {csv_path}")
    print(f"Deduped result saved to: {output_path}")


if __name__ == "__main__":
    dedupe()
