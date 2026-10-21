"""Step 0a: download MyDramaList's listing pages (popular + newest).

Fetches https://mydramalist.com/shows/popular?page=1..250 and
https://mydramalist.com/shows/newest?page=1..N with Playwright. Each source's pages
are saved into their own subfolder under html_pages/ (html_pages/popular/,
html_pages/newest/), so both sources can use the same page_N.html naming without
colliding. These listing pages are later parsed (Step 0b) to pull out each drama's
title URL.

Refresh mode (--refresh, used nightly) fetches only the first N pages of each source into
html_pages/refresh/<YYYY-MM-DD>/<source>/, so new dramas are discovered without touching
the archived pages. Step 0b reads every subfolder, so old and new pages are combined.
"""

import argparse
import asyncio
import os
import random
import re
from datetime import date
from typing import Optional

from playwright.async_api import Route, async_playwright, expect

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

HTML_PAGES_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\html_pages"

# Each listing source has its own URL pattern, its own subfolder (named after the
# source) and its own hardcoded last page. MyDramaList doesn't expose a clean "total
# pages" count, so last_page needs to be checked/updated manually after running.
SOURCES = {
    "popular": {
        "url_template": "https://mydramalist.com/shows/popular?page={}",
        "last_page": 250,
    },
    "newest": {
        "url_template": "https://mydramalist.com/shows/newest?page={}",
        # Not verified against the live site yet — check the actual last page once
        # this runs (watch for repeated "Error fetching" / empty results) and adjust.
        "last_page": 250,
    },
}


async def block_images_and_fonts(route: Route):
    if route.request.resource_type in ["image", "font", "media"]:
        await route.abort()
    else:
        await route.continue_()


async def fetch_rendered_html(url: str) -> Optional[str]:
    selected_user_agent = random.choice(USER_AGENTS)
    print(f"Fetching: {url} (UA: {selected_user_agent[:40]}...)")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--window-size=1920,1080"],
            )
            context = await browser.new_context(
                user_agent=selected_user_agent,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.route("**/*", block_images_and_fonts)

            await page.goto(url, timeout=120000)

            # Wait for at least one drama title to appear
            content_selector = ".box h6.title a"
            locator = page.locator(content_selector).first
            await expect(locator).to_have_text(re.compile(r"\S+"), timeout=60000)

            await asyncio.sleep(2)
            html = await page.content()
            await browser.close()
            return html

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


async def download_source(source_name, url_template, last_page, output_dir, dry_run=False):
    print(f"\n--- Source: {source_name} -> {output_dir} ---")
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    for page_num in range(1, last_page + 1):
        url = url_template.format(page_num)
        output_path = os.path.join(output_dir, f"page_{page_num}.html")

        if os.path.exists(output_path):
            print(f"[{source_name}] Page {page_num} already exists — skipping.")
            continue
        if dry_run:
            print(f"[{source_name}] Would fetch: {url}")
            continue

        print(f"\n[{source_name}] Starting page {page_num}")
        html_source = await fetch_rendered_html(url)

        if html_source:
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_source)
                print(f"Saved: {output_path} ({len(html_source)} chars)")
            except Exception as e:
                print(f"Error saving page {page_num}: {e}")
        else:
            print(f"Skipped page {page_num} due to fetch error.")

        sleep_time = random.uniform(3, 6)
        print(f"Sleeping {sleep_time:.1f}s...\n")
        await asyncio.sleep(sleep_time)


async def main(refresh=False, max_pages=None, dry_run=False):
    """Full crawl into html_pages/<source>/, or with refresh=True the first max_pages
    pages into html_pages/refresh/<today>/<source>/ (re-running the same day resumes)."""
    root = os.path.join(HTML_PAGES_DIR, "refresh", date.today().isoformat()) if refresh else HTML_PAGES_DIR

    for source_name, cfg in SOURCES.items():
        last_page = min(cfg["last_page"], max_pages) if max_pages else cfg["last_page"]
        output_dir = os.path.join(root, source_name)
        await download_source(source_name, cfg["url_template"], last_page, output_dir, dry_run)


def parse_args():
    parser = argparse.ArgumentParser(description="Download MyDramaList listing pages.")
    parser.add_argument("--refresh", action="store_true", help="fetch the first pages into html_pages/refresh/<today>/")
    parser.add_argument("--max-pages", type=int, help="pages per source (refresh default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be fetched, send no requests")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    max_pages = args.max_pages
    if args.refresh and max_pages is None:
        from scrape_settings import REFRESH_LISTING_PAGES

        max_pages = REFRESH_LISTING_PAGES
    asyncio.run(main(args.refresh, max_pages, args.dry_run))
