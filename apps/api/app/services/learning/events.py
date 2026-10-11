"""Append-only outfit event logging for the learning pipeline."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutfitEvent, OutfitEventType, UserStyleState
from app.services.learning.style_dna import update_style_state_from_event


async def append_event(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    outfit_id: uuid.UUID,
    event_type: str,
    position: int | None = None,
    style_tags: list[str] | tuple[str, ...] | set[str] | None = None,
) -> OutfitEvent:
    """Persist a new event append-only and apply style DNA feedback."""
    normalized = str(event_type).strip().lower()
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

    state_result = await db.execute(select(UserStyleState).where(UserStyleState.user_id == user_id))
    state = state_result.scalar_one_or_none()
    if state is None:
        state = UserStyleState(user_id=user_id, style_dna={"style_vector": {}, "tag_affinities": {}}, n_events=0)
        db.add(state)
        await db.flush()

    current_style_state = state.style_dna or {"style_vector": {}, "tag_affinities": {}}
    updated = update_style_state_from_event(current_style_state, normalized, style_tags)
    state.style_dna = updated
    state.n_events += 1
    return event
