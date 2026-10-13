from unittest.mock import AsyncMock
import uuid

import pytest
from pydantic import ValidationError

from app.api.endpoints.demo import DemoRunRequest, insider_sequence, run_demo
from app.api.endpoints.events import IngestEventRequest
from app.models.event import AttackEvent, EventType
from app.services.insider import InsiderContext, assess_insider
from app.services import alert_engine, event_ingestor


def context(**overrides):
    return InsiderContext.model_validate({"actor_id": "account-001", "role": "employee", "resource": "finance/export", **overrides})


def event(kind=EventType.LOGIN_SUCCESS, **overrides):
    return AttackEvent(id=uuid.uuid4(), event_type=kind, source_ip="192.0.2.1", threat_score=0, **overrides)


@pytest.mark.parametrize("kind,metadata,score,rule", [
    (EventType.LOGIN_SUCCESS, {}, 0, None),
    (EventType.FILE_DOWNLOAD, {"sensitive": True}, 0, None),
    (EventType.FILE_DOWNLOAD, {"outside_scope": True}, 0, None),
    (EventType.FILE_DOWNLOAD, {"sensitive": True, "outside_scope": True}, 70, "out_of_scope_access"),
    (EventType.FILE_DOWNLOAD, {"honeytoken": True}, 90, "honeytoken_access"),
    (EventType.FILE_DOWNLOAD, {"sensitive": True, "records_accessed": 999}, 0, None),
    (EventType.FILE_DOWNLOAD, {"sensitive": True, "records_accessed": 1000}, 65, "bulk_sensitive_access"),
    (EventType.FILE_DOWNLOAD, {"sensitive": True, "bytes_transferred": 100_000_000}, 65, "bulk_sensitive_access"),
    (EventType.FILE_UPLOAD, {"sensitive": True, "destination": "unapproved_external"}, 85, "unapproved_transfer"),
    (EventType.FILE_UPLOAD, {"sensitive": True, "destination": "approved_external"}, 0, None),
    (EventType.COMMAND, {"role": "administrator", "admin_action": "audit_disabled"}, 85, "audit_disabled"),
    (EventType.COMMAND, {"role": "administrator", "admin_action": "privilege_change"}, 70, "privilege_change"),
    (EventType.COMMAND, {"role": "administrator", "admin_action": "credential_export"}, 85, "credential_export"),
    (EventType.COMMAND, {"role": "administrator", "admin_action": "privilege_change", "approved_change": True}, 0, None),
    (EventType.CANARY_TRIP, {}, 90, None),
    (EventType.EXPLOIT_ATTEMPT, {}, 70, None),
])
def test_policy(kind, metadata, score, rule):
    observed = event(kind)
    result = assess_insider(observed, context(**metadata))
    assert observed.threat_score == result["score"] == score
    assert [finding["rule"] for finding in result["findings"]] == ([rule] if rule else [])
    assert observed.parsed_data["insider"]["actor_id"] == "account-001"


def test_approved_change_cannot_suppress_decoy_or_data_findings():
    observed = event(EventType.COMMAND)
    result = assess_insider(observed, context(role="administrator", approved_change=True, honeytoken=True, sensitive=True, outside_scope=True))
    assert result["score"] == 90
    assert len(result["findings"]) == 2
    assert observed.mitre_technique


@pytest.mark.parametrize("metadata", [{"actor_id": " "}, {"records_accessed": -1}, {"honeytoken": "false"}, {"role": "unknown"}, {"extra": True}])
def test_invalid_telemetry_rejected(metadata):
    with pytest.raises(ValidationError):
        context(**metadata)


def test_ingest_accepts_typed_context_and_discards_forged_assessment():
    payload = IngestEventRequest(event_type="login_success", source_ip="192.0.2.1", insider=context(), parsed_data={"insider_assessment": {"score": 100}})
    assert payload.parsed_data == {"insider": context().model_dump()}
    with pytest.raises(ValidationError):
        IngestEventRequest(event_type="command", source_ip="192.0.2.1", parsed_data={"insider": {"actor_id": "missing-fields"}})
    with pytest.raises(ValidationError):
        IngestEventRequest(event_type="command", source_ip="192.0.2.1", insider=context(), parsed_data={"insider": context().model_dump()})


@pytest.mark.asyncio
async def test_insider_enrichment_is_offline_and_survives_redis_failure(monkeypatch):
    observed = event(EventType.COMMAND, parsed_data={"insider": context(role="administrator", admin_action="audit_disabled").model_dump()})
    classify = AsyncMock(side_effect=AssertionError("Insider metadata must not reach the LLM"))
    monkeypatch.setattr(event_ingestor, "classify_ttp", classify)
    monkeypatch.setattr(event_ingestor.redis, "xadd", AsyncMock(side_effect=ConnectionError("offline")))
    await event_ingestor.enrich_event(observed)
    assert observed.threat_score == 85
    classify.assert_not_called()


@pytest.mark.asyncio
async def test_legacy_decoy_login_scoring_unchanged(monkeypatch):
    monkeypatch.setattr(event_ingestor.redis, "xadd", AsyncMock())
    observed = event()
    await event_ingestor.enrich_event(observed, use_llm=False)
    assert observed.threat_score == 60


@pytest.mark.asyncio
async def test_alert_titles_separate_accounts_on_shared_ip():
    titles = []
    for account in ["account-001", "account-002"]:
        db = AsyncMock()
        db.scalar.return_value = None
        db.add = lambda alert: titles.append(alert.title)
        observed = event(EventType.FILE_DOWNLOAD)
        assess_insider(observed, context(actor_id=account, honeytoken=True))
        alert = await alert_engine.evaluate_event(db, observed)
        assert alert.extra["insider"]["actor_id"] == account
        assert "analyst approval" in alert.recommendation
    assert titles[0] != titles[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,scores", [("employee-misuse", [0, 90, 65, 85]), ("administrator-misuse", [0, 0, 85, 70, 90])])
async def test_demo_uses_real_pipeline_without_services(monkeypatch, scenario, scores):
    from app.config import settings
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(event_ingestor.redis, "xadd", AsyncMock())
    db = AsyncMock()
    db.scalar.return_value = None
    added = []
    db.add = added.append
    result = await run_demo(DemoRunRequest(scenario=scenario), db, "admin")
    events = [item for item in added if isinstance(item, AttackEvent)]
    assert [item.threat_score for item in events] == scores
    assert result.events_created == len(insider_sequence(scenario))
    assert all(item.parsed_data["simulated"] for item in events)
    assert all(item.session_id == result.session_id for item in events)


@pytest.mark.asyncio
async def test_account_filter_applies_to_count_and_items_queries():
    from sqlalchemy.dialects import postgresql
    from unittest.mock import MagicMock
    from app.api.endpoints.events import list_events

    db = AsyncMock()
    count = MagicMock()
    count.scalar.return_value = 0
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = []
    db.execute.side_effect = [count, rows]
    result = await list_events(skip=0, limit=100, actor_id="account-001", db=db, _user="admin")
    assert result.total == 0
    for call in db.execute.await_args_list:
        query = call.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        assert "actor_id" in str(query)
        assert "account-001" in str(query)


@pytest.mark.asyncio
async def test_investigation_includes_identity_and_findings():
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from app.api.endpoints.investigations import get_investigation

    observed = event(EventType.FILE_DOWNLOAD, timestamp=datetime.now(timezone.utc))
    assess_insider(observed, context(honeytoken=True))
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = [observed]
    alerts = MagicMock()
    alerts.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute.side_effect = [rows, alerts]
    result = await get_investigation("collector-session", db, "admin")
    evidence = result.events[0].parsed_data
    assert evidence["insider"]["actor_id"] == "account-001"
    assert evidence["insider_assessment"]["findings"][0]["rule"] == "honeytoken_access"
