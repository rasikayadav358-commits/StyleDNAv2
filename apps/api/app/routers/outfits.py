"""Outfit generation and variation endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Outfit, OutfitEvent, OutfitEventType, OutfitItem, OutfitSlot, User, WardrobeItem
from app.db.session import get_db
from app.deps import get_current_user
from app.services.learning.events import append_event
from app.services.outfits.explain import explain_outfit
from app.services.outfits.generator import generate_outfits as build_outfits
from app.services.outfits.variations import generate_variations

router = APIRouter(prefix="/outfits", tags=["outfits"])


class GenerateOutfitsRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    occasion: list[str] | None = Field(default=None)
    season: str = "all_season"
    style_overrides: dict[str, Any] | None = None
    use_only_wardrobe: bool = True
    add_new_item: bool = False
    n: int = Field(default=10, ge=1, le=50)
    body_shape: str | None = None
    seed: int = 0


class OutfitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    skeleton: str | None = None
    slots: dict[str, str] = Field(default_factory=dict)
    item_ids: list[str] = Field(default_factory=list)
    score: float | None = None
    reasons: list[str] = Field(default_factory=list)


class GenerateOutfitsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outfits: list[OutfitResponse]
    count: int


class VariationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    variation_type: str = Field(..., min_length=1)


class EventRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str = Field(..., min_length=1)
    position: int | None = None
    style_tags: list[str] | None = None


class SaveRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    saved: bool = True


class VariationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outfit_id: uuid.UUID
    variation_type: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outfit_id: uuid.UUID
    event_type: str
    status: str = "logged"


class SaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outfit_id: uuid.UUID
    saved: bool


class SavedOutfitsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outfits: list[OutfitResponse]
    count: int


async def _get_user_outfit_or_404(db: AsyncSession, outfit_id: uuid.UUID, user_id: uuid.UUID) -> Outfit:
    stmt = select(Outfit).where(Outfit.id == outfit_id, Outfit.user_id == user_id)
    result = await db.execute(stmt)
    outfit = result.scalar_one_or_none()
    if outfit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outfit not found")
    return outfit


async def _log_event(db: AsyncSession, user_id: uuid.UUID, outfit_id: uuid.UUID, event_type: str, position: int | None = None) -> None:
    normalized = event_type.strip().lower()
    try:
        enum_value = OutfitEventType(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported event type") from exc

    event = OutfitEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        outfit_id=outfit_id,
        type=enum_value,
        position=position,
    )
    db.add(event)
    await db.flush()


@router.post("/generate", response_model=GenerateOutfitsResponse, status_code=status.HTTP_200_OK)
async def generate_outfits(
    body: GenerateOutfitsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate outfit candidates from the authenticated user's wardrobe."""
    stmt = select(WardrobeItem).where(
        cast(WardrobeItem.user_id, String) == str(current_user.id),
        WardrobeItem.is_available.is_(True),
    )
    result = await db.execute(stmt)
    wardrobe_items = list(result.scalars().all())

    if body.occasion:
        filter_values = {value.strip().lower() for value in body.occasion if value}
        wardrobe_items = [
            item
            for item in wardrobe_items
            if not item.occasions or any(str(occasion).strip().lower() in filter_values for occasion in (item.occasions or []))
        ]

    candidate_models = build_outfits(
        wardrobe_items,
        occasion=(body.occasion[0] if body.occasion else "casual"),
        season=body.season,
        body_shape=body.body_shape,
        attrs=body.style_overrides or {},
        seed=body.seed,
        limit=max(body.n, 1),
        max_candidates=5000,
    )

    created_outfits: list[OutfitResponse] = []
    for index, candidate in enumerate(candidate_models):
        outfit = Outfit(
            id=uuid.uuid4(),
            user_id=current_user.id,
            occasion=(body.occasion[0] if body.occasion else "casual"),
            context={"skeleton": candidate.skeleton, "seed": body.seed},
            score_rules=float(
                0.0 if not candidate else 0.0
            ),
            score_model=None,
            score_final=None,
            policy=None,
            propensity=None,
            features={"body_fit": 0.5, "color": 0.5, "style": 0.5, "occasion": 0.5, "season": 0.5, "layering": 0.5, "novelty": 0.5},
            explanation={"reasons": explain_outfit(candidate, occasion=(body.occasion[0] if body.occasion else "casual"), season=body.season, body_shape=body.body_shape, attrs=body.style_overrides or {})},
            saved=False,
        )
        db.add(outfit)
        await db.flush()

        for slot_name, item in candidate.slots.items():
            slot_value = slot_name.lower()
            slot_enum = None
            for enum_member in OutfitSlot:
                if enum_member.value == slot_value:
                    slot_enum = enum_member
                    break
            if slot_enum is None:
                slot_enum = OutfitSlot.ACCESSORY
            outfit_item = OutfitItem(
                id=uuid.uuid4(),
                outfit_id=outfit.id,
                slot=slot_enum,
                wardrobe_item_id=getattr(item, "id", None),
                product_id=None,
            )
            db.add(outfit_item)

        await _log_event(db, current_user.id, outfit.id, "impression", position=index)
        created_outfits.append(
            OutfitResponse(
                id=outfit.id,
                skeleton=candidate.skeleton,
                slots={slot: str(item.id) for slot, item in candidate.slots.items()},
                item_ids=[str(item_id) for item_id in candidate.item_ids],
                score=0.0,
                reasons=explain_outfit(candidate, occasion=(body.occasion[0] if body.occasion else "casual"), season=body.season, body_shape=body.body_shape, attrs=body.style_overrides or {}),
            )
        )

    await db.commit()
    return GenerateOutfitsResponse(outfits=created_outfits, count=len(created_outfits))


@router.post("/{outfit_id}/variation", response_model=VariationResponse, status_code=status.HTTP_200_OK)
async def create_variation(
    outfit_id: uuid.UUID,
    body: VariationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    outfit = await _get_user_outfit_or_404(db, outfit_id, current_user.id)
    slots = {item.slot.value: item.wardrobe_item_id for item in (await db.execute(select(OutfitItem).where(OutfitItem.outfit_id == outfit.id))).scalars().all()}
    candidate = {"slots": {slot: {"id": item_id} for slot, item_id in slots.items() if item_id is not None}}
    variations = generate_variations(candidate, occasion=outfit.occasion or "casual", season="all_season")
    selected = next((variation for variation in variations if variation["type"] == body.variation_type), None)
    if selected is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported variation type")

    new_outfit = Outfit(
        id=uuid.uuid4(),
        user_id=current_user.id,
        occasion=outfit.occasion,
        context={"variation_type": body.variation_type, "parent_outfit_id": str(outfit.id)},
        saved=False,
        explanation={"reasons": selected["constraints"]},
    )
    db.add(new_outfit)
    await db.flush()
    await _log_event(db, current_user.id, new_outfit.id, "variation")
    await db.commit()
    return VariationResponse(outfit_id=new_outfit.id, variation_type=body.variation_type, constraints=selected["constraints"])


@router.post("/{outfit_id}/events", response_model=EventResponse, status_code=status.HTTP_200_OK)
async def record_outfit_event(
    outfit_id: uuid.UUID,
    body: EventRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_outfit_or_404(db, outfit_id, current_user.id)
    await append_event(
        db,
        user_id=current_user.id,
        outfit_id=outfit_id,
        event_type=body.type,
        position=body.position,
        style_tags=body.style_tags,
    )
    await db.commit()
    return EventResponse(outfit_id=outfit_id, event_type=body.type, status="logged")


@router.post("/{outfit_id}/save", response_model=SaveResponse, status_code=status.HTTP_200_OK)
async def save_outfit(
    outfit_id: uuid.UUID,
    body: SaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    outfit = await _get_user_outfit_or_404(db, outfit_id, current_user.id)
    outfit.saved = body.saved
    db.add(outfit)
    await _log_event(db, current_user.id, outfit.id, "save")
    await db.commit()
    return SaveResponse(outfit_id=outfit.id, saved=outfit.saved)


@router.get("/saved", response_model=SavedOutfitsResponse, status_code=status.HTTP_200_OK)
async def list_saved_outfits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Outfit).where(Outfit.user_id == current_user.id, Outfit.saved.is_(True)).order_by(Outfit.created_at.desc())
    result = await db.execute(stmt)
    outfits = result.scalars().all()

    response_items: list[OutfitResponse] = []
    for outfit in outfits:
        response_items.append(
            OutfitResponse(
                id=outfit.id,
                skeleton=(outfit.context or {}).get("skeleton"),
                slots={},
                item_ids=[],
                score=float(outfit.score_final) if outfit.score_final is not None else None,
                reasons=(outfit.explanation or {}).get("reasons", []),
            )
        )

    return SavedOutfitsResponse(outfits=response_items, count=len(response_items))
