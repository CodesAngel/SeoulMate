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

import asyncio
import random
import os
import pandas as pd
import re
from playwright.async_api import async_playwright, Route, TimeoutError

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
async def download_page(i, url, context, output_dir, semaphore):
    url = url.strip()
    if (
        not url
        or url.lower() in ["n/a", "none", "null"]
        or not url.startswith("https://mydramalist.com/")
    ):
        print(f"[{i}] Skipping invalid URL: {url}")
        return

    drama_id = url.split("/")[-1].strip()
    if not drama_id:
        print(f"[{i}] Skipping invalid drama ID: {url}")
        return

    output_path = os.path.join(output_dir, f"{drama_id}.html")
    if os.path.exists(output_path):
        print(f"[{i}] Already saved — skipping: {drama_id}")
        return

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

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_source)
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
            print(f"[{i}] Failed to fetch page: {url}")


# -------------------------------------------
# Main
# -------------------------------------------
async def main():
    CSV_FILE = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\mydramalist_data.csv"
    OUTPUT_DIR = r"D:\Projects\SeoulMate\scrapers\DramaList_Scrapper\output\dramas_html"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(CSV_FILE)
    if "Title_URL" not in df.columns:
        raise ValueError("CSV must contain a 'Title_URL' column!")

    urls = df["Title_URL"].dropna().astype(str).tolist()
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
        await asyncio.gather(*tasks)

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
