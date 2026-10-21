"""Runs the full DramaList scrape pipeline in one go:

  0a. step0a_download_listing_pages - download popular-shows listing pages -> html_pages/
  0b. step0b_extract_drama_urls     - extract each drama's URL to a CSV    -> mydramalist_data.csv
  1.  step1_download_html           - download each drama's own page      -> dramas_html/
  2.  step2_extract_data            - extract fields to CSV               -> output/dramalist_all_dramas.csv
  2b. step2b_dedupe_data            - remove duplicate rows (by url)      -> output/dramalist_all_dramas.deduped.csv
  2c. step2c_clean_titles           - fix HTML entities, drop Special/BTS -> output/dramalist_all_dramas.deduped.cleantitle.csv
  2d. step2d_split_by_country       - split cleaned data by country       -> output/by_country/<prefix>drama_dataset.csv
  2e. step2e_clean_country_datasets - drop columns, clean fields per file -> output/by_country/cleaned/<prefix>drama_dataset.csv
  4.  step4_publish_dataset         - merge + validate into data/final    -> data/final/kdrama_dataset.csv
  3.  step3_download_images         - download poster images by ID        -> output/drama_image_by_id/
      (runs after step 4, so posters follow the published dataset)

Each step is independently resumable (skips work already done), so re-running
this script after a partial run just picks up where it left off.

Note: step2b, step2c and step2e each write a separate output file rather than
overwriting their input — dramalist_all_dramas.csv is never modified by step2b,
dramalist_all_dramas.deduped.csv is never modified by step2c, and the raw
output/by_country/*.csv files are never modified by step2e.

Usage:
    python run_pipeline.py                  # run all ten steps
    python run_pipeline.py --skip-listing --skip-urls --skip-html
                                             # already have dramas_html/, just extract + get images
    python run_pipeline.py --only images    # run only the image-download step
    python run_pipeline.py --refresh        # nightly: first listing pages, new + due drama pages
    python run_pipeline.py --refresh --dry-run --only html
                                             # show what would be downloaded, no requests

Which countries are downloaded and the refresh intervals are set in steps/scrape_settings.py.
"""

import argparse
import asyncio

from steps import scrape_settings
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
    step4_publish_dataset,
)

BASE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper"

STEPS = ["listing", "urls", "html", "data", "dedupe", "clean", "split", "cleandata", "publish", "images"]

# Set from the command line in main(); used by the download steps.
OPTIONS = argparse.Namespace(refresh=False, max_pages=None, max_fetch=None, dry_run=False)


def run_listing():
    print("\n=== Step 0a/10: downloading listing pages ===")
    max_pages = OPTIONS.max_pages
    if OPTIONS.refresh and max_pages is None:
        max_pages = scrape_settings.REFRESH_LISTING_PAGES
    asyncio.run(step0a_download_listing_pages.main(OPTIONS.refresh, max_pages, OPTIONS.dry_run))


def run_urls():
    print("\n=== Step 0b/10: extracting drama URLs from listing pages ===")
    step0b_extract_drama_urls.extract_from_folder(
        rf"{BASE}\output\html_pages",
        rf"{BASE}\mydramalist_data.csv",
    )


def run_html():
    print("\n=== Step 1/10: downloading drama pages ===")
    max_fetch = OPTIONS.max_fetch
    if OPTIONS.refresh and max_fetch is None:
        max_fetch = scrape_settings.REFRESH_MAX_FETCH
    asyncio.run(step1_download_html.main(OPTIONS.refresh, max_fetch, OPTIONS.dry_run))


def run_data():
    print("\n=== Step 2/10: extracting data to CSV ===")
    step2_extract_data.process_folder(
        rf"{BASE}\output\dramas_html",
        output_csv=rf"{BASE}\output\dramalist_all_dramas.csv",
        max_workers=None,
        skip_existing=True,
        failed_list=step1_download_html.FAILED_LIST,
    )


def run_dedupe():
    print("\n=== Step 2b/10: removing duplicate rows (by url) ===")
    step2b_dedupe_data.dedupe(rf"{BASE}\output\dramalist_all_dramas.csv")


def run_clean():
    print("\n=== Step 2c/10: cleaning titles (HTML entities, Special/BTS rows) ===")
    step2c_clean_titles.clean_titles(
        rf"{BASE}\output\dramalist_all_dramas.deduped.csv",
        rf"{BASE}\output\dramalist_all_dramas.deduped.cleantitle.csv",
    )


def run_split():
    print("\n=== Step 2d/10: splitting cleaned data by country ===")
    step2d_split_by_country.split_by_country(
        rf"{BASE}\output\dramalist_all_dramas.deduped.cleantitle.csv",
        rf"{BASE}\output\by_country",
    )


def run_cleandata():
    print("\n=== Step 2e/10: cleaning each per-country dataset ===")
    step2e_clean_country_datasets.clean_country_datasets(
        rf"{BASE}\output\by_country",
        rf"{BASE}\output\by_country\cleaned",
    )


def run_publish():
    print("\n=== Step 4/10: merging into data/final (validated) ===")
    step4_publish_dataset.publish_dataset(
        step4_publish_dataset.DEFAULT_SOURCE,
        step4_publish_dataset.DEFAULT_TARGET,
        step4_publish_dataset.DEFAULT_REPORT,
    )


def run_images():
    print("\n=== Step 3/10: downloading poster images ===")
    step3_download_images.download_images_from_csv(
        step3_download_images.DEFAULT_CSV,
        output_folder=step3_download_images.DEFAULT_OUTPUT,
        report_path=step3_download_images.DEFAULT_REPORT,
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
    "publish": run_publish,
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
    parser.add_argument("--skip-publish", action="store_true", help="skip step 4 (merge into data/final)")
    parser.add_argument("--skip-images", action="store_true", help="skip step 3 (download images)")
    parser.add_argument(
        "--only",
        choices=STEPS,
        help="run only this one step",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="nightly mode: first listing pages into html_pages/refresh/<today>/, new + due drama pages",
    )
    parser.add_argument("--max-pages", type=int, help="listing pages per source (refresh default: 5)")
    parser.add_argument("--max-fetch", type=int, help="drama pages per run (refresh default: 300)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run only the listing/html steps, printing what they would fetch; no requests, no files written",
    )
    args = parser.parse_args()
    OPTIONS.refresh, OPTIONS.dry_run = args.refresh, args.dry_run
    OPTIONS.max_pages, OPTIONS.max_fetch = args.max_pages, args.max_fetch

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
            args.skip_publish,
            args.skip_images,
        ]
        steps_to_run = [step for step, skip in zip(STEPS, skip_flags) if not skip]

    if args.dry_run:
        steps_to_run = [step for step in steps_to_run if step in ("listing", "html")]
        print(f"Dry run: only {', '.join(steps_to_run) or 'no'} step(s), nothing is fetched or written.")

    for step in steps_to_run:
        RUNNERS[step]()

    print("\nPipeline finished.")


if __name__ == "__main__":
    main()
