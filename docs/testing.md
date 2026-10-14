# Testing Insidi_OS

Start with the [installation guide](getting-started.md). Run commands from the directory indicated in each section. Unit tests do not require a running Docker stack; browser tests do.

## Backend unit tests

Install Python 3.12. From the repository root, Windows PowerShell:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
Set-Location backend
$env:PYTHONPATH = '.'
..\.venv\Scripts\python.exe -m compileall -q app tests
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ..
```

Linux/macOS, from the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m pip check
cd backend
../.venv/bin/python -m compileall -q app tests
PYTHONPATH=. ../.venv/bin/python -m pytest -q
cd ..
```

Using the virtual environment's executable directly avoids needing to activate it. If `python --version` reports another version on Windows, use `py -3.12 -m venv .venv` instead.

Tests cover configuration, authentication/security behavior, insider detection, demo scheduling, SSH log parsing and session deduplication, and active TCP connection snapshots. The latest local verification at the connection-tracking update passed 71 backend tests; the count may increase as the project develops.

## Frontend checks and production build

Install Node.js 22. From the repository root:

```text
cd frontend
npm ci
npm run typecheck
npm run build
```

`npm ci` installs the committed lockfile. A successful build checks the production frontend; it does not start the backend or perform browser tests.

## Browser workflow tests

Start the application from another terminal at the repository root:

```text
docker compose up -d --build --wait
```

In the `frontend` directory, after `npm ci`, install Chromium:

```text
npx playwright install chromium
```

On Linux, use `npx playwright install --with-deps chromium` if browser system libraries are missing.

Windows PowerShell, still in `frontend`:

```powershell
# Replace these values with the credentials in your root .env.
$env:E2E_ADMIN_USERNAME = 'admin'
$env:E2E_ADMIN_PASSWORD = 'your-local-password'
$env:PLAYWRIGHT_BASE_URL = 'http://localhost:3000'
npm run test:e2e
```

Linux/macOS, still in `frontend`:

```bash
export E2E_ADMIN_USERNAME='admin'
export E2E_ADMIN_PASSWORD='your-local-password'
export PLAYWRIGHT_BASE_URL='http://localhost:3000'
npm run test:e2e
```

Use your actual password, not the placeholder shown above. Without these variables, tests assume the sample credentials in `.env.example`. Do not commit passwords in scripts or test fixtures.

The latest local verification passed seven browser tests covering login, generated investigations, employee and administrator scenarios, live pause/resume, persisted demo progress, replay/presenter controls, and decoy connection display states. The connection-display test uses mocked API snapshots; it does not replace the [real SSH test](honeypot-testing.md).

Browser tests create synthetic events, alerts, and demo runs in the running database. Run them against a local test instance. Failed runs retain screenshots and traces under `frontend/test-results/`; inspect a trace with `npx playwright show-trace` followed by the actual trace file path.

The API limits login attempts to ten within five minutes. Repeated full test runs can hit HTTP 429. Wait five minutes, or restart only the local backend from the repository root:

```text
docker compose restart backend
```

In lab mode, use `docker compose -f docker-compose.yml -f docker-compose.lab.yml restart backend`. This resets the in-memory login limit and briefly interrupts the API without deleting database evidence or restarting SSH decoys.

## Dependency audit and CI

From `frontend`:

```text
npm audit --omit=dev --audit-level=high
```

This is a separate security check. At the connection-tracking update, the production dependency audit still reported known findings involving Next.js, sharp, and source-map-js. Passing functional tests does not mean this audit is clean. Review the current output before deployment; do not use `npm audit fix --force` without checking compatibility and rerunning the tests.

The repository's [CI workflow](../.github/workflows/ci.yml) runs backend checks, frontend checks/build/audit, and Docker-backed Playwright tests. A failing dependency audit can make CI red even when unit and browser workflows pass.
