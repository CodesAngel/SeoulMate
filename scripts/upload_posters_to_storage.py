"""Upload and verify all poster variants in Supabase Storage.

The command is safe to rerun. Objects are upserted at deterministic paths, and
the database poster key is updated only after every upload passes metadata and
public HTTP verification.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from sqlalchemy import select, text


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.models import Drama  # noqa: E402
from database.session import SessionLocal  # noqa: E402
from database.settings import get_database_settings  # noqa: E402


BUCKET_NAME = "drama-posters"
BUCKET_FILE_LIMIT = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/webp"}
DEFAULT_ORIGINALS = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_by_id"
)
DEFAULT_THUMBNAILS = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_cards"
)
DEFAULT_POSTER_MANIFEST = (
    PROJECT_DIR / "data" / "reports" / "poster_inventory.csv"
)
DEFAULT_THUMBNAIL_MANIFEST = (
    PROJECT_DIR / "data" / "reports" / "poster_thumbnail_manifest.csv"
)
DEFAULT_CSV_REPORT = (
    PROJECT_DIR / "data" / "reports" / "poster_storage_manifest.csv"
)
DEFAULT_JSON_REPORT = (
    PROJECT_DIR / "data" / "reports" / "poster_storage_summary.json"
)
_thread_local = threading.local()


def http_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authenticated_headers(secret_key: str, **extra: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {secret_key}",
        "apikey": secret_key,
        **extra,
    }


def ensure_bucket(storage_url: str, secret_key: str) -> dict[str, Any]:
    headers = authenticated_headers(secret_key, **{"Content-Type": "application/json"})
    response = requests.get(
        f"{storage_url}/bucket/{BUCKET_NAME}", headers=headers, timeout=30
    )
    payload = {
        "id": BUCKET_NAME,
        "name": BUCKET_NAME,
        "public": True,
        "file_size_limit": BUCKET_FILE_LIMIT,
        "allowed_mime_types": sorted(ALLOWED_MIME_TYPES),
    }
    if response.status_code == 404:
        response = requests.post(
            f"{storage_url}/bucket", headers=headers, json=payload, timeout=30
        )
        if not response.ok:
            raise RuntimeError(
                f"Could not create Storage bucket ({response.status_code}): "
                f"{response.text[:300]}"
            )
    elif not response.ok:
        raise RuntimeError(
            f"Could not inspect Storage bucket ({response.status_code}): "
            f"{response.text[:300]}"
        )

    response = requests.get(
        f"{storage_url}/bucket/{BUCKET_NAME}", headers=headers, timeout=30
    )
    response.raise_for_status()
    bucket = response.json()
    bucket_mimes = set(bucket.get("allowed_mime_types") or [])
    if (
        bucket.get("public") is not True
        or bucket.get("file_size_limit") != BUCKET_FILE_LIMIT
        or bucket_mimes != ALLOWED_MIME_TYPES
    ):
        raise ValueError(
            "Existing drama-posters bucket does not match the required public, "
            "size-limit, and MIME-type settings"
        )
    return bucket


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required manifest is missing: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_upload_tasks(args: argparse.Namespace) -> tuple[list[dict[str, Any]], int]:
    originals = read_csv(args.poster_manifest.resolve())
    thumbnails = read_csv(args.thumbnail_manifest.resolve())
    original_by_id = {row["image_id"]: row for row in originals}
    thumbnail_by_id = {row["image_id"]: row for row in thumbnails}
    if len(original_by_id) != len(originals):
        raise ValueError("Original poster manifest contains duplicate image IDs")
    if len(thumbnail_by_id) != len(thumbnails):
        raise ValueError("Thumbnail manifest contains duplicate image IDs")

    with SessionLocal() as session:
        dramas = list(
            session.execute(
                select(Drama.id, Drama.image_id, Drama.title).order_by(Drama.id)
            ).all()
        )
    if len(dramas) != len(originals) or len(dramas) != len(thumbnails):
        raise ValueError(
            f"Count mismatch: {len(dramas)} database dramas, "
            f"{len(originals)} originals, and {len(thumbnails)} thumbnails"
        )

    tasks: list[dict[str, Any]] = []
    for drama in dramas:
        original = original_by_id.get(drama.image_id)
        thumbnail = thumbnail_by_id.get(drama.image_id)
        if original is None or thumbnail is None:
            raise ValueError(
                f"Missing local poster variant for drama {drama.id} ({drama.image_id})"
            )
        if int(original["drama_id"]) != drama.id:
            raise ValueError(f"Original manifest association changed for drama {drama.id}")
        if int(thumbnail["drama_id"]) != drama.id:
            raise ValueError(f"Thumbnail manifest association changed for drama {drama.id}")

        original_path = (args.originals.resolve() / original["actual_filename"]).resolve()
        thumbnail_path = (
            args.thumbnails.resolve() / thumbnail["thumbnail_filename"]
        ).resolve()
        variants = (
            (
                "original",
                original_path,
                "image/jpeg",
                original["sha256"],
                f"dramas/{drama.id}/original.jpg",
            ),
            (
                "thumbnail",
                thumbnail_path,
                "image/webp",
                thumbnail["sha256"],
                f"dramas/{drama.id}/thumbnail.webp",
            ),
        )
        for variant, local_path, content_type, digest, object_path in variants:
            if not local_path.is_file():
                raise FileNotFoundError(f"Local {variant} is missing: {local_path}")
            if local_path.stat().st_size > BUCKET_FILE_LIMIT:
                raise ValueError(f"Local file exceeds bucket limit: {local_path}")
            tasks.append(
                {
                    "drama_id": drama.id,
                    "image_id": drama.image_id,
                    "variant": variant,
                    "local_path": str(local_path),
                    "object_path": object_path,
                    "content_type": content_type,
                    "size_bytes": local_path.stat().st_size,
                    "sha256": digest,
                    "database_original_key": f"dramas/{drama.id}/original.jpg",
                    "database_thumbnail_key": f"dramas/{drama.id}/thumbnail.webp",
                }
            )
    return tasks, len(dramas)


def upload_one(task: dict[str, Any]) -> dict[str, Any]:
    local_path = Path(task["local_path"])
    if local_path.stat().st_size != task["size_bytes"]:
        raise ValueError(f"Local size changed before upload: {local_path.name}")
    if sha256_file(local_path) != task["sha256"]:
        raise ValueError(f"Local content changed before upload: {local_path.name}")

    url = (
        f"{task['storage_url']}/object/{BUCKET_NAME}/"
        f"{quote(task['object_path'], safe='/')}"
    )
    headers = authenticated_headers(
        task["secret_key"],
        **{
            "Content-Type": task["content_type"],
            "x-upsert": "true",
            "cache-control": "max-age=3600",
        },
    )
    response: requests.Response | None = None
    for attempt in range(3):
        try:
            with local_path.open("rb") as handle:
                response = http_session().post(
                    url, headers=headers, data=handle, timeout=120
                )
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(0.5 * (attempt + 1))
            continue
        if response.status_code < 500 and response.status_code != 429:
            break
        time.sleep(0.5 * (attempt + 1))

    if response is None or not response.ok:
        status = response.status_code if response is not None else "no response"
        detail = response.text[:300] if response is not None else ""
        raise RuntimeError(
            f"Upload failed for {task['object_path']} ({status}): {detail}"
        )
    return task


def verify_public_object(task: dict[str, Any]) -> dict[str, Any]:
    url = (
        f"{task['storage_url']}/object/public/{BUCKET_NAME}/"
        f"{quote(task['object_path'], safe='/')}"
    )
    response = http_session().head(url, timeout=60)
    content_length = int(response.headers.get("content-length", "-1"))
    content_type = response.headers.get("content-type", "").split(";", 1)[0]
    if (
        response.status_code != 200
        or content_length != task["size_bytes"]
        or content_type != task["content_type"]
    ):
        raise ValueError(
            f"Public object verification failed for {task['object_path']}: "
            f"status={response.status_code}, size={content_length}, "
            f"type={content_type}"
        )
    return {
        "object_path": task["object_path"],
        "http_status": response.status_code,
        "http_content_length": content_length,
        "http_content_type": content_type,
    }


def storage_metadata() -> dict[str, dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.execute(
            text(
                "select name, metadata from storage.objects "
                "where bucket_id = :bucket order by name"
            ),
            {"bucket": BUCKET_NAME},
        ).all()
    return {row.name: row.metadata for row in rows}


def update_and_verify_database(tasks: list[dict[str, Any]], drama_count: int) -> None:
    original_tasks = [task for task in tasks if task["variant"] == "original"]
    mappings = [
        {
            "id": task["drama_id"],
            "poster_original_key": task["database_original_key"],
            "poster_thumbnail_key": task["database_thumbnail_key"],
        }
        for task in original_tasks
    ]
    with SessionLocal.begin() as session:
        session.bulk_update_mappings(Drama, mappings)

    with SessionLocal() as session:
        rows = session.execute(
            select(Drama.id, Drama.poster_original_key, Drama.poster_thumbnail_key)
        ).all()
    actual = {
        row.id: (row.poster_original_key, row.poster_thumbnail_key) for row in rows
    }
    mismatches = [
        task["drama_id"]
        for task in original_tasks
        if actual.get(task["drama_id"])
        != (task["database_original_key"], task["database_thumbnail_key"])
    ]
    if len(actual) != drama_count or mismatches:
        raise ValueError(
            f"Database association verification failed: {len(mismatches)} mismatches"
        )


def write_reports(
    tasks: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    public_results: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    csv_report: Path,
    json_report: Path,
) -> None:
    rows: list[dict[str, Any]] = []
    for task in sorted(
        tasks, key=lambda item: (item["drama_id"], item["variant"] != "original")
    ):
        object_metadata = metadata[task["object_path"]]
        public = public_results[task["object_path"]]
        rows.append(
            {
                "drama_id": task["drama_id"],
                "image_id": task["image_id"],
                "variant": task["variant"],
                "object_path": task["object_path"],
                "content_type": task["content_type"],
                "size_bytes": task["size_bytes"],
                "sha256": task["sha256"],
                "storage_size": object_metadata.get("size"),
                "storage_content_type": object_metadata.get("mimetype"),
                "http_status": public["http_status"],
                "http_content_length": public["http_content_length"],
                "http_content_type": public["http_content_type"],
                "database_original_key": task["database_original_key"],
                "database_thumbnail_key": task["database_thumbnail_key"],
            }
        )
    csv_report.parent.mkdir(parents=True, exist_ok=True)
    json_report.parent.mkdir(parents=True, exist_ok=True)
    with csv_report.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with json_report.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals", type=Path, default=DEFAULT_ORIGINALS)
    parser.add_argument("--thumbnails", type=Path, default=DEFAULT_THUMBNAILS)
    parser.add_argument("--poster-manifest", type=Path, default=DEFAULT_POSTER_MANIFEST)
    parser.add_argument(
        "--thumbnail-manifest", type=Path, default=DEFAULT_THUMBNAIL_MANIFEST
    )
    parser.add_argument("--csv-report", type=Path, default=DEFAULT_CSV_REPORT)
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument(
        "--workers", type=int, default=min(16, max(1, os.cpu_count() or 1))
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("Worker count must be positive")
    settings = get_database_settings()
    storage_url = f"{settings.supabase_url.rstrip('/')}/storage/v1"
    bucket = ensure_bucket(storage_url, settings.supabase_secret_key)
    tasks, drama_count = build_upload_tasks(args)
    for task in tasks:
        task["storage_url"] = storage_url
        task["secret_key"] = settings.supabase_secret_key

    print(
        f"Uploading {len(tasks)} objects for {drama_count} dramas to "
        f"{BUCKET_NAME}.",
        flush=True,
    )
    uploaded: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for position, result in enumerate(executor.map(upload_one, tasks), start=1):
            uploaded.append(result)
            if position % 500 == 0 or position == len(tasks):
                print(f"Uploaded {position}/{len(tasks)}", flush=True)

    expected_paths = {task["object_path"] for task in tasks}
    metadata = storage_metadata()
    actual_paths = set(metadata)
    missing_objects = sorted(expected_paths - actual_paths)
    unexpected_objects = sorted(actual_paths - expected_paths)
    metadata_mismatches: list[str] = []
    for task in tasks:
        item = metadata.get(task["object_path"])
        if item is None:
            continue
        if (
            int(item.get("size", -1)) != task["size_bytes"]
            or item.get("mimetype") != task["content_type"]
        ):
            metadata_mismatches.append(task["object_path"])
    if missing_objects or unexpected_objects or metadata_mismatches:
        raise ValueError(
            f"Storage metadata verification failed: {len(missing_objects)} missing, "
            f"{len(unexpected_objects)} unexpected, "
            f"{len(metadata_mismatches)} metadata mismatches"
        )
    print(f"Storage metadata verified: {len(tasks)}/{len(tasks)}", flush=True)

    public_verifications: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for position, result in enumerate(
            executor.map(verify_public_object, tasks), start=1
        ):
            public_verifications.append(result)
            if position % 500 == 0 or position == len(tasks):
                print(f"Public URLs verified {position}/{len(tasks)}", flush=True)
    public_results = {item["object_path"]: item for item in public_verifications}

    update_and_verify_database(tasks, drama_count)
    print(f"Database associations verified: {drama_count}/{drama_count}", flush=True)

    original_bytes = sum(
        task["size_bytes"] for task in tasks if task["variant"] == "original"
    )
    thumbnail_bytes = sum(
        task["size_bytes"] for task in tasks if task["variant"] == "thumbnail"
    )
    summary = {
        "complete": True,
        "bucket": BUCKET_NAME,
        "bucket_public": bucket["public"],
        "bucket_file_size_limit": bucket["file_size_limit"],
        "bucket_allowed_mime_types": sorted(bucket["allowed_mime_types"]),
        "database_dramas": drama_count,
        "uploaded_objects": len(uploaded),
        "verified_storage_metadata": len(metadata),
        "verified_public_urls": len(public_results),
        "verified_database_associations": drama_count,
        "original_bytes": original_bytes,
        "thumbnail_bytes": thumbnail_bytes,
        "total_bytes": original_bytes + thumbnail_bytes,
        "missing_objects": missing_objects,
        "unexpected_objects": unexpected_objects,
        "metadata_mismatches": metadata_mismatches,
    }
    for task in tasks:
        task.pop("secret_key", None)
        task.pop("storage_url", None)
    write_reports(
        tasks,
        metadata,
        public_results,
        summary,
        args.csv_report,
        args.json_report,
    )
    print(f"Verified objects: {len(tasks)}", flush=True)
    print(f"Total stored data: {summary['total_bytes'] / 1024 / 1024:.2f} MiB")
    print(f"CSV report: {args.csv_report}")
    print(f"JSON report: {args.json_report}")


if __name__ == "__main__":
    main()
