"""Import the canonical K-drama catalog into PostgreSQL.

The command is safe to rerun: dramas and lookup values are upserted, while each
imported drama's normalized relationships are replaced inside one transaction.
Remote poster URLs are used only to recover the stable image ID; they are never
stored as a runtime fallback.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.models import (  # noqa: E402
    Drama,
    DramaCredit,
    DramaGenre,
    DramaKeyword,
    Genre,
    Keyword,
    Person,
)
from database.session import SessionLocal  # noqa: E402


DEFAULT_CSV = PROJECT_DIR / "data" / "final" / "kdrama_dataset.csv"
DEFAULT_META = PROJECT_DIR / "training" / "faiss_index" / "meta.pkl"
DEFAULT_POSTERS = (
    PROJECT_DIR
    / "scrapers"
    / "DramaList_Scrapper"
    / "output"
    / "drama_image_by_id"
)
POSTER_ID_PATTERN = re.compile(r"\[([^\[\]]+)\]\.[A-Za-z0-9]+$")


def normalized_join_key(title: object, aired: object) -> tuple[str, str]:
    clean = lambda value: re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    return clean(title), clean(aired)


def poster_id_from_url(image_url: str) -> str:
    return os.path.splitext(os.path.basename(urlparse(image_url).path))[0]


def slug_part(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "drama"


def split_values(value: object) -> list[str]:
    return list(
        dict.fromkeys(
            part.strip() for part in str(value or "").split(",") if part.strip()
        )
    )


def optional_int(value: object) -> int | None:
    cleaned = str(value or "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def optional_decimal(value: object) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None
    try:
        return f"{float(cleaned):.1f}"
    except ValueError:
        return None


def row_hash(row: dict[str, str]) -> str:
    canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_source(
    csv_path: Path, meta_path: Path, poster_dir: Path
) -> tuple[list[dict[str, Any]], dict[str, set[str]], dict[str, list[tuple[str, int]]]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    with meta_path.open("rb") as handle:
        metadata = pickle.load(handle)

    if len(source_rows) != len(metadata):
        raise ValueError(
            f"Catalog/index mismatch: {len(source_rows)} CSV rows and "
            f"{len(metadata)} metadata rows"
        )

    meta_positions: dict[tuple[str, str], int] = {}
    for position, drama in enumerate(metadata):
        key = normalized_join_key(drama.get("Title"), drama.get("Release Years"))
        if key in meta_positions:
            raise ValueError(f"Duplicate FAISS metadata key at position {position}: {key}")
        meta_positions[key] = position

    poster_files: dict[str, Path] = {}
    for path in poster_dir.iterdir():
        match = POSTER_ID_PATTERN.search(path.name)
        if match and path.is_file():
            poster_files[match.group(1)] = path

    dramas: list[dict[str, Any]] = []
    relations: dict[str, set[str]] = {}
    credits: dict[str, list[tuple[str, int]]] = {}
    seen_source_keys: set[str] = set()
    seen_slugs: set[str] = set()

    for row in source_rows:
        join_key = normalized_join_key(row.get("title"), row.get("aired"))
        if join_key not in meta_positions:
            raise ValueError(f"CSV row is absent from FAISS metadata: {join_key}")

        image_id = poster_id_from_url(row.get("image", ""))
        if not image_id or image_id in seen_source_keys:
            raise ValueError(f"Missing or duplicate image/source ID: {image_id!r}")
        if image_id not in poster_files:
            raise ValueError(f"No local poster for {row.get('title')!r} ({image_id})")

        slug = f"{slug_part(row.get('title', ''))}-{slug_part(image_id)}"
        if slug in seen_slugs:
            raise ValueError(f"Duplicate generated slug: {slug}")
        seen_source_keys.add(image_id)
        seen_slugs.add(slug)

        dramas.append(
            {
                "source_key": image_id,
                "catalog_index": meta_positions[join_key],
                "slug": slug,
                "title": (row.get("title") or "").strip(),
                "alternate_names": split_values(row.get("alternate_names")),
                "description": (row.get("description") or "").strip() or None,
                "image_id": image_id,
                "publisher": (row.get("publisher") or "").strip() or None,
                "rating_value": optional_decimal(row.get("rating_value")),
                "rating_count": optional_int(row.get("rating_count")),
                "episodes": optional_int(row.get("episodes")),
                "aired": (row.get("aired") or "").strip() or None,
                "duration": (row.get("duration") or "").strip() or None,
                "watchers": optional_int(row.get("watchers")),
                "source_hash": row_hash(row),
            }
        )
        relations[f"genres:{image_id}"] = set(split_values(row.get("genres")))
        relations[f"keywords:{image_id}"] = set(split_values(row.get("keywords")))

        for role, column in (
            ("actor", "actors"),
            ("director", "directors"),
            ("screenwriter", "screenwriters"),
        ):
            people = split_values(row.get(column))
            credits[f"{role}:{image_id}"] = [
                (person_name, order) for order, person_name in enumerate(people)
            ]

    positions = [drama["catalog_index"] for drama in dramas]
    if set(positions) != set(range(len(metadata))):
        raise ValueError("Catalog positions are not a complete FAISS index sequence")
    if len(poster_files) != len(dramas):
        extras = sorted(set(poster_files) - seen_source_keys)
        raise ValueError(
            f"Poster count mismatch: {len(poster_files)} files for {len(dramas)} dramas; "
            f"unmatched examples: {extras[:5]}"
        )

    return dramas, relations, credits


def chunked(values: list[dict[str, Any]], size: int = 1_000):
    for offset in range(0, len(values), size):
        yield values[offset : offset + size]


def import_catalog(
    dramas: list[dict[str, Any]],
    relations: dict[str, set[str]],
    credits: dict[str, list[tuple[str, int]]],
    *,
    prune: bool,
) -> dict[str, int]:
    genre_names = sorted(
        {name for key, names in relations.items() if key.startswith("genres:") for name in names}
    )
    keyword_names = sorted(
        {
            name
            for key, names in relations.items()
            if key.startswith("keywords:")
            for name in names
        }
    )
    person_names = sorted({name for items in credits.values() for name, _ in items})

    with SessionLocal.begin() as session:
        for batch in chunked(dramas, 500):
            statement = insert(Drama).values(batch)
            excluded = statement.excluded
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[Drama.source_key],
                    set_={
                        "catalog_index": excluded.catalog_index,
                        "slug": excluded.slug,
                        "title": excluded.title,
                        "alternate_names": excluded.alternate_names,
                        "description": excluded.description,
                        "image_id": excluded.image_id,
                        "publisher": excluded.publisher,
                        "rating_value": excluded.rating_value,
                        "rating_count": excluded.rating_count,
                        "episodes": excluded.episodes,
                        "aired": excluded.aired,
                        "duration": excluded.duration,
                        "watchers": excluded.watchers,
                        "source_hash": excluded.source_hash,
                    },
                )
            )

        if prune:
            source_keys = [drama["source_key"] for drama in dramas]
            session.execute(delete(Drama).where(Drama.source_key.not_in(source_keys)))

        def upsert_names(model, names: list[str]) -> None:
            for batch in chunked([{"name": name} for name in names]):
                session.execute(
                    insert(model).values(batch).on_conflict_do_nothing(index_elements=[model.name])
                )

        upsert_names(Genre, genre_names)
        upsert_names(Keyword, keyword_names)
        upsert_names(Person, person_names)

        drama_ids = dict(session.execute(select(Drama.source_key, Drama.id)).all())
        session.bulk_update_mappings(
            Drama,
            [
                {
                    "id": drama_ids[drama["source_key"]],
                    "poster_original_key": (
                        f"dramas/{drama_ids[drama['source_key']]}/original.jpg"
                    ),
                    "poster_thumbnail_key": (
                        f"dramas/{drama_ids[drama['source_key']]}/thumbnail.webp"
                    ),
                }
                for drama in dramas
            ],
        )
        genre_ids = dict(session.execute(select(Genre.name, Genre.id)).all())
        keyword_ids = dict(session.execute(select(Keyword.name, Keyword.id)).all())
        person_ids = dict(session.execute(select(Person.name, Person.id)).all())
        imported_ids = [drama_ids[drama["source_key"]] for drama in dramas]

        session.execute(delete(DramaGenre).where(DramaGenre.drama_id.in_(imported_ids)))
        session.execute(delete(DramaKeyword).where(DramaKeyword.drama_id.in_(imported_ids)))
        session.execute(delete(DramaCredit).where(DramaCredit.drama_id.in_(imported_ids)))

        genre_rows: list[dict[str, Any]] = []
        keyword_rows: list[dict[str, Any]] = []
        credit_rows: list[dict[str, Any]] = []
        for drama in dramas:
            source_key = drama["source_key"]
            drama_id = drama_ids[source_key]
            genre_rows.extend(
                {"drama_id": drama_id, "genre_id": genre_ids[name]}
                for name in relations[f"genres:{source_key}"]
            )
            keyword_rows.extend(
                {"drama_id": drama_id, "keyword_id": keyword_ids[name]}
                for name in relations[f"keywords:{source_key}"]
            )
            for role in ("actor", "director", "screenwriter"):
                credit_rows.extend(
                    {
                        "drama_id": drama_id,
                        "person_id": person_ids[name],
                        "role": role,
                        "billing_order": order,
                    }
                    for name, order in credits[f"{role}:{source_key}"]
                )

        for model, rows in (
            (DramaGenre, genre_rows),
            (DramaKeyword, keyword_rows),
            (DramaCredit, credit_rows),
        ):
            for batch in chunked(rows):
                session.execute(insert(model).values(batch))

        return {
            "dramas": len(dramas),
            "genres": len(genre_names),
            "keywords": len(keyword_names),
            "people": len(person_names),
            "drama_genres": len(genre_rows),
            "drama_keywords": len(keyword_rows),
            "drama_credits": len(credit_rows),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--meta", type=Path, default=DEFAULT_META)
    parser.add_argument("--posters", type=Path, default=DEFAULT_POSTERS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete database dramas absent from the source catalog.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dramas, relations, credits = load_source(args.csv, args.meta, args.posters)
    print(f"Validated {len(dramas)} dramas and local poster mappings.")
    print(f"Catalog indexes: 0..{len(dramas) - 1}")
    if args.dry_run:
        print("Dry run complete; the database was not changed.")
        return

    counts = import_catalog(dramas, relations, credits, prune=args.prune)
    print("Catalog import committed:")
    for name, count in counts.items():
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
