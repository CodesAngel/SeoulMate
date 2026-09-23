"""Runs the full DramaList scrape pipeline in one go:

  0a. step0a_download_listing_pages - download popular-shows listing pages -> html_pages/
  0b. step0b_extract_drama_urls     - extract each drama's URL to a CSV    -> mydramalist_data.csv
  1.  step1_download_html           - download each drama's own page      -> dramas_html/
  2.  step2_extract_data            - extract fields to CSV               -> output/dramalist_all_dramas.csv
  2b. step2b_dedupe_data            - remove duplicate rows (by url)      -> output/dramalist_all_dramas.deduped.csv
  3.  step3_download_images         - download poster images              -> drama_image/

Each step is independently resumable (skips work already done), so re-running
this script after a partial run just picks up where it left off.

Note: step2b writes a separate *.deduped.csv file rather than overwriting Step 2's
output — it does not replace dramalist_all_dramas.csv automatically.

Usage:
    python run_pipeline.py                  # run all six steps
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
    step3_download_images,
)

BASE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper"

STEPS = ["listing", "urls", "html", "data", "dedupe", "images"]


def run_listing():
    print("\n=== Step 0a/6: downloading listing pages ===")
    asyncio.run(step0a_download_listing_pages.main())


def run_urls():
    print("\n=== Step 0b/6: extracting drama URLs from listing pages ===")
    step0b_extract_drama_urls.extract_from_folder(
        rf"{BASE}\output\html_pages",
        rf"{BASE}\mydramalist_data.csv",
    )


def run_html():
    print("\n=== Step 1/6: downloading drama pages ===")
    asyncio.run(step1_download_html.main())


def run_data():
    print("\n=== Step 2/6: extracting data to CSV ===")
    step2_extract_data.process_folder(
        rf"{BASE}\output\dramas_html",
        output_csv=rf"{BASE}\output\dramalist_all_dramas.csv",
        max_workers=None,
        skip_existing=True,
    )


def run_dedupe():
    print("\n=== Step 2b/6: removing duplicate rows (by url) ===")
    step2b_dedupe_data.dedupe(rf"{BASE}\output\dramalist_all_dramas.csv")


def run_images():
    print("\n=== Step 3/6: downloading poster images ===")
    step3_download_images.download_images_from_csv(
        rf"{BASE}\dramalist_kdramas.xlsx",
        output_folder=rf"{BASE}\output\drama_image",
    )


RUNNERS = {
    "listing": run_listing,
    "urls": run_urls,
    "html": run_html,
    "data": run_data,
    "dedupe": run_dedupe,
    "images": run_images,
}


def main():
    parser = argparse.ArgumentParser(description="Run the DramaList scrape pipeline.")
    parser.add_argument("--skip-listing", action="store_true", help="skip step 0a (download listing pages)")
    parser.add_argument("--skip-urls", action="store_true", help="skip step 0b (extract drama URLs)")
    parser.add_argument("--skip-html", action="store_true", help="skip step 1 (download drama pages)")
    parser.add_argument("--skip-data", action="store_true", help="skip step 2 (extract data)")
    parser.add_argument("--skip-dedupe", action="store_true", help="skip step 2b (remove duplicate rows)")
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
            args.skip_images,
        ]
        steps_to_run = [step for step, skip in zip(STEPS, skip_flags) if not skip]

    for step in steps_to_run:
        RUNNERS[step]()

    print("\nPipeline finished.")


if __name__ == "__main__":
    main()
