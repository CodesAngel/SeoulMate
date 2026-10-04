"""Generate verified WebP card thumbnails from the audited poster originals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_POSTERS = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_by_id"
)
DEFAULT_OUTPUT = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_cards"
)
DEFAULT_INVENTORY = PROJECT_DIR / "data" / "reports" / "poster_inventory.csv"
DEFAULT_CSV_REPORT = (
    PROJECT_DIR / "data" / "reports" / "poster_thumbnail_manifest.csv"
)
DEFAULT_JSON_REPORT = (
    PROJECT_DIR / "data" / "reports" / "poster_thumbnail_summary.json"
)
SAFE_IMAGE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generate_one(task: dict[str, Any]) -> dict[str, Any]:
    source = Path(task["source"])
    target = Path(task["target"])
    source_hash = sha256_file(source)
    if source_hash != task["source_sha256"]:
        raise ValueError(f"Source changed after poster audit: {source.name}")

    try:
        with Image.open(source) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            image.thumbnail(
                (task["max_width"], task["max_height"]),
                Image.Resampling.LANCZOS,
            )
            width, height = image.size
            temporary = target.with_name(f"{target.name}.tmp")
            image.save(
                temporary,
                "WEBP",
                quality=task["quality"],
                method=task["method"],
            )
            temporary.replace(target)
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError(f"Could not generate thumbnail for {source.name}: {error}") from error

    with Image.open(target) as thumbnail:
        if thumbnail.format != "WEBP":
            raise ValueError(f"Generated file is not WebP: {target.name}")
        if thumbnail.size != (width, height):
            raise ValueError(f"Generated dimensions changed unexpectedly: {target.name}")
        thumbnail.verify()

    size_bytes = target.stat().st_size
    return {
        "drama_id": task["drama_id"],
        "image_id": task["image_id"],
        "source_filename": source.name,
        "source_sha256": source_hash,
        "thumbnail_key": f"dramas/{task['drama_id']}/thumbnail.webp",
        "thumbnail_filename": target.name,
        "width": width,
        "height": height,
        "size_bytes": size_bytes,
        "sha256": sha256_file(target),
    }


def load_tasks(
    inventory_path: Path,
    poster_dir: Path,
    output_dir: Path,
    *,
    max_width: int,
    max_height: int,
    quality: int,
    method: int,
) -> tuple[list[dict[str, Any]], int]:
    if not inventory_path.is_file():
        raise FileNotFoundError(
            f"Poster inventory is missing: {inventory_path}. "
            "Run scripts/audit_poster_inventory.py first."
        )
    if not poster_dir.is_dir():
        raise FileNotFoundError(f"Original poster directory is missing: {poster_dir}")

    with inventory_path.open(encoding="utf-8", newline="") as handle:
        inventory = list(csv.DictReader(handle))
    if not inventory:
        raise ValueError("Poster inventory is empty")

    image_ids = [row["image_id"] for row in inventory]
    if len(image_ids) != len(set(image_ids)):
        raise ValueError("Poster inventory contains duplicate image IDs")

    tasks: list[dict[str, Any]] = []
    source_bytes = 0
    for row in inventory:
        if row["status"] != "matched":
            raise ValueError(
                f"Poster inventory is not clean for image ID {row['image_id']}: "
                f"{row['status']}"
            )
        image_id = row["image_id"]
        if not SAFE_IMAGE_ID.fullmatch(image_id):
            raise ValueError(f"Unsafe image ID in poster inventory: {image_id!r}")

        source = (poster_dir / row["actual_filename"]).resolve()
        if source.parent != poster_dir:
            raise ValueError(f"Poster path escapes the source directory: {source}")
        if not source.is_file():
            raise FileNotFoundError(f"Audited poster is missing: {source}")

        source_bytes += source.stat().st_size
        tasks.append(
            {
                "drama_id": int(row["drama_id"]),
                "image_id": image_id,
                "source": str(source),
                "source_sha256": row["sha256"],
                "target": str(output_dir / f"{image_id}.webp"),
                "max_width": max_width,
                "max_height": max_height,
                "quality": quality,
                "method": method,
            }
        )
    return tasks, source_bytes


def write_reports(
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    csv_report: Path,
    json_report: Path,
) -> None:
    csv_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.parent.mkdir(parents=True, exist_ok=True)
    with csv_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    with json_report.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--posters", type=Path, default=DEFAULT_POSTERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--csv-report", type=Path, default=DEFAULT_CSV_REPORT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--max-width", type=int, default=480)
    parser.add_argument("--max-height", type=int, default=720)
    parser.add_argument("--quality", type=int, default=80)
    parser.add_argument("--method", type=int, choices=range(0, 7), default=6)
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, max(1, os.cpu_count() or 1)),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.max_width < 1 or args.max_height < 1:
        raise ValueError("Thumbnail bounds must be positive")
    if not 1 <= args.quality <= 100:
        raise ValueError("WebP quality must be between 1 and 100")
    if args.workers < 1:
        raise ValueError("Worker count must be positive")

    poster_dir = args.posters.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks, source_bytes = load_tasks(
        args.inventory.resolve(),
        poster_dir,
        output_dir,
        max_width=args.max_width,
        max_height=args.max_height,
        quality=args.quality,
        method=args.method,
    )

    print(
        f"Generating {len(tasks)} WebP thumbnails at up to "
        f"{args.max_width}x{args.max_height}, quality {args.quality}."
    )
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for position, result in enumerate(
            executor.map(generate_one, tasks, chunksize=8), start=1
        ):
            results.append(result)
            if position % 250 == 0 or position == len(tasks):
                print(f"Generated {position}/{len(tasks)}")

    expected_names = {f"{task['image_id']}.webp" for task in tasks}
    actual_names = {path.name for path in output_dir.glob("*.webp") if path.is_file()}
    missing_outputs = sorted(expected_names - actual_names)
    unexpected_outputs = sorted(actual_names - expected_names)
    if missing_outputs or unexpected_outputs:
        raise ValueError(
            f"Thumbnail set mismatch: {len(missing_outputs)} missing, "
            f"{len(unexpected_outputs)} unexpected"
        )

    results.sort(key=lambda row: row["image_id"])
    thumbnail_bytes = sum(row["size_bytes"] for row in results)
    content_hashes: dict[str, list[str]] = defaultdict(list)
    for row in results:
        content_hashes[row["sha256"]].append(row["thumbnail_filename"])
    duplicate_content = {
        digest: names for digest, names in content_hashes.items() if len(names) > 1
    }
    summary = {
        "complete": len(results) == len(tasks),
        "generated_thumbnails": len(results),
        "max_width": args.max_width,
        "max_height": args.max_height,
        "quality": args.quality,
        "webp_method": args.method,
        "source_bytes": source_bytes,
        "thumbnail_bytes": thumbnail_bytes,
        "average_thumbnail_bytes": round(thumbnail_bytes / len(results), 2),
        "smallest_thumbnail_bytes": min(row["size_bytes"] for row in results),
        "largest_thumbnail_bytes": max(row["size_bytes"] for row in results),
        "size_reduction_percent": round(
            (1 - thumbnail_bytes / source_bytes) * 100, 2
        ),
        "duplicate_thumbnail_content": duplicate_content,
        "missing_outputs": missing_outputs,
        "unexpected_outputs": unexpected_outputs,
    }
    write_reports(results, summary, args.csv_report, args.json_report)

    print(f"Verified thumbnails: {len(results)}")
    print(f"Thumbnail size: {thumbnail_bytes / 1024 / 1024:.2f} MiB")
    print(f"Average size: {thumbnail_bytes / len(results) / 1024:.1f} KiB")
    print(f"Reduction from originals: {summary['size_reduction_percent']:.2f}%")
    print(f"CSV report: {args.csv_report}")
    print(f"JSON report: {args.json_report}")


if __name__ == "__main__":
    main()
