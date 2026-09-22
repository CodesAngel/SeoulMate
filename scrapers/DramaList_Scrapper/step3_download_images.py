# Only check the missing images and download them
import pandas as pd
import aiohttp
import asyncio
import aiofiles
import os
import re
import random
from tqdm.asyncio import tqdm as async_tqdm
from urllib.parse import urlparse

def sanitize_filename(name):
    """Remove invalid characters for safe file naming."""
    return re.sub(r'[\\/*?:"<>|]', "_", str(name)).strip()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Bingbot/2.0 (+http://www.bing.com/bingbot.htm)",
]

async def download_image(session, sem, title, image_url, output_folder, retries=3):
    """Download a single image asynchronously with retries."""
    if not image_url or str(image_url).lower() == 'nan':
        return None

    async with sem:
        ext = os.path.splitext(urlparse(image_url).path)[-1] or ".jpg"
        filename = sanitize_filename(title) + ext
        filepath = os.path.join(output_folder, filename)

        # Skip if already exists and valid (>1KB)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
            return None

        for attempt in range(retries):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(image_url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        if len(content) < 500:  # avoid broken images
                            continue
                        async with aiofiles.open(filepath, "wb") as f:
                            await f.write(content)
                        return filename
            except Exception:
                await asyncio.sleep(0.5 * (attempt + 1))
        return None

async def download_images_async(tasks, output_folder, concurrency=100):
    """Manage asynchronous downloading of images."""
    os.makedirs(output_folder, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)

    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=3600)
    timeout = aiohttp.ClientTimeout(total=25)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        coroutines = [
            download_image(session, sem, title, url, output_folder)
            for title, url in tasks
        ]
        results = []
        for coro in async_tqdm.as_completed(
            coroutines, total=len(coroutines), desc="Downloading missing images", unit="img"
        ):
            result = await coro
            results.append(result)
        return results

def download_images_from_csv(csv_path, output_folder, concurrency=100):
    """Download only missing images from a CSV/Excel file."""
    # Read data
    if csv_path.lower().endswith(('.xlsx', '.xls')):
        df = pd.read_excel(csv_path)
    else:
        df = pd.read_csv(csv_path, sep=None, engine="python")

    if "title" not in df.columns or "image" not in df.columns:
        raise ValueError("The file must contain 'title' and 'image' columns.")

    os.makedirs(output_folder, exist_ok=True)

    # Filter: only those whose image is missing in folder
    missing_tasks = []
    for _, row in df.iterrows():
        if pd.isna(row["image"]):
            continue
        ext = os.path.splitext(urlparse(str(row["image"])).path)[-1] or ".jpg"
        filename = sanitize_filename(row["title"]) + ext
        filepath = os.path.join(output_folder, filename)
        if not (os.path.exists(filepath) and os.path.getsize(filepath) > 1024):
            missing_tasks.append((row["title"], row["image"]))

    print(f"Found {len(df)} total entries.")
    print(f"Skipping {len(df) - len(missing_tasks)} existing files.")
    print(f"Downloading {len(missing_tasks)} missing images...\n")

    if not missing_tasks:
        print("All images already downloaded.")
        return

    asyncio.run(download_images_async(missing_tasks, output_folder, concurrency))
    print(f"\nAll missing images saved in '{output_folder}' folder.")

# Example usage:
download_images_from_csv("D:\\Projects\\SeoulMate\\scrapers\\DramaList_Scrapper\\dramalist_kdramas.xlsx", output_folder="D:\\Projects\\SeoulMate\\scrapers\\DramaList_Scrapper\\drama_image")
