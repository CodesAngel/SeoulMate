"""Step 0a: download MyDramaList's popular-shows listing pages.

Fetches https://mydramalist.com/shows/popular?page=1..250 with Playwright and
saves the rendered HTML of each page into html_pages/. These listing pages are
later parsed (Step 0b) to pull out each drama's title URL.
"""

import asyncio
import os
import random
import re
from typing import Optional

from playwright.async_api import Route, async_playwright, expect

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

BASE_URL = "https://mydramalist.com/shows/popular?page={}"
OUTPUT_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\html_pages"
LAST_PAGE = 250


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


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for page_num in range(1, LAST_PAGE + 1):
        url = BASE_URL.format(page_num)
        output_path = os.path.join(OUTPUT_DIR, f"page_{page_num}.html")

        if os.path.exists(output_path):
            print(f"Page {page_num} already exists — skipping.")
            continue

        print(f"\nStarting page {page_num}")
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


if __name__ == "__main__":
    asyncio.run(main())
