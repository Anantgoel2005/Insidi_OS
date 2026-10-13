from __future__ import annotations

import logging

from app.agents.ttp_profiler import classify_ttp
from app.core.redis_client import redis, STREAMS
from app.models.event import AttackEvent, EventType
from app.services.insider import InsiderContext, assess_insider

logger = logging.getLogger(__name__)


async def enrich_event(event: AttackEvent, *, use_llm: bool = True) -> None:
    context = (event.parsed_data or {}).get("insider")
    if context is not None:
        # Validate before the best-effort stream block; invalid telemetry must fail.
        assess_insider(event, InsiderContext.model_validate(context))
    try:
        if context is None and event.event_type in (EventType.COMMAND, EventType.SHELL_SPAWN):
            ttp = await classify_ttp(
                command_line=event.raw_log or "",
                raw_log=event.raw_log or "",
                use_llm=use_llm,
            )
            event.mitre_technique = ttp.get("technique_id")
            event.mitre_tactic = ttp.get("tactic")

        if context is not None:
            pass  # Identity-aware scoring above replaces perimeter heuristics.
        elif event.event_type == EventType.EXPLOIT_ATTEMPT:
            event.threat_score = min(100, event.threat_score + 70)
        elif event.event_type == EventType.LOGIN_SUCCESS:
            event.threat_score = min(100, event.threat_score + 60)
        elif event.event_type in (EventType.COMMAND, EventType.SHELL_SPAWN):
            event.threat_score = min(100, event.threat_score + 45)
        elif event.event_type == EventType.LOGIN_ATTEMPT:
            event.threat_score = min(100, event.threat_score + 10)
        elif event.event_type == EventType.CANARY_TRIP:
            event.threat_score = min(100, event.threat_score + 90)

        await redis.xadd(
            STREAMS["events"],
            {
                "event_id": str(event.id),
                "event_type": event.event_type.value,
                "source_ip": event.source_ip,
                "mitre_technique": event.mitre_technique or "",
                "threat_score": str(event.threat_score),
                "timestamp": event.timestamp.isoformat() if event.timestamp else "",
            },
            maxlen=50000,
        )
    except Exception as exc:
        logger.error("Event enrichment failed for %s: %s", event.id, exc)
