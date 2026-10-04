"""Authenticated watchlist and rating routes backed by PostgreSQL."""

from decimal import Decimal
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import AuthenticatedUser, require_user
from database.models import Drama, Rating, WatchlistItem
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


def _storage_url(object_key: str | None) -> str | None:
    if not object_key:
        return None
    base = get_database_settings().supabase_url.rstrip("/")
    encoded_key = quote(object_key, safe="/")
    return f"{base}/storage/v1/object/public/drama-posters/{encoded_key}"


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


def _library_rows(db: Session, user_id) -> list[tuple[WatchlistItem, Drama]]:
    return list(
        db.execute(
            select(WatchlistItem, Drama)
            .join(Drama, Drama.id == WatchlistItem.drama_id)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.updated_at.desc(), WatchlistItem.created_at.desc())
        ).all()
    )


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
