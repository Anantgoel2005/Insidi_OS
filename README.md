# Insider Threat Orchestrator

[![CI](https://github.com/Anantgoel2005/insider-threat-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Anantgoel2005/insider-threat-orchestrator/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Anantgoel2005/insider-threat-orchestrator/actions/workflows/codeql.yml/badge.svg)](https://github.com/Anantgoel2005/insider-threat-orchestrator/actions/workflows/codeql.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](frontend/package.json)

> **A self-hostable analyst console for employee and administrator insider-threat investigations.**

Insider Threat Orchestrator combines identity-aware telemetry with controlled decoy and canary activity to produce explainable alerts and investigation timelines for employee data misuse and privileged administrator abuse. It supports deterministic lab demonstrations without requiring a live attacker or an external LLM.

This separate project builds on [Deception Orchestrator](https://github.com/Anantgoel2005/deception-orchestrator) and preserves its development history. See the [insider-threat guide](docs/insider-threats.md) for the new workflows and integration limits.

[Quick start](#quick-start) · [Demo flow](#demo-flow) · [Architecture](#architecture) · [Deployment](#deployment) · [Security](docs/security.md)

> [!WARNING]
> This is a defensive lab and portfolio project, not an internet-exposed honeypot platform. Run decoys only on systems and networks you own. The hosted control plane never needs Docker socket access.

## See it in action

![Animated walkthrough of the Deception Orchestrator analyst workflow](docs/assets/demo-walkthrough.gif)

| Analyst dashboard | MITRE-tagged investigation |
| --- | --- |
| ![Deception Orchestrator dashboard showing live attack telemetry](docs/assets/dashboard.png) | ![Attack investigation showing the deterministic credential-to-exfiltration timeline](docs/assets/investigation.png) |

Both views above were captured from the bundled offline demo. The workflow generates safe TEST-NET telemetry, processes it through the production event pipeline, and opens the resulting investigation automatically.

## What you can demonstrate

| Capability | What it shows |
| --- | --- |
| **Protected analyst console** | Single-admin login, HttpOnly sessions, CSRF checks, rate limits, and deployment status. |
| **Demo Lab** | A deterministic credential-to-exfiltration scenario using TEST-NET addresses. |
| **Investigation workflow** | MITRE-tagged events, severity scoring, alert triage, and an ordered attack timeline. |
| **URL canaries** | One-time beacon callbacks that generate a critical event and alert. |
| **Local decoy lab** | Explicit, local-only Docker decoys with a separate log-monitor worker. |
| **Optional AI enrichment** | DeepSeek can enrich analysis when configured; deterministic offline rules remain the default fallback. |
| **Insider-threat findings** | Identity-aware rules for employee data misuse and privileged administrator abuse, with account filters and explainable evidence. |
| **Insider demo scenarios** | Valid internal logins, decoy data access, bulk exports, unapproved transfers, audit disabling, and privilege changes. |

See the [insider-threat guide](docs/insider-threats.md) for collector metadata, detection thresholds, API examples and operational limits. Choose **Employee data misuse** or **Privileged administrator misuse** in Demo Lab to try the workflows.

## Architecture

```mermaid
flowchart LR
    Analyst["Security analyst"] --> Console["Next.js analyst console"]
    Console --> API["FastAPI control plane"]
    API --> DB[("PostgreSQL")]
    API --> Queue["Redis streams"]
    Canary["URL canary callback"] --> API
    Worker["Local lab worker"] --> API
    Worker --> Decoys["Private Docker decoys"]
```

The public surface is limited to the authenticated dashboard and an optional URL-canary callback. Docker-managed decoys are a local-lab capability, not a hosted deployment feature.

See the [architecture and trust-boundary guide](docs/architecture.md) for component responsibilities, security invariants, and deliberate limitations.

## Engineering quality

- **Fail-closed production configuration** validates secrets, password hashing, HTTPS URLs, session limits, and explicit CORS origins before startup.
- **Hardened browser sessions** use HttpOnly cookies, issuer/audience-bound JWTs, CSRF protection, login throttling, and no-store API responses.
- **Reproducible validation** runs backend unit tests plus a real-browser analyst workflow, Python dependency checks, TypeScript validation, a Next.js production build, and a production dependency audit.
- **Supply-chain controls** pin GitHub Actions to immutable commits, run CodeQL, and schedule Dependabot updates for Python, npm, and Actions.
- **Least-privilege deployment** runs application containers as non-root users and keeps PostgreSQL, Redis, FastAPI, and the Docker socket outside the public production surface.

## Quick start

### Prerequisites

- Docker Desktop or Docker Engine with Compose v2
- A free local port `3000` for the console and `8000` for the API

### Start the safe control plane

```bash
cp .env.example .env
# PowerShell: Copy-Item .env.example .env

# Set SECRET_KEY and ADMIN_PASSWORD in .env, then:
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), then sign in with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`.

The default configuration works offline, and the bundled demo always uses deterministic local MITRE mapping even when an external provider is configured. To enable DeepSeek enrichment for non-demo telemetry, set:

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_key_here
LLM_MODEL=deepseek-v4-flash
```

## Demo flow

1. Open **Demo Lab** and run the safe scenario.
2. Review the generated credential attempts, successful access, command activity, exploit attempt, and canary trip in **Events**.
3. Open the linked **Investigation** to follow the ordered attack timeline and MITRE context.
4. In **Alerts**, acknowledge or resolve the high-confidence findings.
5. In **Canaries**, generate a URL beacon, copy its callback URL, and fetch it once to trigger a critical alert.

The scenario uses documentation-only TEST-NET addresses and follows the same event-processing path as the decoy and canary pipelines.

## Local decoy lab

Docker decoys are disabled by default. Enable them only on a controlled machine:

```bash
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build
```

Deploy an SSH decoy from **Local Decoys**, then connect from a VM or device you control on the same lab network. The worker records the resulting connection events in the analyst console.

> [!CAUTION]
> Do not expose the included lab templates to the public internet. They are intentionally simple, use fake known credentials, and exist only to demonstrate the telemetry workflow.

## Deployment

The production overlay is for a **control plane plus URL-canary callbacks** on a Docker-capable Linux VPS. It does not mount the Docker socket or expose lab decoys.

1. Point a domain's DNS record at the VPS.
2. Configure `DOMAIN`, `APP_BASE_URL`, `CANARY_BASE_URL`, a 32+ character `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD_HASH`.
3. Run:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
   ```

4. Verify `/health`, sign in over HTTPS, generate a URL canary, and fetch its callback URL from a permitted external device.

See the [deployment notes](docs/deployment.md), [demo script](docs/demo-script.md), [architecture guide](docs/architecture.md), [security notes](docs/security.md), [release checklist](docs/release-checklist.md), and [roadmap](docs/roadmap.md) for details.

## API and validation

- Local OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Key routes: `POST /api/v1/auth/login`, `POST /api/v1/demo/run`, `GET /api/v1/investigations/{session_id}`, and public `GET /c/{token}`
- CI runs backend tests, dependency checks, TypeScript validation, a frontend production build, a production npm audit, and Playwright coverage of login and the end-to-end demo investigation on every pull request.
- CodeQL analyzes Python and TypeScript on pull requests, pushes to `main`, and a weekly schedule.

## Project status

This repository is portfolio-ready for demonstrating a SOC deception workflow. A company deployment would require a separate collector/agent architecture, enterprise identity/RBAC, SIEM integrations, hardened decoy templates, audit retention, and operational assurance.

The [roadmap](docs/roadmap.md) separates portfolio-release work, operational maturity, and organizational deployment so experimental scope is not presented as production capability.

## License and responsible use

No license is currently included. Before accepting external contributions or commercial use, add an explicit license and review the [security boundary](docs/security.md).
