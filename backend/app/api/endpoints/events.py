from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.event import AttackEvent, EventType
from app.services.event_processor import process_event
from app.services.insider import InsiderContext

router = APIRouter()


class EventOut(BaseModel):
    id: uuid.UUID
    honeypot_id: uuid.UUID | None
    canary_id: uuid.UUID | None
    event_type: EventType
    source_ip: str
    source_port: int | None
    username: str | None
    raw_log: str | None
    parsed_data: dict | None
    mitre_technique: str | None
    mitre_tactic: str | None
    threat_score: int
    session_id: str | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int


class IngestEventRequest(BaseModel):
    honeypot_id: uuid.UUID | None = None
    canary_id: uuid.UUID | None = None
    event_type: EventType
    source_ip: str
    source_port: int | None = None
    username: str | None = None
    raw_log: str | None = None
    parsed_data: dict | None = None
    session_id: str | None = None
    insider: InsiderContext | None = None

    @model_validator(mode="after")
    def validate_insider_metadata(self):
        metadata = dict(self.parsed_data or {})
        metadata.pop("insider_assessment", None)  # Findings are server-generated.
        if self.insider is not None and "insider" in metadata:
            raise ValueError("Provide insider context only once")
        context = self.insider
        if context is None and "insider" in metadata:
            context = InsiderContext.model_validate(metadata["insider"])
        if context is not None:
            metadata["insider"] = context.model_dump()
        self.parsed_data = metadata or None
        return self


@router.get("", response_model=EventListOut)
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    event_type: EventType | None = None,
    source_ip: str | None = None,
    actor_id: str | None = None,
    honeypot_id: uuid.UUID | None = None,
    min_threat_score: int | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    conditions = []
    if event_type:
        conditions.append(AttackEvent.event_type == event_type)
    if source_ip:
        conditions.append(AttackEvent.source_ip == source_ip)
    if actor_id:
        conditions.append(AttackEvent.parsed_data["insider"]["actor_id"].astext == actor_id)
    if honeypot_id:
        conditions.append(AttackEvent.honeypot_id == honeypot_id)
    if min_threat_score is not None:
        conditions.append(AttackEvent.threat_score >= min_threat_score)
    if session_id:
        conditions.append(AttackEvent.session_id == session_id)

    total_q = select(func.count(AttackEvent.id))
    items_q = select(AttackEvent).order_by(AttackEvent.timestamp.desc())
    if conditions:
        total_q = total_q.where(*conditions)
        items_q = items_q.where(*conditions)

    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    items_result = await db.execute(items_q.offset(skip).limit(limit))
    items = items_result.scalars().all()

    return EventListOut(
        items=[EventOut.model_validate(e) for e in items],
        total=total,
    )


@router.post("/ingest", response_model=EventOut)
async def ingest_event(
    payload: IngestEventRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    event = AttackEvent(
        honeypot_id=payload.honeypot_id,
        canary_id=payload.canary_id,
        event_type=payload.event_type,
        source_ip=payload.source_ip,
        source_port=payload.source_port,
        username=payload.username,
        raw_log=payload.raw_log,
        parsed_data=payload.parsed_data,
        session_id=payload.session_id,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    await process_event(db, event)

    return EventOut.model_validate(event)


@router.get("/session/{session_id}", response_model=list[EventOut])
async def get_session_events(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    result = await db.execute(
        select(AttackEvent)
        .where(AttackEvent.session_id == session_id)
        .order_by(AttackEvent.timestamp.asc())
    )
    return [EventOut.model_validate(e) for e in result.scalars().all()]


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    result = await db.execute(select(AttackEvent).where(AttackEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventOut.model_validate(event)

