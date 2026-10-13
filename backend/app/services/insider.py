"""Deterministic findings from trusted identity and access telemetry.

Metadata describes observed account activity, not a conclusion about a person.
The collector must derive scope, destination and change approval from policy.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import AttackEvent, EventType


class InsiderContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    actor_id: str = Field(min_length=1, max_length=128)
    role: Literal["employee", "administrator"]
    resource: str = Field(min_length=1, max_length=512)
    sensitive: bool = False
    outside_scope: bool = False
    honeytoken: bool = False
    records_accessed: int = Field(default=0, ge=0)
    bytes_transferred: int = Field(default=0, ge=0)
    destination: Literal["internal", "approved_external", "unapproved_external", "unknown"] = "unknown"
    admin_action: Literal["none", "privilege_change", "audit_disabled", "credential_export"] = "none"
    approved_change: bool = False


def assess_insider(event: AttackEvent, context: InsiderContext) -> dict:
    findings = []

    def add(rule: str, score: int, reason: str, technique: str, tactic: str):
        findings.append(dict(rule=rule, score=score, reason=reason, technique=technique, tactic=tactic))

    access = event.event_type in (EventType.FILE_DOWNLOAD, EventType.FILE_UPLOAD, EventType.COMMAND)
    if context.honeytoken and (access or event.event_type == EventType.CANARY_TRIP):
        add("honeytoken_access", 90, "Account interacted with a designated decoy resource.", "T1213", "Collection")
    if access and context.sensitive and context.outside_scope:
        add("out_of_scope_access", 70, "Sensitive resource access is outside the account's permitted scope.", "T1213", "Collection")
    if access and context.sensitive and (context.records_accessed >= 1000 or context.bytes_transferred >= 100_000_000):
        add("bulk_sensitive_access", 65, "Sensitive access reached 1,000 records or 100 MB in this event.", "T1213", "Collection")
    if event.event_type == EventType.FILE_UPLOAD and context.sensitive and context.destination == "unapproved_external":
        add("unapproved_transfer", 85, "Sensitive data was transferred to an unapproved external destination.", "T1048", "Exfiltration")
    if event.event_type == EventType.COMMAND and context.role == "administrator" and not context.approved_change:
        actions = {
            "audit_disabled": (85, "Audit logging was disabled without an approved change.", "T1562.001", "Defense Evasion"),
            "privilege_change": (70, "Account privileges changed without an approved change.", "T1098", "Persistence"),
            "credential_export": (85, "Credentials were exported without an approved change.", "T1003", "Credential Access"),
        }
        if context.admin_action in actions:
            add(context.admin_action, *actions[context.admin_action])

    strongest = max(findings, key=lambda finding: finding["score"], default=None)
    # A legitimate internal login alone is not evidence of insider misuse.
    baseline = {EventType.CANARY_TRIP: 90, EventType.EXPLOIT_ATTEMPT: 70}.get(event.event_type, 0)
    score = max(strongest["score"] if strongest else 0, baseline)
    event.threat_score = score
    event.mitre_technique = strongest["technique"] if strongest else None
    event.mitre_tactic = strongest["tactic"] if strongest else None
    assessment = {"score": score, "findings": findings, "policy_version": "insider-v1"}
    event.parsed_data = {**(event.parsed_data or {}), "insider": context.model_dump(), "insider_assessment": assessment}
    return assessment
