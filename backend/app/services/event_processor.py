from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.honeypot import Honeypot
from app.models.event import AttackEvent, EventType
from app.models.alert import Alert
from app.services.alert_engine import evaluate_event
from app.services.event_ingestor import enrich_event


async def process_event(db: AsyncSession, event: AttackEvent, *, use_llm: bool = True) -> Alert | None:
    """Run the event pipeline, with optional external enrichment."""
    await enrich_event(event, use_llm=use_llm)
    if event.honeypot_id:
        honeypot = await db.scalar(select(Honeypot).where(Honeypot.id == event.honeypot_id))
        if honeypot:
            honeypot.total_connections += 1 if event.event_type.value == "connection" else 0
            honeypot.total_commands += 1 if event.event_type.value == "command" else 0
            if event.event_type.value == "connection":
                honeypot.unique_attackers = await db.scalar(select(func.count(func.distinct(AttackEvent.source_ip))).where(
                    AttackEvent.honeypot_id == event.honeypot_id,
                    AttackEvent.event_type == EventType.CONNECTION, AttackEvent.source_ip.notin_(["0.0.0.0", "unknown"]),
                )) or 0
    return await evaluate_event(db, event)
