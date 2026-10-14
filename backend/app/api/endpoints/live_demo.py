import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.config import settings
from app.models.demo_run import DemoRun
from app.services.demo_scenarios import scenario_steps
from app.services.live_demo import advance_run, initial_sandbox

router = APIRouter()


class StartRequest(BaseModel):
    scenario: Literal["employee-misuse", "administrator-misuse", "credential-to-exfiltration"] = "employee-misuse"
    interval_seconds: int = Field(default=4, ge=2, le=10)
    autoplay: bool = True


class ControlRequest(BaseModel):
    action: Literal["pause", "resume", "step", "stop", "speed"]
    expected_cursor: int = Field(ge=0)
    interval_seconds: int | None = Field(default=None, ge=2, le=10)


def serialize_run(run: DemoRun) -> dict:
    plan = scenario_steps(run.scenario)
    return {
        "session_id": run.session_id, "scenario": run.scenario, "status": run.status,
        "cursor": run.cursor, "total_steps": len(plan), "interval_seconds": run.interval_seconds,
        "plan": [{"title": step["title"], "narrative": step["narrative"]} for step in plan],
        "steps": run.steps, "sandbox": run.sandbox, "created_at": run.created_at,
        "next_step_at": run.next_step_at,
    }


def require_demo():
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")


async def get_run(db, session_id, *, lock=False):
    query = select(DemoRun).where(DemoRun.session_id == session_id)
    if lock:
        query = query.with_for_update()
    run = await db.scalar(query)
    if not run:
        raise HTTPException(status_code=404, detail="Live demo not found")
    return run


@router.post("", dependencies=[Depends(require_demo)])
async def start_live(payload: StartRequest, db: AsyncSession = Depends(get_db), _user: str = Depends(get_current_user)):
    # Serialize starts, including requests across multiple API workers.
    await db.execute(select(func.pg_advisory_xact_lock(941035)))
    count = await db.scalar(select(func.count()).select_from(DemoRun).where(DemoRun.status.in_(["running", "paused"])))
    if count >= 10:
        raise HTTPException(status_code=409, detail="Stop an existing demo before starting another (10 active runs maximum)")
    run = DemoRun(
        session_id=f"live-{uuid.uuid4().hex[:12]}", scenario=payload.scenario,
        status="running" if payload.autoplay else "paused", cursor=0,
        interval_seconds=payload.interval_seconds, next_step_at=datetime.now(timezone.utc),
        sandbox=initial_sandbox(), steps=[],
    )
    db.add(run)
    await db.flush()
    return serialize_run(run)


@router.get("/{session_id}", dependencies=[Depends(require_demo)])
async def read_live(session_id: str, db: AsyncSession = Depends(get_db), _user: str = Depends(get_current_user)):
    return serialize_run(await get_run(db, session_id))


@router.post("/{session_id}/control", dependencies=[Depends(require_demo)])
async def control_live(session_id: str, payload: ControlRequest, db: AsyncSession = Depends(get_db), _user: str = Depends(get_current_user)):
    run = await get_run(db, session_id, lock=True)
    if run.status in ("completed", "stopped"):
        return serialize_run(run)
    if payload.action == "step":
        if run.status != "paused":
            raise HTTPException(status_code=409, detail="Pause the demo before stepping")
        if payload.expected_cursor != run.cursor:
            # Retried requests return the committed result without adding an event.
            return serialize_run(run)
        await advance_run(db, run)
    elif payload.action == "pause":
        run.status = "paused"
    elif payload.action == "resume":
        run.status = "running"
        run.next_step_at = datetime.now(timezone.utc)
    elif payload.action == "stop":
        run.status = "stopped"
    elif payload.action == "speed":
        if payload.interval_seconds is None:
            raise HTTPException(status_code=422, detail="interval_seconds is required")
        run.interval_seconds = payload.interval_seconds
        run.next_step_at = datetime.now(timezone.utc) + timedelta(seconds=payload.interval_seconds)
    await db.flush()
    return serialize_run(run)
