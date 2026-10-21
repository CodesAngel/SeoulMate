# Works parallel downloads with error handling and N/A handling

# import asyncio
# import random
# import os
# import pandas as pd
# from playwright.async_api import async_playwright, Route

# # ===============================================
# #  User-Agent rotation (to avoid detection)
# # ===============================================
# USER_AGENTS = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
# ]

# # ===============================================
# #  Block unnecessary resources (faster scraping)
# # ===============================================
# async def block_images_and_fonts(route: Route):
#     if route.request.resource_type in ["image", "font", "media"]:
#         await route.abort()
#     else:
#         await route.continue_()

# # ===============================================
# #  Download a single page safely (with retry)
# # ===============================================
# async def download_page(i, url, browser, output_dir, semaphore):
#     url = url.strip()

#     if not url or url.lower() in ["n/a", "none", "null"]:
#         print(f"[{i}] Skipping invalid URL: {url}")
#         return

#     if not url.startswith("https://mydramalist.com/"):
#         print(f"[{i}] Skipping non-MyDramaList URL: {url}")
#         return

#     drama_id = url.split("/")[-1].strip()
#     if not drama_id:
#         print(f"[{i}] Skipping invalid drama ID from URL: {url}")
#         return

#     output_path = os.path.join(output_dir, f"{drama_id}.html")
#     if os.path.exists(output_path):
#         print(f"[{i}] Already saved — skipping: {drama_id}")
#         return

#     async with semaphore:
#         selected_user_agent = random.choice(USER_AGENTS)
#         success = False

#         for attempt in range(2):  # retry twice if needed
#             context = await browser.new_context(
#                 viewport={"width": 1920, "height": 1080},
#                 ignore_https_errors=True,
#                 user_agent=selected_user_agent,
#             )

#             try:
#                 page = await context.new_page()
#                 await page.route("**/*", block_images_and_fonts)

#                 print(f"[{i}] ({attempt+1}/2) Downloading: {url}")
#                 await page.goto(url, timeout=45000, wait_until="domcontentloaded")
#                 await page.wait_for_selector("h1", timeout=10000)

#                 html_source = await page.content()

#                 with open(output_path, "w", encoding="utf-8") as f:
#                     f.write(html_source)
#                 print(f"[{i}] Saved: {output_path} ({len(html_source)} chars)")

#                 success = True
#                 await page.close()
#                 break

#             except Exception as e:
#                 print(f"[{i}] Attempt {attempt+1} failed for {url}: {e}")
#                 await asyncio.sleep(random.uniform(2, 4))

#             finally:
#                 await context.close()

#         if not success:
#             print(f"[{i}] Failed to fetch page: {url}")

#         await asyncio.sleep(random.uniform(1, 2))

# # ===============================================
# #  Main function — parallel downloads
# # ===============================================
# async def main():
#     CSV_FILE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\mydramalist_data.csv"
#     OUTPUT_DIR = "dramas_html"
#     os.makedirs(OUTPUT_DIR, exist_ok=True)

#     df = pd.read_csv(CSV_FILE)
#     if "Title_URL" not in df.columns:
#         raise ValueError("CSV must contain a 'Title_URL' column!")

#     urls = df["Title_URL"].dropna().astype(str).tolist()
#     semaphore = asyncio.Semaphore(5)  # adjust concurrency

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(
#             headless=True,
#             args=["--no-sandbox", "--disable-gpu", "--window-size=1920,1080"]
#         )

#         tasks = [
#             download_page(i, url, browser, OUTPUT_DIR, semaphore)
#             for i, url in enumerate(urls, start=1)
#         ]
#         await asyncio.gather(*tasks)

#         await browser.close()

# # ===============================================
# #  Entry point
# # ===============================================
# if __name__ == "__main__":
#     asyncio.run(main())


# More robust parallel downloading logic
# concurrent file limit to 5, does not exhasust browser or out of memory problem also retry mechanism too

import argparse
import asyncio
import random
import os
import pandas as pd
import re
import time
from datetime import date, datetime, timedelta
from playwright.async_api import async_playwright, Route, TimeoutError

try:
    from steps import scrape_settings as settings
except ImportError:  # run directly as steps/step1_download_html.py
    import scrape_settings as settings

BASE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper"
CSV_FILE = rf"{BASE}\mydramalist_data.csv"
OUTPUT_DIR = rf"{BASE}\output\dramas_html"
# Step 2 output, read for each saved drama's air dates (refresh schedule).
EXTRACTED_CSV = rf"{BASE}\output\dramalist_all_dramas.csv"
# Written by Step 2: saved pages it couldn't parse, one drama ID per line.
FAILED_LIST = rf"{BASE}\output\dramas_html_failed.txt"

# -------------------------------------------
# User-Agent rotation
# -------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]


# -------------------------------------------
# Block unnecessary resources
# -------------------------------------------
async def block_images_and_fonts(route: Route):
    if route.request.resource_type in ["image", "font", "media", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()


# -------------------------------------------
# Remove emojis safely
# -------------------------------------------
def remove_emojis(text):
    return re.sub(r"[\U00010000-\U0010ffff]", "", text)


# -------------------------------------------
# Download single page
# -------------------------------------------
def drama_id_of(url):
    """'https://mydramalist.com/100-my-fair-lady' -> '100-my-fair-lady'; '' if invalid."""
    url = str(url or "").strip()
    if not url.startswith("https://mydramalist.com/"):
        return ""
    return url.rstrip("/").split("/")[-1].strip()


async def download_page(i, url, context, output_dir, semaphore):
    """Download one drama page. The new HTML replaces a saved copy only if it holds the
    drama's JSON-LD block, so a block/error page never overwrites good data."""
    url = url.strip()
    drama_id = drama_id_of(url)
    if not drama_id:
        print(f"[{i}] Skipping invalid URL: {url}")
        return False

    output_path = os.path.join(output_dir, f"{drama_id}.html")

    async with semaphore:
        success = False
        for attempt in range(2):
            try:
                page = await context.new_page()
                await page.route("**/*", block_images_and_fonts)

                print(f"[{i}] ({attempt+1}/2) Downloading: {url}")
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_selector("h1", timeout=10000)

                await asyncio.sleep(random.uniform(1, 2.5))  # let JS finish
                html_source = await page.content()
                html_source = remove_emojis(html_source)
                if "application/ld+json" not in html_source:
                    raise ValueError("page has no JSON-LD block (blocked or error page)")

                temp_path = output_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(html_source)
                os.replace(temp_path, output_path)
                print(f"[{i}] Saved: {output_path} ({len(html_source)} chars)")

                success = True
                await page.close()
                break

            except TimeoutError:
                print(f"[{i}] Timeout for {url}, retrying...")
            except Exception as e:
                print(f"[{i}] Attempt {attempt+1} failed for {url}: {e}")
            finally:
                try:
                    await page.close()
                except:
                    pass
                await asyncio.sleep(random.uniform(1, 3))

        if not success:
            print(f"[{i}] Failed to fetch page (saved copy kept): {url}")
        return success


# -------------------------------------------
# What to download
# -------------------------------------------
def parse_air_date(text):
    text = " ".join(str(text).split())
    for fmt in ("%b %d, %Y", "%b %Y", "%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def air_state(aired, today):
    """'upcoming', 'airing', 'recently_ended' or 'completed' from an 'aired' value such
    as 'Aug 26, 2002 - Sep 24, 2002', 'Feb  4, 2026' or 'Jul 11, 2010 - ?'."""
    parts = [part.strip() for part in str(aired or "").split(" - ")]
    start = parse_air_date(parts[0]) if parts[0] else None
    if start is None or start > today:
        return "upcoming"
    end_text = parts[1] if len(parts) > 1 else parts[0]
    if end_text == "?":
        open_days = (today - start).days
        return "airing" if open_days <= settings.OPEN_ENDED_AIRING_DAYS else "completed"
    end = parse_air_date(end_text) or start
    if end >= today:
        return "airing"
    if (today - end).days <= settings.RECENTLY_ENDED_DAYS:
        return "recently_ended"
    return "completed"


def plan_downloads(refresh=False, today=None, now=None):
    """Return {"new": [...], "due": [(overdue ratio, state, url), ...], "skipped_origin": n}.

    New = listed but not saved yet. Due (refresh only) = saved pages older than their
    refresh interval: by air state, or "broken" when Step 2 couldn't parse the saved copy.
    Only dramas whose listing origin is in scrape_settings.INCLUDE_ORIGINS are considered.
    """
    today = today or date.today()
    now = now or time.time()

    listing = pd.read_csv(CSV_FILE, dtype=str, keep_default_na=False)
    if "Title_URL" not in listing.columns:
        raise ValueError("CSV must contain a 'Title_URL' column!")
    media_info = listing["Media_Info"] if "Media_Info" in listing.columns else [""] * len(listing)

    urls = {}
    for url, info in zip(listing["Title_URL"], media_info):
        drama_id = drama_id_of(url)
        if drama_id and drama_id not in urls:
            urls[drama_id] = (url.strip(), info)
    included = {d: url for d, (url, info) in urls.items() if settings.is_included(info)}

    saved = set()
    if os.path.isdir(OUTPUT_DIR):
        saved = {name[:-5] for name in os.listdir(OUTPUT_DIR) if name.endswith(".html")}

    plan = {
        "new": [url for d, url in included.items() if d not in saved],
        "due": [],
        "skipped_origin": len(urls) - len(included),
    }
    if not refresh:
        return plan

    failed = set()
    if os.path.exists(FAILED_LIST):
        with open(FAILED_LIST, encoding="utf-8") as f:
            failed = {line.strip() for line in f if line.strip()}
    aired = {}
    if os.path.exists(EXTRACTED_CSV):
        extracted = pd.read_csv(
            EXTRACTED_CSV, encoding="utf-8-sig", dtype=str, keep_default_na=False, usecols=["url", "aired"]
        )
        aired = {drama_id_of(u): a for u, a in zip(extracted["url"], extracted["aired"])}

    for drama_id, url in included.items():
        if drama_id not in saved:
            continue
        age_days = (now - os.path.getmtime(os.path.join(OUTPUT_DIR, f"{drama_id}.html"))) / 86400
        state = "broken" if drama_id in failed else air_state(aired.get(drama_id), today)
        interval = settings.REFRESH_DAYS[state]
        if age_days >= interval:
            plan["due"].append((age_days / interval, state, url))
    plan["due"].sort(key=lambda item: item[0], reverse=True)
    return plan


# -------------------------------------------
# Main
# -------------------------------------------
async def main(refresh=False, max_fetch=None, dry_run=False):
    """Download new drama pages; with refresh=True also re-download due ones. New pages
    come first, then the most overdue; max_fetch caps the total per run."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    plan = plan_downloads(refresh)
    due_states = {}
    for _, state, _ in plan["due"]:
        due_states[state] = due_states.get(state, 0) + 1
    urls = plan["new"] + [url for _, _, url in plan["due"]]
    if max_fetch is not None:
        urls = urls[:max_fetch]

    origins = "all" if settings.INCLUDE_ORIGINS is None else ", ".join(settings.INCLUDE_ORIGINS)
    print(f"Origins: {origins} (skipped {plan['skipped_origin']} other listed dramas)")
    print(f"New: {len(plan['new'])} | due for refresh: {len(plan['due'])} {due_states or ''}")
    print(f"Fetching {len(urls)} pages" + (f" (capped at {max_fetch})" if max_fetch is not None else ""))
    if dry_run:
        for url in urls[:20]:
            print(f"  would fetch: {url}")
        if len(urls) > 20:
            print(f"  ... and {len(urls) - 20} more")
        return
    if not urls:
        return

    semaphore = asyncio.Semaphore(5)  # safe concurrency level

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--window-size=1920,1080"],
        )

        # Reuse one context across all downloads
        selected_user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            user_agent=selected_user_agent,
        )

        tasks = [
            asyncio.create_task(download_page(i, url, context, OUTPUT_DIR, semaphore))
            for i, url in enumerate(urls, start=1)
        ]
        results = await asyncio.gather(*tasks)

        await context.close()
        await browser.close()

    print(f"Downloaded {sum(1 for ok in results if ok)} of {len(urls)} pages.")


def parse_args():
    parser = argparse.ArgumentParser(description="Download MyDramaList drama pages.")
    parser.add_argument("--refresh", action="store_true", help="also re-download pages due for a refresh")
    parser.add_argument("--max-fetch", type=int, help="pages per run (refresh default: 300)")
    parser.add_argument("--dry-run", action="store_true", help="print what would be fetched, send no requests")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    max_fetch = args.max_fetch
    if args.refresh and max_fetch is None:
        max_fetch = settings.REFRESH_MAX_FETCH
    asyncio.run(main(args.refresh, max_fetch, args.dry_run))
