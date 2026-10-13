from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.event import AttackEvent

logger = logging.getLogger(__name__)

THRESHOLD_HIGH = 60
THRESHOLD_CRITICAL = 85


async def evaluate_event(db: AsyncSession, event: AttackEvent) -> Alert | None:
    if event.threat_score < THRESHOLD_HIGH:
        return None

    if event.threat_score >= THRESHOLD_CRITICAL:
        severity = AlertSeverity.CRITICAL
    else:
        severity = AlertSeverity.HIGH

    insider = (event.parsed_data or {}).get("insider")
    assessment = (event.parsed_data or {}).get("insider_assessment", {})
    title = f"{event.event_type.value.replace('_', ' ').title()} from {event.source_ip}"
    if insider:
        rules = ", ".join(finding["rule"] for finding in assessment.get("findings", [])) or event.event_type.value
        title = f"Insider activity: {insider['actor_id']} [{rules}]"
    if event.mitre_technique:
        title += f" [{event.mitre_technique}]"

    description = (
        f"Threat score: {event.threat_score}/100\n"
        f"Source IP: {event.source_ip}\n"
        f"MITRE technique: {event.mitre_technique or 'N/A'}\n"
        f"Raw log: {(event.raw_log or '')[:500]}"
    )
    if insider:
        description += "\nAccount: " + insider["actor_id"] + "\nResource: " + insider["resource"]
        description += "\n" + "\n".join(finding["reason"] for finding in assessment.get("findings", []))

    recommendation = _get_recommendation(event)

    # Do not turn a noisy decoy into hundreds of identical open alerts.
    recent = await db.scalar(
        select(Alert).where(
            Alert.title == title,
            Alert.status.in_([AlertStatus.NEW, AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING]),
            Alert.created_at >= datetime.now(timezone.utc) - timedelta(minutes=10),
        ).limit(1)
    )
    if recent:
        return recent

    alert = Alert(
        event_id=event.id,
        title=title,
        description=description,
        severity=severity,
        recommendation=recommendation,
        extra={
            "source_ip": event.source_ip,
            "event_type": event.event_type.value,
            "threat_score": event.threat_score,
            "mitre_technique": event.mitre_technique,
            "insider": insider,
            "insider_assessment": assessment if insider else None,
        },
    )
    db.add(alert)
    await db.flush()
    logger.info("Alert created: %s (severity=%s)", title, severity.value)

    return alert


def _get_recommendation(event: AttackEvent) -> str:
    if (event.parsed_data or {}).get("insider"):
        return (
            "Preserve identity, resource and destination audit evidence. Correlate this account across devices and sessions. "
            "Verify business purpose, approved changes and possible account compromise with the responsible owner. "
            "Treat this as a reviewable finding, not proof of malicious intent. Require analyst approval for containment."
        )
    if event.event_type.value == "canary_trip":
        return "CRITICAL: A canary token has been tripped. Investigate immediately. Rotate all credentials in the affected scope."
    if event.event_type.value == "exploit_attempt":
        return "Block source IP at perimeter firewall. Analyze exploit payload. Check for related vulnerabilities."
    if event.event_type.value == "login_success":
        return "Investigate successful login. Verify if credentials were legitimate. Review session activity."
    return "Review event in SIEM. Correlate with other activity from this source IP."
