# Download poster images named "<Title> (<Year>) [<ID>].jpg".
#
# The ID is the file name of the poster URL in the dataset's `image` column
# (https://i.mydramalist.com/9oX6Gf.jpg -> 9oX6Gf). It is unique per drama, so dramas
# that share a title (e.g. "Bad Guy" 2010 and 2024) no longer overwrite each other's
# file. The backend finds a poster by the [ID] part only; the title and year are a
# human-readable label. Only posters whose ID is not in the folder yet are downloaded.
import argparse
import asyncio
import csv
import os
import random
import re
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import aiohttp
import pandas as pd
from tqdm.asyncio import tqdm as async_tqdm

PROJECT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CSV = PROJECT_DIR / "data" / "final" / "kdrama_dataset.csv"
DEFAULT_OUTPUT = PROJECT_DIR / "scrapers" / "DramaList_Scrapper" / "output" / "drama_image_by_id"
DEFAULT_REPORT = DEFAULT_OUTPUT.parent / "drama_image_by_id_report.csv"

# Matches the "[ID].ext" suffix of a saved poster. Keep in sync with the backend.
POSTER_ID_PATTERN = re.compile(r"\[([^\[\]]+)\]\.[A-Za-z0-9]+$")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


def poster_id(image_url):
    """'https://i.mydramalist.com/73PkAD_4f.jpg' -> '73PkAD_4f' (None if no URL)."""
    if not image_url or str(image_url).lower() == "nan":
        return None
    stem = os.path.splitext(os.path.basename(urlparse(str(image_url)).path))[0]
    return stem or None


def first_year(aired):
    match = re.search(r"\b(19|20)\d{2}\b", str(aired or ""))
    return match.group(0) if match else None


def sanitize_label(title):
    """Title part of the file name: no characters Windows forbids, and no brackets
    or parentheses, so the "(Year) [ID]" suffix always parses."""
    label = re.sub(r'[\\/*?:"<>|]', "_", str(title)).strip()
    label = re.sub(r"[\[\]()]", "", label)
    return re.sub(r"\s+", " ", label).strip() or "untitled"


def poster_filename(title, aired, image_url):
    """'Bad Guy', 'May 26, 2010 - ...', '.../9oX6Gf.jpg' -> 'Bad Guy (2010) [9oX6Gf].jpg'."""
    ext = os.path.splitext(urlparse(str(image_url)).path)[-1] or ".jpg"
    year = first_year(aired)
    year_part = f" ({year})" if year else ""
    return f"{sanitize_label(title)}{year_part} [{poster_id(image_url)}]{ext}"


def existing_poster_ids(output_folder):
    """IDs already saved in the folder (files under 1 KB count as missing)."""
    ids = set()
    for path in Path(output_folder).glob("*"):
        match = POSTER_ID_PATTERN.search(path.name)
        if match and path.is_file() and path.stat().st_size > 1024:
            ids.add(match.group(1))
    return ids


async def download_image(session, sem, task, output_folder, retries=3):
    """Download one poster. Returns (task, status) where status is 'ok' or an error."""
    filepath = Path(output_folder) / task["filename"]
    status = "failed"
    async with sem:
        for attempt in range(retries):
            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(task["image"], headers=headers) as response:
                    if response.status == 404:
                        return task, "http 404"
                    if response.status != 200:
                        status = f"http {response.status}"
                    else:
                        content = await response.read()
                        if len(content) < 500:  # broken / placeholder image
                            status = "too small"
                        else:
                            async with aiofiles.open(filepath, "wb") as f:
                                await f.write(content)
                            return task, "ok"
            except Exception as e:
                status = f"error: {type(e).__name__}"
            await asyncio.sleep(0.5 * (attempt + 1))
    return task, status


async def download_images_async(tasks, output_folder, concurrency):
    sem = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency, ttl_dns_cache=3600)
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        coroutines = [download_image(session, sem, task, output_folder) for task in tasks]
        results = []
        for coro in async_tqdm.as_completed(
            coroutines, total=len(coroutines), desc="Downloading posters", unit="img"
        ):
            results.append(await coro)
        return results


def download_images_from_csv(csv_path, output_folder, report_path, concurrency=10):
    """Download every poster in the CSV whose ID is not in `output_folder` yet."""
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    for column in ("title", "image", "aired"):
        if column not in df.columns:
            raise ValueError(f"The CSV must contain a '{column}' column.")
    os.makedirs(output_folder, exist_ok=True)

    have = existing_poster_ids(output_folder)
    tasks, no_url = [], []
    for _, row in df.iterrows():
        pid = poster_id(row["image"])
        if not pid:
            no_url.append(row["title"])
            continue
        if pid in have:
            continue
        tasks.append({
            "title": str(row["title"]).strip(),
            "aired": row["aired"],
            "image": str(row["image"]),
            "id": pid,
            "filename": poster_filename(row["title"], row["aired"], row["image"]),
        })

    print(f"CSV: {csv_path} ({len(df)} dramas)")
    print(f"Output: {output_folder}")
    print(f"Already saved: {len(have)} | no image URL: {len(no_url)} | to download: {len(tasks)}\n")

    results = asyncio.run(download_images_async(tasks, output_folder, concurrency)) if tasks else []
    failed = [(task, status) for task, status in results if status != "ok"]

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "aired", "id", "image", "status"])
        for task, status in failed:
            writer.writerow([task["title"], task["aired"], task["id"], task["image"], status])
        for title in no_url:
            writer.writerow([title, "", "", "", "no image url"])

    print(f"\nDownloaded {len(results) - len(failed)} | failed {len(failed)} | no URL {len(no_url)}")
    print(f"Failures (if any) listed in: {report_path}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__ or "Download drama posters by ID.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Dataset CSV with title, aired, image columns")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Folder to save posters in")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="CSV listing failed downloads")
    parser.add_argument("--concurrency", type=int, default=10, help="Parallel downloads (keep it polite)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_images_from_csv(args.csv, args.out, args.report, args.concurrency)
