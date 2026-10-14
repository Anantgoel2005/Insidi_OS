from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.honeypot import Honeypot, HoneypotStatus, HoneypotType
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class HoneypotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    honeypot_type: HoneypotType
    ports: str | None = None
    config_override: str | None = None


class HoneypotUpdate(BaseModel):
    name: str | None = None
    status: HoneypotStatus | None = None
    config_override: str | None = None


class HoneypotOut(BaseModel):
    id: uuid.UUID
    name: str
    honeypot_type: HoneypotType
    status: HoneypotStatus
    container_id: str | None
    ip_address: str | None
    ports: str | None
    total_connections: int
    total_commands: int
    unique_attackers: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HoneypotListOut(BaseModel):
    items: list[HoneypotOut]
    total: int


@router.get("", response_model=HoneypotListOut)
async def list_honeypots(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: HoneypotStatus | None = None,
    honeypot_type: HoneypotType | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    conditions = []
    if status:
        conditions.append(Honeypot.status == status)
    if honeypot_type:
        conditions.append(Honeypot.honeypot_type == honeypot_type)

    total_q = select(func.count(Honeypot.id))
    items_q = select(Honeypot).order_by(Honeypot.created_at.desc())
    if conditions:
        total_q = total_q.where(*conditions)
        items_q = items_q.where(*conditions)

    total_result = await db.execute(total_q)
    total = total_result.scalar() or 0

    items_result = await db.execute(items_q.offset(skip).limit(limit))
    items = items_result.scalars().all()

    return HoneypotListOut(
        items=[HoneypotOut.model_validate(h) for h in items],
        total=total,
    )


@router.post("", response_model=HoneypotOut, status_code=status.HTTP_201_CREATED)
async def create_honeypot(
    payload: HoneypotCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    if not settings.enable_local_decoys:
        raise HTTPException(status_code=403, detail="Local decoy deployment is disabled for this control plane")
    honeypot = Honeypot(
        name=payload.name,
        honeypot_type=payload.honeypot_type,
        ports=payload.ports,
        config_override=payload.config_override,
    )
    db.add(honeypot)
    await db.flush()
    honeypot_id = honeypot.id

    await db.commit()
    background_tasks.add_task(_deploy_honeypot_background, honeypot_id)

    await db.refresh(honeypot)
    return HoneypotOut.model_validate(honeypot)


def _deploy_honeypot_background(honeypot_id: uuid.UUID) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.honeypots.manager import HoneypotManager

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    try:
        with Session(engine) as session:
            manager = HoneypotManager()
            manager.deploy(session, honeypot_id)
            session.commit()
        logger.info("Honeypot %s deployed successfully", honeypot_id)
    except Exception as exc:
        logger.error("Failed to deploy honeypot %s: %s", honeypot_id, exc)
        # Deployment exceptions roll back the manager's transaction. Persist
        # the failure separately so the console does not remain "deploying".
        with Session(engine) as session:
            failed = session.get(Honeypot, honeypot_id)
            if failed:
                failed.status = HoneypotStatus.ERROR
                session.commit()
    finally:
        engine.dispose()


@router.get("/{honeypot_id}", response_model=HoneypotOut)
async def get_honeypot(
    honeypot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    result = await db.execute(select(Honeypot).where(Honeypot.id == honeypot_id))
    honeypot = result.scalar_one_or_none()
    if not honeypot:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    return HoneypotOut.model_validate(honeypot)


@router.patch("/{honeypot_id}", response_model=HoneypotOut)
async def update_honeypot(
    honeypot_id: uuid.UUID,
    payload: HoneypotUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    result = await db.execute(select(Honeypot).where(Honeypot.id == honeypot_id))
    honeypot = result.scalar_one_or_none()
    if not honeypot:
        raise HTTPException(status_code=404, detail="Honeypot not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(honeypot, field, value)

    await db.flush()
    await db.refresh(honeypot)
    return HoneypotOut.model_validate(honeypot)


@router.delete("/{honeypot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_honeypot(
    honeypot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    result = await db.execute(select(Honeypot).where(Honeypot.id == honeypot_id))
    honeypot = result.scalar_one_or_none()
    if not honeypot:
        raise HTTPException(status_code=404, detail="Honeypot not found")
    await db.delete(honeypot)
