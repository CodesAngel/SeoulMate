"""Splits dramalist_all_dramas.deduped.cleantitle.csv into one CSV per country.

Reads the 'country' column and writes each country's rows into its own file under
output/by_country/, named <prefix>drama_dataset.csv using the industry-standard
shorthand for that country (e.g. South Korea -> kdrama_dataset.csv). Countries with
no established shorthand fall back to their first letter (logged so it can be
corrected in COUNTRY_PREFIXES below).
"""

import os

import pandas as pd

INPUT_CSV = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramalist_all_dramas.deduped.cleantitle.csv"
OUTPUT_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\by_country"

COUNTRY_PREFIXES = {
    "South Korea": "k",
    "China": "c",
    "Thailand": "t",
    "Japan": "j",
    "Taiwan": "tw",
    "Hong Kong": "hk",
    "Philippines": "p",
    "Singapore": "s",
}


def split_by_country(input_csv=INPUT_CSV, output_dir=OUTPUT_DIR):
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    os.makedirs(output_dir, exist_ok=True)

    for country, group in df.groupby("country"):
        prefix = COUNTRY_PREFIXES.get(country)
        if prefix is None:
            prefix = country.strip()[0].lower()
            print(f"No mapped prefix for '{country}' — falling back to '{prefix}'. "
                  f"Add it to COUNTRY_PREFIXES if this is wrong.")

        output_path = os.path.join(output_dir, f"{prefix}drama_dataset.csv")
        group.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"{country}: {len(group)} rows -> {output_path}")


if __name__ == "__main__":
    split_by_country()
