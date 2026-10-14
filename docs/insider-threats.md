# Insider-threat telemetry

The control plane supports employee data misuse and privileged administrator misuse using explicit identity and access metadata. Existing decoy telemetry remains supported. The rules generate reviewable findings about account activity; they do not determine a person's intent or automatically contain an account.

Choose **Employee data misuse** or **Administrator abuse** in Live Showcase and start the live demo. Both scenarios use synthetic accounts and resources, documentation-only IP addresses, and the real scoring and alert pipeline without external AI. Ordinary internal logins and approved privilege updates have score zero.

## Collector contract

Send events to the existing authenticated `POST /api/v1/events/ingest` route with an `insider` object. Browser session requests require the existing CSRF token. This is a lab ingestion interface, not a new production collector authentication scheme.

```json
{
  "event_type": "file_upload",
  "source_ip": "192.0.2.10",
  "username": "synthetic-user",
  "session_id": "collector-session-001",
  "insider": {
    "actor_id": "directory-account-001",
    "role": "employee",
    "resource": "finance/quarterly-export.csv",
    "sensitive": true,
    "destination": "unapproved_external",
    "bytes_transferred": 120000000
  }
}
```

Required context: stable `actor_id`, `role` (`employee` or `administrator`), and `resource`. Use an immutable directory ID or pseudonym rather than an IP address or mutable display name. Optional fields default conservatively: `sensitive`, `outside_scope`, `honeytoken`, and `approved_change` are false; record and byte counts are zero; destination is unknown; admin action is none. Boolean fields must be JSON booleans, counts must be nonnegative integers, and unknown context fields are rejected. Context may also be supplied in `parsed_data.insider`, but not in both locations. Client-supplied assessments are discarded and recomputed by the server.

Derive context from a trusted collector and authoritative policy: directory role, resource ACLs, classification, designated decoys, destination allowlists, and approved change records. Never accept `approved_change` or scope declarations from the monitored account itself. Missing telemetry is not evidence of safe activity. `raw_log` is optional; avoid ingesting actual document contents, secrets, or unnecessary personal data.

## Detection policy v1

| Finding | Observations required | Score |
| --- | --- | --- |
| Decoy interaction | Designated honeytoken plus download, upload, command or canary trip | 90 |
| Out-of-scope access | Sensitive resource plus outside permitted scope on download, upload or command | 70 |
| Bulk sensitive access | Sensitive resource plus at least 1,000 records or 100,000,000 bytes in one download, upload or command event | 65 |
| Unapproved transfer | Sensitive upload to an explicitly unapproved external destination | 85 |
| Audit disabling | Administrator command; audit_disabled; no approved change | 85 |
| Privilege change | Administrator command; privilege_change; no approved change | 70 |
| Credential export | Administrator command; credential_export; no approved change | 85 |

The strongest matching rule determines score and the primary MITRE tag; all rule explanations are retained in `parsed_data.insider_assessment`. MITRE tags are investigative hints, not proof of a particular technique. An approved administrative change suppresses only the administrative rules; decoy and data-access findings still apply. A canary trip remains score 90 even without a honeytoken flag, and an explicit exploit attempt retains score 70. Insider context bypasses external LLM enrichment.

## Investigation

Events and investigation timelines show account, role, resource and rule explanations. Filter **Events** by account ID, or use `GET /api/v1/events?actor_id=directory-account-001` to review that account across IPs and sessions. Alerts include identity metadata and recommendations to preserve audit evidence, verify business purpose and consider compromised credentials. Open-alert deduplication uses account and rule names rather than shared source IP; it retains the existing ten-minute window. Review Events for all occurrences.

Identity context and assessments use the existing JSONB event data. The live showcase additionally requires migration `0002_live_demo`, applied automatically by the Docker Compose backend startup. Deploy the updated backend and frontend together.

## Operational limits

This is deterministic, per-event detection. Bulk thresholds are starter lab policy, not learned behavioral baselines or rolling-volume correlation. A directory login is not a decoy login, so collectors should provide insider context for legitimate internal telemetry. Public URL-canary callbacks identify a network request only; they must not infer an employee identity from an IP address, URL scanner or user agent.

Production use still requires trusted identity, endpoint, DLP, file-share, database, cloud and administrative audit collectors; service authentication; organizational scope and allowlist policy; RBAC; access auditing; retention enforcement; and tamper-evident evidence storage. The project does not yet supply these integrations. Configure collection and review around the organization's approved monitoring policy. Analysts must validate findings before any containment decision.
