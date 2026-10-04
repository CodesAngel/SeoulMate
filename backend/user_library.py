"""Authenticated watchlist and rating routes backed by PostgreSQL."""

from decimal import Decimal
import json
from pathlib import Path
from typing import Literal
from urllib.parse import quote

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import AuthenticatedUser, require_user
from database.models import Drama, Profile, Rating, WatchlistItem
from database.session import get_db
from database.settings import get_database_settings


WatchStatus = Literal["planned", "watching", "completed", "paused", "dropped"]
router = APIRouter(prefix="/me", tags=["My library"])


class WatchlistUpdate(BaseModel):
    status: WatchStatus = "planned"


class WatchlistMergeItem(WatchlistUpdate):
    drama_id: int = Field(gt=0)


class WatchlistMergeRequest(BaseModel):
    items: list[WatchlistMergeItem] = Field(default_factory=list, max_length=500)


class RatingUpdate(BaseModel):
    rating: float = Field(ge=1, le=10)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_path: str | None = Field(default=None, max_length=255)

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Display name cannot be empty")
        return cleaned


def _storage_url(object_key: str | None) -> str | None:
    if not object_key:
        return None
    base = get_database_settings().supabase_url.rstrip("/")
    encoded_key = quote(object_key, safe="/")
    return f"{base}/storage/v1/object/public/drama-posters/{encoded_key}"


def _avatar_url(object_key: str | None) -> str | None:
    if not object_key:
        return None
    base = get_database_settings().supabase_url.rstrip("/")
    encoded_key = quote(object_key, safe="/")
    return f"{base}/storage/v1/object/public/avatars/{encoded_key}"


def _drama_payload(drama: Drama) -> dict:
    thumbnail_url = _storage_url(drama.poster_thumbnail_key)
    return {
        "drama_id": drama.id,
        "Title": drama.title,
        "Description": drama.description,
        "Release Years": drama.aired,
        "Network": drama.publisher,
        "rating_value": float(drama.rating_value) if drama.rating_value else None,
        "episodes": drama.episodes,
        "watchers": drama.watchers,
        "image_id": drama.image_id,
        "poster_original_path": drama.poster_original_key,
        "poster_thumbnail_path": drama.poster_thumbnail_key,
        "poster_original_url": _storage_url(drama.poster_original_key),
        "poster_thumbnail_url": thumbnail_url,
        "Image": thumbnail_url,
    }


def _watchlist_payload(item: WatchlistItem, drama: Drama) -> dict:
    return {
        "drama": _drama_payload(drama),
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _require_drama(db: Session, drama_id: int) -> Drama:
    drama = db.get(Drama, drama_id)
    if drama is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drama not found")
    return drama


def _get_or_create_profile(db: Session, current_user: AuthenticatedUser) -> Profile:
    profile = db.get(Profile, current_user.id)
    if profile is None:
        fallback_name = current_user.email.split("@", 1)[0] if current_user.email else None
        profile = Profile(id=current_user.id, display_name=fallback_name)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _profile_payload(profile: Profile) -> dict:
    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "avatar_path": profile.avatar_path,
        "avatar_url": _avatar_url(profile.avatar_path),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def _profile_statistics(db: Session, user_id) -> dict:
    status_rows = db.execute(
        select(WatchlistItem.status, func.count())
        .where(WatchlistItem.user_id == user_id)
        .group_by(WatchlistItem.status)
    ).all()
    status_counts = {watch_status: count for watch_status, count in status_rows}
    rating_count, average_rating = db.execute(
        select(func.count(Rating.drama_id), func.avg(Rating.rating)).where(
            Rating.user_id == user_id
        )
    ).one()
    return {
        "saved_total": sum(status_counts.values()),
        "active_total": sum(
            status_counts.get(key, 0) for key in ("planned", "watching", "paused")
        ),
        "planned": status_counts.get("planned", 0),
        "watching": status_counts.get("watching", 0),
        "completed": status_counts.get("completed", 0),
        "paused": status_counts.get("paused", 0),
        "dropped": status_counts.get("dropped", 0),
        "ratings_total": rating_count,
        "average_rating": round(float(average_rating), 1) if average_rating else None,
    }


def _delete_storage_avatar(object_key: str | None) -> None:
    if not object_key:
        return
    settings = get_database_settings()
    encoded_key = quote(object_key, safe="/")
    response = requests.delete(
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/avatars/{encoded_key}",
        headers={
            "apikey": settings.supabase_secret_key,
            "Authorization": f"Bearer {settings.supabase_secret_key}",
        },
        timeout=15,
    )
    if response.status_code not in (200, 204, 404):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The account avatar could not be removed. Please try again.",
        )


def _purge_legacy_user_data(user_id: str) -> None:
    backend_dir = Path(__file__).resolve().parent
    profile_path = backend_dir / "runtime_data" / "user_profiles" / f"{user_id}.json"
    profile_path.unlink(missing_ok=True)

    analytics_dir = backend_dir / "runtime_data" / "analytics"
    stats_path = analytics_dir / "user_stats.json"
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
            if isinstance(stats, dict) and user_id in stats:
                del stats[user_id]
                stats_path.write_text(
                    json.dumps(stats, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        except (OSError, json.JSONDecodeError):
            pass

    for filename in ("interactions.jsonl", "search_log.jsonl"):
        path = analytics_dir / filename
        if not path.exists():
            continue
        try:
            kept_lines = []
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    kept_lines.append(line)
                    continue
                if record.get("user_id") != user_id:
                    kept_lines.append(line)
            output = "\n".join(kept_lines)
            path.write_text(f"{output}\n" if output else "", encoding="utf-8")
        except OSError:
            pass


def _library_rows(db: Session, user_id) -> list[tuple[WatchlistItem, Drama]]:
    return list(
        db.execute(
            select(WatchlistItem, Drama)
            .join(Drama, Drama.id == WatchlistItem.drama_id)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.updated_at.desc(), WatchlistItem.created_at.desc())
        ).all()
    )


@router.get("/profile")
def get_account_profile(
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, current_user)
    return {
        "profile": _profile_payload(profile),
        "statistics": _profile_statistics(db, current_user.id),
    }


@router.patch("/profile")
def update_account_profile(
    update: ProfileUpdate,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile(db, current_user)
    if "display_name" in update.model_fields_set:
        profile.display_name = update.display_name
    if "avatar_path" in update.model_fields_set:
        if update.avatar_path is not None:
            expected_path = f"{current_user.id}/avatar"
            if update.avatar_path != expected_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid avatar object path",
                )
        elif profile.avatar_path:
            _delete_storage_avatar(profile.avatar_path)
        profile.avatar_path = update.avatar_path
    db.commit()
    db.refresh(profile)
    return {
        "profile": _profile_payload(profile),
        "statistics": _profile_statistics(db, current_user.id),
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    profile = db.get(Profile, current_user.id)
    if profile is not None:
        _delete_storage_avatar(profile.avatar_path)

    settings = get_database_settings()
    response = requests.delete(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{current_user.id}",
        headers={
            "apikey": settings.supabase_secret_key,
            "Authorization": f"Bearer {settings.supabase_secret_key}",
        },
        timeout=15,
    )
    if response.status_code not in (200, 204, 404):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The account could not be deleted. Please try again.",
        )
    _purge_legacy_user_data(str(current_user.id))


@router.get("/watchlist")
def get_watchlist(
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    items = [
        _watchlist_payload(item, drama)
        for item, drama in _library_rows(db, current_user.id)
    ]
    return {"items": items}


@router.put("/watchlist/{drama_id}")
def save_watchlist_item(
    drama_id: int,
    update: WatchlistUpdate,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    drama = _require_drama(db, drama_id)
    item = db.get(
        WatchlistItem,
        {"user_id": current_user.id, "drama_id": drama_id},
    )
    if item is None:
        item = WatchlistItem(
            user_id=current_user.id,
            drama_id=drama_id,
            status=update.status,
        )
        db.add(item)
    else:
        item.status = update.status
    db.commit()
    db.refresh(item)
    return {"item": _watchlist_payload(item, drama)}


@router.post("/watchlist/merge")
def merge_guest_watchlist(
    request: WatchlistMergeRequest,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    requested = {item.drama_id: item.status for item in request.items}
    if requested:
        valid_ids = set(
            db.scalars(select(Drama.id).where(Drama.id.in_(requested))).all()
        )
        missing_ids = sorted(set(requested) - valid_ids)
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown drama IDs: {missing_ids}",
            )
        existing_ids = set(
            db.scalars(
                select(WatchlistItem.drama_id).where(
                    WatchlistItem.user_id == current_user.id,
                    WatchlistItem.drama_id.in_(requested),
                )
            ).all()
        )
        for drama_id, watch_status in requested.items():
            if drama_id not in existing_ids:
                db.add(
                    WatchlistItem(
                        user_id=current_user.id,
                        drama_id=drama_id,
                        status=watch_status,
                    )
                )
        db.commit()

    items = [
        _watchlist_payload(item, drama)
        for item, drama in _library_rows(db, current_user.id)
    ]
    return {"items": items}


@router.delete("/watchlist/{drama_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_watchlist_item(
    drama_id: int,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    item = db.get(
        WatchlistItem,
        {"user_id": current_user.id, "drama_id": drama_id},
    )
    if item is not None:
        db.delete(item)
        db.commit()


@router.get("/ratings")
def get_ratings(
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Rating, Drama)
        .join(Drama, Drama.id == Rating.drama_id)
        .where(Rating.user_id == current_user.id)
        .order_by(Rating.updated_at.desc(), Rating.created_at.desc())
    ).all()
    return {
        "items": [
            {
                "drama": _drama_payload(drama),
                "rating": float(rating.rating),
                "created_at": rating.created_at,
                "updated_at": rating.updated_at,
            }
            for rating, drama in rows
        ]
    }


@router.put("/ratings/{drama_id}")
def save_rating(
    drama_id: int,
    update: RatingUpdate,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    drama = _require_drama(db, drama_id)
    rating = db.get(
        Rating,
        {"user_id": current_user.id, "drama_id": drama_id},
    )
    if rating is None:
        rating = Rating(
            user_id=current_user.id,
            drama_id=drama_id,
            rating=Decimal(str(update.rating)),
        )
        db.add(rating)
    else:
        rating.rating = Decimal(str(update.rating))

    watchlist_item = db.get(
        WatchlistItem,
        {"user_id": current_user.id, "drama_id": drama_id},
    )
    if watchlist_item is None:
        watchlist_item = WatchlistItem(
            user_id=current_user.id,
            drama_id=drama_id,
            status="completed",
        )
        db.add(watchlist_item)
    else:
        watchlist_item.status = "completed"

    db.commit()
    db.refresh(rating)
    db.refresh(watchlist_item)
    return {
        "item": {
            "drama": _drama_payload(drama),
            "rating": float(rating.rating),
            "created_at": rating.created_at,
            "updated_at": rating.updated_at,
        },
        "watchlist_item": _watchlist_payload(watchlist_item, drama),
    }


@router.delete("/ratings/{drama_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_rating(
    drama_id: int,
    current_user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    rating = db.get(
        Rating,
        {"user_id": current_user.id, "drama_id": drama_id},
    )
    if rating is not None:
        db.delete(rating)
        db.commit()
