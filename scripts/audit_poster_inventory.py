"""Audit the one-to-one mapping between database dramas and local posters.

The audit is read-only. It writes a row-level CSV manifest and a JSON summary
that can also be used to verify later Supabase Storage uploads.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from sqlalchemy import select


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.models import Drama  # noqa: E402
from database.session import SessionLocal  # noqa: E402


DEFAULT_POSTERS = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_by_id"
)
DEFAULT_CSV_REPORT = PROJECT_DIR / "data" / "reports" / "poster_inventory.csv"
DEFAULT_JSON_REPORT = (
    PROJECT_DIR / "data" / "reports" / "poster_inventory_summary.json"
)
POSTER_ID_PATTERN = re.compile(r"\[([^\[\]]+)\]\.([A-Za-z0-9]+)$")
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")


def sanitize_label(title: str) -> str:
    """Use the same readable filename rules as the poster downloader."""

    label = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
    label = re.sub(r"[\[\]()]", "", label)
    return re.sub(r"\s+", " ", label).strip() or "untitled"


def expected_filename(title: str, aired: str | None, image_id: str) -> str:
    year_match = YEAR_PATTERN.search(aired or "")
    year_part = f" ({year_match.group(0)})" if year_match else ""
    return f"{sanitize_label(title)}{year_part} [{image_id}].jpg"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_image(path: Path) -> tuple[str | None, int | None, int | None, str | None]:
    try:
        with Image.open(path) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
        return image_format, width, height, None
    except (OSError, UnidentifiedImageError) as error:
        return None, None, None, f"{type(error).__name__}: {error}"


def serialize_paths(paths: list[Path]) -> list[str]:
    return [path.relative_to(PROJECT_DIR).as_posix() for path in paths]


def audit_poster_inventory(poster_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    poster_dir = poster_dir.resolve()
    if not poster_dir.is_dir():
        raise FileNotFoundError(f"Poster directory does not exist: {poster_dir}")

    with SessionLocal() as session:
        dramas = list(
            session.execute(
                select(
                    Drama.id,
                    Drama.source_key,
                    Drama.image_id,
                    Drama.poster_key,
                    Drama.title,
                    Drama.aired,
                ).order_by(Drama.id)
            ).all()
        )

    files = sorted((path for path in poster_dir.iterdir() if path.is_file()), key=lambda p: p.name)
    files_by_id: defaultdict[str, list[Path]] = defaultdict(list)
    unparseable_files: list[Path] = []
    for path in files:
        match = POSTER_ID_PATTERN.search(path.name)
        if match:
            files_by_id[match.group(1)].append(path)
        else:
            unparseable_files.append(path)

    database_ids: defaultdict[str, list[int]] = defaultdict(list)
    for drama in dramas:
        database_ids[drama.image_id or ""].append(drama.id)

    duplicate_database_ids = {
        image_id: drama_ids
        for image_id, drama_ids in database_ids.items()
        if image_id and len(drama_ids) > 1
    }
    duplicate_file_ids = {
        image_id: serialize_paths(paths)
        for image_id, paths in files_by_id.items()
        if len(paths) > 1
    }
    unrecognized_file_ids = {
        image_id: serialize_paths(paths)
        for image_id, paths in files_by_id.items()
        if image_id not in database_ids
    }

    rows: list[dict[str, Any]] = []
    content_hashes: defaultdict[str, list[Path]] = defaultdict(list)
    missing_drama_ids: list[int] = []
    misnamed_files: list[dict[str, str]] = []
    unreadable_files: list[dict[str, str]] = []
    non_jpeg_files: list[dict[str, str]] = []
    database_mapping_mismatches: list[dict[str, Any]] = []

    for drama in dramas:
        image_id = drama.image_id or ""
        expected_name = expected_filename(drama.title, drama.aired, image_id)
        expected_key = f"dramas/{drama.id}/original.jpg"
        matches = files_by_id.get(image_id, [])

        mapping_problems: list[str] = []
        if not image_id:
            mapping_problems.append("missing_database_image_id")
        if drama.source_key != image_id:
            mapping_problems.append("source_key_image_id_mismatch")
        if drama.poster_key != expected_key:
            mapping_problems.append("poster_key_mismatch")
        if mapping_problems:
            database_mapping_mismatches.append(
                {
                    "drama_id": drama.id,
                    "image_id": image_id,
                    "problems": mapping_problems,
                }
            )

        if not matches:
            missing_drama_ids.append(drama.id)
            rows.append(
                {
                    "drama_id": drama.id,
                    "image_id": image_id,
                    "title": drama.title,
                    "aired": drama.aired or "",
                    "expected_filename": expected_name,
                    "actual_filename": "",
                    "status": "missing",
                    "size_bytes": "",
                    "width": "",
                    "height": "",
                    "format": "",
                    "sha256": "",
                }
            )
            continue

        for path in matches:
            statuses: list[str] = []
            if len(matches) > 1:
                statuses.append("duplicate_image_id")
            if path.name != expected_name:
                statuses.append("misnamed")
                misnamed_files.append(
                    {
                        "image_id": image_id,
                        "actual": path.name,
                        "expected": expected_name,
                    }
                )

            image_format, width, height, image_error = inspect_image(path)
            if image_error:
                statuses.append("unreadable")
                unreadable_files.append(
                    {"path": path.relative_to(PROJECT_DIR).as_posix(), "error": image_error}
                )
            elif image_format != "JPEG":
                statuses.append("not_jpeg")
                non_jpeg_files.append(
                    {
                        "path": path.relative_to(PROJECT_DIR).as_posix(),
                        "format": image_format or "unknown",
                    }
                )

            content_hash = sha256_file(path)
            content_hashes[content_hash].append(path)
            rows.append(
                {
                    "drama_id": drama.id,
                    "image_id": image_id,
                    "title": drama.title,
                    "aired": drama.aired or "",
                    "expected_filename": expected_name,
                    "actual_filename": path.name,
                    "status": ";".join(statuses) if statuses else "matched",
                    "size_bytes": path.stat().st_size,
                    "width": width or "",
                    "height": height or "",
                    "format": image_format or "",
                    "sha256": content_hash,
                }
            )

    duplicate_content = {
        content_hash: serialize_paths(paths)
        for content_hash, paths in content_hashes.items()
        if len(paths) > 1
    }
    matched_rows = sum(row["status"] == "matched" for row in rows)
    summary: dict[str, Any] = {
        "database_dramas": len(dramas),
        "poster_files": len(files),
        "poster_bytes": sum(path.stat().st_size for path in files),
        "matched_dramas": matched_rows,
        "missing_drama_ids": missing_drama_ids,
        "duplicate_database_image_ids": duplicate_database_ids,
        "duplicate_file_image_ids": duplicate_file_ids,
        "duplicate_file_content": duplicate_content,
        "misnamed_files": misnamed_files,
        "unrecognized_file_ids": unrecognized_file_ids,
        "unparseable_files": serialize_paths(unparseable_files),
        "unreadable_files": unreadable_files,
        "non_jpeg_files": non_jpeg_files,
        "database_mapping_mismatches": database_mapping_mismatches,
    }
    summary["content_duplicate_review_required"] = bool(duplicate_content)
    summary["complete_one_to_one_mapping"] = (
        len(dramas) == len(files) == matched_rows
        and not duplicate_database_ids
        and not duplicate_file_ids
        and not missing_drama_ids
        and not misnamed_files
        and not unrecognized_file_ids
        and not unparseable_files
        and not unreadable_files
        and not non_jpeg_files
        and not database_mapping_mismatches
    )
    return rows, summary


def write_reports(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    csv_report: Path,
    json_report: Path,
) -> None:
    csv_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.parent.mkdir(parents=True, exist_ok=True)

    with csv_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    with json_report.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--posters", type=Path, default=DEFAULT_POSTERS)
    parser.add_argument("--csv-report", type=Path, default=DEFAULT_CSV_REPORT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, summary = audit_poster_inventory(args.posters)
    write_reports(rows, summary, args.csv_report, args.json_report)

    print(f"Database dramas: {summary['database_dramas']}")
    print(f"Local poster files: {summary['poster_files']}")
    print(f"Clean one-to-one matches: {summary['matched_dramas']}")
    print(f"Missing: {len(summary['missing_drama_ids'])}")
    print(f"Duplicate IDs: {len(summary['duplicate_file_image_ids'])}")
    print(f"Duplicate content: {len(summary['duplicate_file_content'])}")
    print(f"Misnamed: {len(summary['misnamed_files'])}")
    print(f"Unrecognized: {len(summary['unrecognized_file_ids'])}")
    print(f"Unreadable: {len(summary['unreadable_files'])}")
    print(f"CSV report: {args.csv_report}")
    print(f"JSON report: {args.json_report}")
    if not summary["complete_one_to_one_mapping"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
