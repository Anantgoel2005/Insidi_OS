from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from app.models.event import EventType
from app.models.honeypot import HoneypotStatus, HoneypotType
from app.services import decoy_connections, event_processor, log_monitor


@pytest.mark.parametrize("line,kind,user,ip,port", [
    ("Accepted password for root from 172.28.0.1 port 51042 ssh2", EventType.LOGIN_SUCCESS, "root", "172.28.0.1", 51042),
    ("Failed password for invalid user alice from 192.0.2.1 port 51234 ssh2", EventType.LOGIN_ATTEMPT, "alice", "192.0.2.1", 51234),
    ("Connection from 2001:db8::1 port 51234 on :: port 22", EventType.CONNECTION, None, "2001:db8::1", 51234),
    ("Disconnected from user root 172.28.0.1 port 51042", EventType.SESSION_CLOSE, "root", "172.28.0.1", 51042),
    ("Connection closed by authenticating user root 192.0.2.1 port 51234 [preauth]", EventType.SESSION_CLOSE, None, "192.0.2.1", 51234),
    ("Connection closed by 192.0.2.1 port 51234", EventType.SESSION_CLOSE, None, "192.0.2.1", 51234),
])
def test_parse_ssh_endpoint_and_lifecycle(line, kind, user, ip, port):
    result = log_monitor.parse_ssh_log(line)
    assert result == {"event_type": kind, "username": user, "source_ip": ip, "source_port": port}


@pytest.mark.parametrize("line", ["Server listening on 0.0.0.0 port 22.", "Received disconnect from 192.0.2.1 port 51234:11: disconnected by user", "Accepted password for root from invalid-ip port 5", "Connection from 192.0.2.1 port 99999"])
def test_diagnostic_or_invalid_lines_are_not_commands(line):
    assert log_monitor.parse_ssh_log(line) is None


def test_fingerprints_are_stable_across_line_endings_but_preserve_distinct_attempts():
    line = "2026-10-14T06:40:00.123456789Z Failed password for root from 192.0.2.1 port 51234"
    assert log_monitor.log_fingerprint("container", line) == log_monitor.log_fingerprint("container", line + "\r\n")
    assert log_monitor.log_fingerprint("container", line) != log_monitor.log_fingerprint("container", line.replace("789Z", "790Z"))


def test_live_count_excludes_listeners_closed_and_outbound_sockets():
    tables = """sl local_address rem_address st
0: 00000000:0016 00000000:0000 0A
1: 0100007F:0016 0100007F:C001 01
2: 0100007F:C002 0100007F:0016 01
3: 0100007F:0016 0100007F:C003 06
4: 00000000000000000000000000000000:0016 00000000000000000000000000000001:C004 01
5: 0100007F:0050 0100007F:C005 01
"""
    assert decoy_connections.count_established(tables, {22}) == 2
    assert decoy_connections.count_established(tables, {80}) == 1


@pytest.mark.asyncio
async def test_unavailable_monitor_is_not_zero_connected_clients(monkeypatch):
    monkeypatch.setattr(decoy_connections.settings, "enable_local_decoys", True)
    hp = SimpleNamespace(status=HoneypotStatus.RUNNING, container_id="test", honeypot_type=HoneypotType.SSH)
    def unavailable(*args):
        raise RuntimeError("Docker unavailable")
    monkeypatch.setattr(decoy_connections, "_read_count", unavailable)
    assert await decoy_connections.connection_snapshot(hp) == (None, "unavailable")
    monkeypatch.setattr(decoy_connections, "_read_count", lambda *args: 0)
    assert await decoy_connections.connection_snapshot(hp) == (0, "live")


@pytest.mark.asyncio
@pytest.mark.parametrize("previous_kind,inferred", [(None, True), (EventType.LOGIN_ATTEMPT, False), (EventType.SESSION_CLOSE, True)])
async def test_authentication_infers_only_one_connection_per_session(monkeypatch, previous_kind, inferred):
    db = AsyncMock()
    previous = SimpleNamespace(event_type=previous_kind, session_id="existing-session") if previous_kind else None
    db.scalar.side_effect = [None, SimpleNamespace(), None, previous]
    added = []
    db.add = added.append
    process = AsyncMock()
    monkeypatch.setattr(event_processor, "process_event", process)
    await log_monitor._process_log_line(db, str(uuid.uuid4()), "2026-10-14T06:40:00.123456789Z Accepted password for root from 192.0.2.1 port 51234 ssh2\r", "container")
    assert [event.event_type for event in added] == ([EventType.CONNECTION] if inferred else []) + [EventType.LOGIN_SUCCESS]
    assert len({event.session_id for event in added}) == 1
    assert added[-1].source_port == 51234
    assert added[-1].username == "root"
    assert added[-1].timestamp.year == 2026
    if not inferred:
        assert added[-1].session_id == "existing-session"


@pytest.mark.asyncio
async def test_committed_fingerprint_prevents_reingestion(monkeypatch):
    db = AsyncMock()
    db.scalar.return_value = uuid.uuid4()
    process = AsyncMock()
    monkeypatch.setattr(event_processor, "process_event", process)
    await log_monitor._process_log_line(db, str(uuid.uuid4()), "Accepted password for root from 192.0.2.1 port 51234 ssh2", "container")
    db.flush.assert_not_called()
    process.assert_not_called()
