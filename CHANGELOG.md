# Changelog

All notable changes to Insidi_OS are documented here.

## Unreleased

- Rebrand the insider-threat version as Insidi_OS with a vector identity, redesigned login, consistent console navigation and API metadata.
- Add a live showcase with timed attack, detection and sandbox-response feeds, presenter view, pause, stepping and replay.
- Persist run state, response evidence and per-run alerts; add migration `0002_live_demo`.

Earlier release history is inherited from Deception Orchestrator.

## 1.0.0 - 2026-08-11

### Added

- Protected analyst console with dashboard, event, alert, investigation, canary, demo, and local-decoy workflows.
- Deterministic credential-to-exfiltration demo using safe TEST-NET telemetry and local MITRE mapping.
- Optional DeepSeek enrichment for non-demo telemetry with an offline rules fallback.
- Docker Compose development, local-lab, and production configurations with health checks and non-root application containers.
- Backend unit coverage and Playwright tests for authentication and the end-to-end demo investigation.
- CI, CodeQL, Dependabot, security guidance, architecture documentation, and a reproducible release workflow.

### Security

- Fail-closed production settings, issuer/audience-bound HttpOnly sessions, CSRF validation, login throttling, explicit CORS, and no-store API responses.
- Production services keep PostgreSQL, Redis, FastAPI, and the Docker socket outside the public surface.

### Scope

- This release is a defensive portfolio lab and single-admin control plane. It is not an internet-facing managed honeypot platform or an enterprise multi-tenant service.
