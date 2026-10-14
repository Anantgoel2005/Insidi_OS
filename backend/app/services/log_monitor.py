from __future__ import annotations

import asyncio
import logging
import re
import hashlib
import ipaddress
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.docker_client import get_docker
from app.models.event import AttackEvent, EventType
from app.models.canary import CanaryToken  # noqa: F401 - register metadata for worker-only imports
from app.models.honeypot import Honeypot, HoneypotStatus

logger = logging.getLogger(__name__)

SSH_PATTERNS = [
    (re.compile(r"Accepted \w+ for (?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"), EventType.LOGIN_SUCCESS),
    (re.compile(r"Failed \w+ for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+) port (?P<port>\d+)"), EventType.LOGIN_ATTEMPT),
    (re.compile(r"Connection (?:closed|reset) by (?:(?:authenticating user|invalid user) \S+ )?(?P<ip>\S+) port (?P<port>\d+)"), EventType.SESSION_CLOSE),
    (re.compile(r"Disconnected from (?:user |invalid user )?(?P<user>\S+) (?P<ip>\S+) port (?P<port>\d+)"), EventType.SESSION_CLOSE),
    (re.compile(r"Connection from (?P<ip>\S+) port (?P<port>\d+)"), EventType.CONNECTION),
]


def parse_ssh_log(line: str) -> dict | None:
    for pattern, event_type in SSH_PATTERNS:
        match = pattern.search(_strip_timestamp(line))
        if not match:
            continue
        try:
            source_ip = str(ipaddress.ip_address(match["ip"]))
            port = int(match["port"])
            if not 0 < port <= 65535:
                return None
        except ValueError:
            return None
        return {"event_type": event_type, "source_ip": source_ip, "source_port": port, "username": match.groupdict().get("user")}
    # Startup and diagnostic messages are not executed shell commands.
    return None


def log_fingerprint(container_id: str, line: str) -> str:
    return hashlib.sha256(f"{container_id}:{line.strip()}".encode()).hexdigest()


def _log_timestamp(line: str) -> datetime | None:
    try:
        return datetime.fromisoformat(line.split(maxsplit=1)[0].replace("Z", "+00:00"))
    except (ValueError, IndexError):
        return None


async def monitor_honeypot_logs() -> None:
    try:
        docker_client = get_docker()
    except RuntimeError:
        logger.warning("Docker unavailable — log monitor disabled")
        return

    logger.info("Honeypot log monitor started")
    tracked: dict[str, str] = {}
    cursors: dict[str, datetime] = {}

    while True:
        try:
            async with async_session_factory() as session:
                cursor_updates = {}
                result = await session.execute(
                    select(Honeypot.container_id, Honeypot.id).where(
                        Honeypot.status == HoneypotStatus.RUNNING,
                        Honeypot.container_id.is_not(None),
                    ).order_by(Honeypot.id)
                )
                for row in result.all():
                    container_id = str(row[0])
                    honeypot_id = str(row[1])

                    if container_id not in tracked:
                        tracked[container_id] = honeypot_id
                        logger.info("Now tracking honeypot %s (container %s)", honeypot_id, container_id[:12])

                    try:
                        container = docker_client.containers.get(container_id)
                        options = {"timestamps": True}
                        if container_id in cursors:
                            options["since"] = cursors[container_id] - timedelta(seconds=1)
                        else:
                            options["tail"] = 2000
                        logs = container.logs(**options).decode("utf-8", errors="replace")

                        for line in logs.strip().split("\n"):
                            if not line.strip():
                                continue
                            await _process_log_line(session, honeypot_id, line, container_id)
                        timestamps = [value for line in logs.splitlines() if (value := _log_timestamp(line))]
                        if timestamps:
                            cursor_updates[container_id] = max(timestamps)
                    except Exception as exc:
                        logger.warning("Failed to process logs for %s: %s", container_id[:12], exc)

                await session.commit()
                cursors.update(cursor_updates)
        except Exception as exc:
            logger.debug("Log monitor cycle error: %s", exc)

        await asyncio.sleep(2)


async def _process_log_line(session, honeypot_id: str, line: str, container_id: str) -> None:
    parsed = parse_ssh_log(line)
    if not parsed:
        return
    hp_id = uuid.UUID(honeypot_id)
    fingerprint = log_fingerprint(container_id, line)
    seen = select(AttackEvent.id).where(AttackEvent.honeypot_id == hp_id, AttackEvent.parsed_data["log_fingerprint"].astext == fingerprint).limit(1)
    if await session.scalar(seen):
        return
    # Serialize session creation/counts, including across multiple log workers.
    honeypot = await session.scalar(select(Honeypot).where(Honeypot.id == hp_id).with_for_update())
    if not honeypot or await session.scalar(seen):
        return
    previous = await session.scalar(select(AttackEvent).where(
        AttackEvent.honeypot_id == hp_id, AttackEvent.source_ip == parsed["source_ip"],
        AttackEvent.source_port == parsed["source_port"], AttackEvent.session_id.is_not(None),
    ).order_by(AttackEvent.timestamp.desc(), (AttackEvent.event_type == EventType.SESSION_CLOSE).desc()).limit(1))
    new_connection = previous is None or (previous.event_type == EventType.SESSION_CLOSE and parsed["event_type"] != EventType.SESSION_CLOSE)
    session_id = f"decoy-{uuid.uuid4().hex}" if new_connection else previous.session_id
    timestamp = _log_timestamp(line) or datetime.now(timezone.utc)
    from app.services.event_processor import process_event

    async def append(event_type, *, inferred=False):
        event = AttackEvent(
            honeypot_id=hp_id, event_type=event_type, source_ip=parsed["source_ip"],
            source_port=parsed["source_port"], username=parsed["username"], session_id=session_id,
            timestamp=timestamp, threat_score=0, raw_log=_strip_timestamp(line)[:2000],
            parsed_data={"container_id": container_id, "log_fingerprint": fingerprint + (":connection" if inferred else ""), "inferred_connection": inferred},
        )
        session.add(event)
        await session.flush()
        await process_event(session, event, use_llm=False)

    # sshd INFO logs may start at authentication; infer one connection for
    # that endpoint rather than counting every password attempt as a new one.
    if new_connection and parsed["event_type"] != EventType.CONNECTION:
        await append(EventType.CONNECTION, inferred=True)
    await append(parsed["event_type"])


def _strip_timestamp(line: str) -> str:
    ts_match = re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[.\d+Z]*\s+", line)
    if ts_match:
        return line[ts_match.end():].strip()
    return line.strip()
