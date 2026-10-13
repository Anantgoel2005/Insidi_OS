from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.alert import Alert
from app.models.event import AttackEvent

router = APIRouter()


class InvestigationEvent(BaseModel):
    id: str
    event_type: str
    source_ip: str
    raw_log: str | None
    mitre_technique: str | None
    mitre_tactic: str | None
    threat_score: int
    timestamp: datetime
    simulated: bool
    username: str | None
    parsed_data: dict | None


class InvestigationOut(BaseModel):
    session_id: str
    source_ip: str
    events: list[InvestigationEvent]
    alert_ids: list[str]


@router.get("/{session_id}", response_model=InvestigationOut)
async def get_investigation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    events = (await db.execute(select(AttackEvent).where(AttackEvent.session_id == session_id).order_by(AttackEvent.timestamp))).scalars().all()
    if not events:
        raise HTTPException(status_code=404, detail="Investigation not found")
    event_ids = [event.id for event in events]
    alert_ids = [str(value) for value in (await db.execute(select(Alert.id).where(Alert.event_id.in_(event_ids)))).scalars().all()]
    return InvestigationOut(
        session_id=session_id,
        source_ip=events[0].source_ip,
        alert_ids=alert_ids,
        events=[InvestigationEvent(
            id=str(event.id), event_type=event.event_type.value, source_ip=event.source_ip,
            raw_log=event.raw_log, mitre_technique=event.mitre_technique,
            mitre_tactic=event.mitre_tactic, threat_score=event.threat_score,
            timestamp=event.timestamp, simulated=bool((event.parsed_data or {}).get("simulated")),
            username=event.username, parsed_data=event.parsed_data,
        ) for event in events],
    )
