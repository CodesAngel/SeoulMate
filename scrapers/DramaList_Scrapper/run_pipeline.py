"""Runs the full DramaList scrape pipeline in one go:

  0a. step0a_download_listing_pages - download popular-shows listing pages -> html_pages/
  0b. step0b_extract_drama_urls     - extract each drama's URL to a CSV    -> mydramalist_data.csv
  1.  step1_download_html           - download each drama's own page      -> dramas_html/
  2.  step2_extract_data            - extract fields to CSV               -> output/dramalist_all_dramas.csv
  2b. step2b_dedupe_data            - remove duplicate rows (by url)      -> output/dramalist_all_dramas.deduped.csv
  2c. step2c_clean_titles           - fix HTML entities, drop Special/BTS -> output/dramalist_all_dramas.deduped.cleantitle.csv
  2d. step2d_split_by_country       - split cleaned data by country       -> output/by_country/<prefix>drama_dataset.csv
  2e. step2e_clean_country_datasets - drop columns, clean fields per file -> output/by_country/cleaned/<prefix>drama_dataset.csv
  3.  step3_download_images         - download poster images              -> drama_image/

Each step is independently resumable (skips work already done), so re-running
this script after a partial run just picks up where it left off.

Note: step2b, step2c and step2e each write a separate output file rather than
overwriting their input — dramalist_all_dramas.csv is never modified by step2b,
dramalist_all_dramas.deduped.csv is never modified by step2c, and the raw
output/by_country/*.csv files are never modified by step2e.

Usage:
    python run_pipeline.py                  # run all nine steps
    python run_pipeline.py --skip-listing --skip-urls --skip-html
                                             # already have dramas_html/, just extract + get images
    python run_pipeline.py --only images    # run only the image-download step
"""

import argparse
import asyncio

from steps import (
    step0a_download_listing_pages,
    step0b_extract_drama_urls,
    step1_download_html,
    step2_extract_data,
    step2b_dedupe_data,
    step2c_clean_titles,
    step2d_split_by_country,
    step2e_clean_country_datasets,
    step3_download_images,
)

BASE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper"

STEPS = ["listing", "urls", "html", "data", "dedupe", "clean", "split", "cleandata", "images"]


def run_listing():
    print("\n=== Step 0a/9: downloading listing pages ===")
    asyncio.run(step0a_download_listing_pages.main())


def run_urls():
    print("\n=== Step 0b/9: extracting drama URLs from listing pages ===")
    step0b_extract_drama_urls.extract_from_folder(
        rf"{BASE}\output\html_pages",
        rf"{BASE}\mydramalist_data.csv",
    )


def run_html():
    print("\n=== Step 1/9: downloading drama pages ===")
    asyncio.run(step1_download_html.main())


def run_data():
    print("\n=== Step 2/9: extracting data to CSV ===")
    step2_extract_data.process_folder(
        rf"{BASE}\output\dramas_html",
        output_csv=rf"{BASE}\output\dramalist_all_dramas.csv",
        max_workers=None,
        skip_existing=True,
    )


def run_dedupe():
    print("\n=== Step 2b/9: removing duplicate rows (by url) ===")
    step2b_dedupe_data.dedupe(rf"{BASE}\output\dramalist_all_dramas.csv")


def run_clean():
    print("\n=== Step 2c/9: cleaning titles (HTML entities, Special/BTS rows) ===")
    step2c_clean_titles.clean_titles(
        rf"{BASE}\output\dramalist_all_dramas.deduped.csv",
        rf"{BASE}\output\dramalist_all_dramas.deduped.cleantitle.csv",
    )


def run_split():
    print("\n=== Step 2d/9: splitting cleaned data by country ===")
    step2d_split_by_country.split_by_country(
        rf"{BASE}\output\dramalist_all_dramas.deduped.cleantitle.csv",
        rf"{BASE}\output\by_country",
    )


def run_cleandata():
    print("\n=== Step 2e/9: cleaning each per-country dataset ===")
    step2e_clean_country_datasets.clean_country_datasets(
        rf"{BASE}\output\by_country",
        rf"{BASE}\output\by_country\cleaned",
    )


def run_images():
    print("\n=== Step 3/9: downloading poster images ===")
    step3_download_images.download_images_from_csv(
        rf"{BASE}\output\by_country\cleaned\kdrama_dataset.csv",
        output_folder=rf"{BASE}\output\drama_image",
    )


RUNNERS = {
    "listing": run_listing,
    "urls": run_urls,
    "html": run_html,
    "data": run_data,
    "dedupe": run_dedupe,
    "clean": run_clean,
    "split": run_split,
    "cleandata": run_cleandata,
    "images": run_images,
}


def main():
    parser = argparse.ArgumentParser(description="Run the DramaList scrape pipeline.")
    parser.add_argument("--skip-listing", action="store_true", help="skip step 0a (download listing pages)")
    parser.add_argument("--skip-urls", action="store_true", help="skip step 0b (extract drama URLs)")
    parser.add_argument("--skip-html", action="store_true", help="skip step 1 (download drama pages)")
    parser.add_argument("--skip-data", action="store_true", help="skip step 2 (extract data)")
    parser.add_argument("--skip-dedupe", action="store_true", help="skip step 2b (remove duplicate rows)")
    parser.add_argument("--skip-clean", action="store_true", help="skip step 2c (clean titles)")
    parser.add_argument("--skip-split", action="store_true", help="skip step 2d (split cleaned data by country)")
    parser.add_argument("--skip-cleandata", action="store_true", help="skip step 2e (clean each per-country dataset)")
    parser.add_argument("--skip-images", action="store_true", help="skip step 3 (download images)")
    parser.add_argument(
        "--only",
        choices=STEPS,
        help="run only this one step",
    )
    args = parser.parse_args()

    if args.only:
        steps_to_run = [args.only]
    else:
        skip_flags = [
            args.skip_listing,
            args.skip_urls,
            args.skip_html,
            args.skip_data,
            args.skip_dedupe,
            args.skip_clean,
            args.skip_split,
            args.skip_cleandata,
            args.skip_images,
        ]
        steps_to_run = [step for step, skip in zip(STEPS, skip_flags) if not skip]

    for step in steps_to_run:
        RUNNERS[step]()

    print("\nPipeline finished.")


if __name__ == "__main__":
    main()
