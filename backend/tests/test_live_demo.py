import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.endpoints import live_demo as endpoints
from app.models.demo_run import DemoRun
from app.services import event_ingestor, live_demo


def run(scenario="employee-misuse", status="paused"):
    return DemoRun(session_id="live-test", scenario=scenario, status=status, cursor=0, interval_seconds=4,
                   next_step_at=datetime.now(timezone.utc), sandbox=live_demo.initial_sandbox(), steps=[])


def database():
    db = AsyncMock()
    db.scalar.return_value = None
    added = []
    db.add = added.append

    async def flush():
        for item in added:
            if hasattr(item, "id") and item.id is None:
                item.id = uuid.uuid4()

    db.flush.side_effect = flush
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario,scores", [("employee-misuse", [0, 90, 65, 85, 85, 0]), ("administrator-misuse", [0, 0, 85, 70, 90, 85, 0])])
async def test_timed_run_records_actual_pipeline_and_contains_synthetic_retries(monkeypatch, scenario, scores):
    monkeypatch.setattr(event_ingestor.redis, "xadd", AsyncMock())
    session = run(scenario)
    db = database()
    for index in range(len(scores)):
        await live_demo.advance_run(db, session)
        assert session.cursor == index + 1
        assert len(session.steps) == index + 1
        assert session.steps[-1]["score"] == scores[index]
        assert bool(session.steps[-1]["alert"]) == (scores[index] >= 60)
    assert session.status == "completed"
    assert session.sandbox["account_contained"]
    assert session.steps[-2]["outcome"] == "Denied by existing containment"
    assert all(action["scope"] == "synthetic_sandbox" for step in session.steps for action in step["responses"])
    assert all(step["event_id"] for step in session.steps)
    if scenario == "administrator-misuse":
        assert session.steps[2]["sandbox_after_attack"]["audit_enabled"] is False
        assert session.steps[2]["sandbox"]["audit_enabled"] is True
    before = session.cursor
    await live_demo.advance_run(db, session)
    assert session.cursor == before


@pytest.mark.asyncio
async def test_failed_processing_does_not_advance_run(monkeypatch):
    monkeypatch.setattr(live_demo, "process_event", AsyncMock(side_effect=RuntimeError("pipeline failed")))
    session = run()
    with pytest.raises(RuntimeError):
        await live_demo.advance_run(database(), session)
    assert session.cursor == 0
    assert session.steps == []


@pytest.mark.asyncio
async def test_manual_step_retry_is_idempotent(monkeypatch):
    session = run()
    session.cursor = 1
    monkeypatch.setattr(endpoints, "get_run", AsyncMock(return_value=session))
    advance = AsyncMock()
    monkeypatch.setattr(endpoints, "advance_run", advance)
    result = await endpoints.control_live("live-test", endpoints.ControlRequest(action="step", expected_cursor=0), database(), "admin")
    assert result["cursor"] == 1
    advance.assert_not_called()


@pytest.mark.asyncio
async def test_running_demo_must_pause_before_manual_step(monkeypatch):
    monkeypatch.setattr(endpoints, "get_run", AsyncMock(return_value=run(status="running")))
    with pytest.raises(HTTPException) as error:
        await endpoints.control_live("live-test", endpoints.ControlRequest(action="step", expected_cursor=0), database(), "admin")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_stopped_run_cannot_resume(monkeypatch):
    session = run(status="stopped")
    monkeypatch.setattr(endpoints, "get_run", AsyncMock(return_value=session))
    result = await endpoints.control_live("live-test", endpoints.ControlRequest(action="resume", expected_cursor=0), database(), "admin")
    assert result["status"] == "stopped"


def test_demo_disabled_and_invalid_speed_rejected(monkeypatch):
    monkeypatch.setattr(endpoints.settings, "demo_mode", False)
    with pytest.raises(HTTPException) as error:
        endpoints.require_demo()
    assert error.value.status_code == 403
    with pytest.raises(ValidationError):
        endpoints.StartRequest(interval_seconds=0)
    with pytest.raises(ValidationError):
        endpoints.ControlRequest(action="step", expected_cursor=-1)


@pytest.mark.asyncio
async def test_scheduler_claims_only_due_running_rows_with_skip_locked(monkeypatch):
    from sqlalchemy.dialects import postgresql
    monkeypatch.setattr(live_demo.settings, "demo_mode", True)
    db = AsyncMock()
    db.begin = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
    rows = MagicMock()
    rows.scalars.return_value.all.return_value = []
    db.execute.return_value = rows
    context = MagicMock(__aenter__=AsyncMock(return_value=db), __aexit__=AsyncMock())
    monkeypatch.setattr(live_demo, "async_session_factory", lambda: context)
    await live_demo.scheduler_tick()
    query = str(db.execute.await_args.args[0].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "FOR UPDATE SKIP LOCKED" in query
    assert "demo_runs.status = 'running'" in query
    assert "demo_runs.next_step_at <=" in query
