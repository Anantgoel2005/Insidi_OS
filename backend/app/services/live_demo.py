"""Durable showcase scheduler and a bounded synthetic response environment."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy import select

from app.config import settings
from app.core.database import async_session_factory
from app.models.demo_run import DemoRun
from app.models.event import AttackEvent, EventType
from app.services.demo_scenarios import scenario_steps
from app.services.event_processor import process_event

logger = logging.getLogger(__name__)


def initial_sandbox() -> dict:
    return {"account_contained": False, "egress_blocked": False, "audit_enabled": True, "privileges_locked": False, "decoy_isolated": False, "blocked_attempts": 0}


def apply_response(sandbox: dict, event: AttackEvent) -> tuple[dict, list[dict], str]:
    """Mutate only the demo's JSON state, never an OS, account, file or firewall."""
    state = dict(sandbox)
    actions = []
    context = (event.parsed_data or {}).get("insider", {})
    rules = {finding["rule"] for finding in (event.parsed_data or {}).get("insider_assessment", {}).get("findings", [])}
    outcome = "Observed"

    def action(code, title, detail):
        actions.append({"code": code, "title": title, "detail": detail, "scope": "synthetic_sandbox"})

    if state["account_contained"] and event.event_type != EventType.SESSION_CLOSE:
        state["blocked_attempts"] += 1
        outcome = "Denied by existing containment"
        action("deny_retry", "Contained account denied", "Persisted sandbox containment denied the next synthetic action.")
    elif "unapproved_transfer" in rules:
        state.update(egress_blocked=True, account_contained=True)
        state["blocked_attempts"] += 1
        outcome = "Transfer blocked in sandbox"
        action("block_egress", "External transfer blocked", f"The sandbox rejected {context.get('bytes_transferred', 0):,} synthetic bytes to an unapproved destination.")
        action("contain_account", "Synthetic account contained", "Subsequent actions from this demo account will be denied inside this run.")
    elif "credential_export" in rules:
        state.update(account_contained=True, egress_blocked=True)
        outcome = "Decoy export contained"
        action("contain_account", "Synthetic account contained", "The sandbox contained the account following unapproved credential export.")
    if "honeytoken_access" in rules:
        state["decoy_isolated"] = True
        action("isolate_decoy", "Decoy interaction isolated", "Only synthetic decoy content is available in this scenario; no real data is served.")
    if "audit_disabled" in rules:
        state["audit_enabled"] = True
        outcome = "Audit logging restored in sandbox"
        action("restore_audit", "Audit logging restored", "The synthetic audit control is enabled after the disabling attempt.")
    if "privilege_change" in rules:
        state["privileges_locked"] = True
        outcome = "Privilege change denied in sandbox"
        action("deny_privilege", "Privilege escalation denied", "The synthetic access policy rejected the unapproved privilege change.")
    if "bulk_sensitive_access" in rules:
        action("review_export", "Bulk export flagged for review", "The real detection finding and event are retained for the analyst.")
    if event.event_type == EventType.SESSION_CLOSE:
        outcome = "Evidence ready for review"
        action("case_ready", "Investigation ready", "The recorded events, findings and sandbox response history are ready for analyst review.")
    if not actions:
        action("observe", "Monitoring continues", "No sandbox containment action is needed for this step." if event.threat_score < 60 else "The event meets the alert threshold. Review the finding in the analyst console.")
    return state, actions, outcome


async def advance_run(db, run: DemoRun) -> None:
    steps = scenario_steps(run.scenario)
    if run.cursor >= len(steps) or run.status in ("completed", "stopped"):
        return
    step = steps[run.cursor]
    started = perf_counter()
    timestamp = datetime.now(timezone.utc)
    context = step["context"]
    event = AttackEvent(
        event_type=step["event_type"], source_ip="198.51.100.42", source_port=49152,
        username=context["actor_id"] if context else "deploy", raw_log=step["raw_log"],
        parsed_data={"source": "demo_scenario", "simulated": True, "live_demo": True, "scenario": run.scenario, **({"insider": context} if context else {})},
        session_id=run.session_id, threat_score=0, timestamp=timestamp,
    )
    db.add(event)
    await db.flush()
    alert = await process_event(db, event, use_llm=False)
    attack_state = dict(run.sandbox)
    if context and context.get("admin_action") == "audit_disabled" and not attack_state["account_contained"]:
        attack_state["audit_enabled"] = False
    sandbox, actions, outcome = apply_response(attack_state, event)
    response_at = datetime.now(timezone.utc)
    record = {
        "index": run.cursor, "title": step["title"], "narrative": step["narrative"],
        "event_id": str(event.id), "event_type": event.event_type.value,
        "raw_log": event.raw_log, "actor_id": event.username, "timestamp": timestamp.isoformat(),
        "score": event.threat_score, "mitre_technique": event.mitre_technique, "mitre_tactic": event.mitre_tactic,
        "findings": (event.parsed_data or {}).get("insider_assessment", {}).get("findings", []),
        "alert": {"id": str(alert.id), "title": alert.title, "severity": alert.severity.value, "recommendation": alert.recommendation} if alert else None,
        "responses": actions, "outcome": outcome, "response_at": response_at.isoformat(),
        "processing_ms": round((perf_counter() - started) * 1000, 1), "sandbox": sandbox,
        "sandbox_before": run.sandbox, "sandbox_after_attack": attack_state,
    }
    run.steps = [*run.steps, record]
    run.sandbox = sandbox
    run.cursor += 1
    run.next_step_at = response_at + timedelta(seconds=run.interval_seconds)
    if run.cursor == len(steps):
        run.status = "completed"


async def scheduler_tick() -> None:
    if not settings.demo_mode:
        return
    async with async_session_factory() as db:
        async with db.begin():
            runs = (await db.execute(
                select(DemoRun).where(DemoRun.status == "running", DemoRun.next_step_at <= datetime.now(timezone.utc))
                .order_by(DemoRun.next_step_at).limit(10).with_for_update(skip_locked=True)
            )).scalars().all()
            for run in runs:
                await advance_run(db, run)


async def run_scheduler() -> None:
    while True:
        try:
            await scheduler_tick()
        except Exception:
            logger.exception("Live demo tick failed; transaction rolled back")
        await asyncio.sleep(0.5)
