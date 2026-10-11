"""Counterfactual wardrobe gap analysis and wishlist storage."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, WardrobeItem, WishlistItem
from app.db.session import get_db
from app.deps import get_current_user
from app.services.catalog.gaps import analyze_gaps

router = APIRouter(tags=["catalog"])


class GapItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    suitability: float
    utility: float
    new_outfits_total: int
    new_outfits_by_occasion: dict[str, int]


class GapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    results: list[GapItemResponse]
    count: int


class WishlistRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID | None = None
    outfit_id: uuid.UUID | None = None
    note: str | None = None


class WishlistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID | None = None
    outfit_id: uuid.UUID | None = None
    note: str | None = None
    created_at: datetime


class WishlistListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[WishlistResponse]
    count: int


@router.get("/gaps", response_model=GapResponse, status_code=status.HTTP_200_OK)
async def get_gaps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WardrobeItem).where(
        WardrobeItem.user_id == current_user.id,
        WardrobeItem.is_available.is_(True),
    )
    result = await db.execute(stmt)
    wardrobe = list(result.scalars().all())
    payload = analyze_gaps([
        {
            "id": str(item.id),
            "category": item.category,
            "style": item.style_tags[0] if item.style_tags else None,
            "color": item.colors[0].get("hex") if item.colors and isinstance(item.colors[0], dict) else None,
            "formality": item.formality,
            "season": "all_season",
            "seasons": item.seasons or ["all_season"],
            "occasions": item.occasions or ["casual"],
            "is_available": item.is_available,
        }
        for item in wardrobe
    ])
    return GapResponse(results=[GapItemResponse(**entry) for entry in payload["results"]], count=payload["count"])


@router.post("/wishlist", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def create_wishlist_item(
    body: WishlistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.product_id is None and body.outfit_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either product_id or outfit_id is required")

    entry = WishlistItem(
        id=uuid.uuid4(),
        user_id=current_user.id,
        product_id=body.product_id,
        outfit_id=body.outfit_id,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return WishlistResponse(
        id=entry.id,
        user_id=entry.user_id,
        product_id=entry.product_id,
        outfit_id=entry.outfit_id,
        note=body.note,
        created_at=entry.created_at,
    )


@router.get("/wishlist", response_model=WishlistListResponse, status_code=status.HTTP_200_OK)
async def list_wishlist_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WishlistItem).where(WishlistItem.user_id == current_user.id).order_by(WishlistItem.created_at.desc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    return WishlistListResponse(
        items=[
            WishlistResponse(
                id=item.id,
                user_id=item.user_id,
                product_id=item.product_id,
                outfit_id=item.outfit_id,
                note=None,
                created_at=item.created_at,
            )
            for item in items
        ],
        count=len(items),
    )


@router.delete("/wishlist/{wishlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wishlist_item(
    wishlist_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(WishlistItem).where(WishlistItem.id == wishlist_id, WishlistItem.user_id == current_user.id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist item not found")
    await db.delete(item)
    await db.commit()
    return None
