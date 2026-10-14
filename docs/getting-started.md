# Install and run Insidi_OS

This guide starts a local development/demo installation. For HTTPS hosting, use the separate [deployment guide](deployment.md). The live showcase works without an AI API key; the first installation still needs internet access to download images and dependencies.

## Requirements

- Git and Docker Desktop (Linux containers) or Docker Engine with Compose v2.
- On Windows, start Docker Desktop and wait until its engine is running.
- Free host ports: `3000` (console), `8000` (API), `5432` (PostgreSQL), and `6379` (Redis).
- For tests outside containers: Python 3.12 and Node.js 22 with npm. These are not required just to run the Docker demo.

Check Docker before continuing:

```text
docker version
docker compose version
```

`docker version` must display both client and server information.

## 1. Clone and configure

```text
git clone https://github.com/Anantgoel2005/Insidi_OS.git
cd Insidi_OS
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
# Generate a secret and paste the printed value into SECRET_KEY in .env:
$secretBytes = New-Object byte[] 32
$secretGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$secretGenerator.GetBytes($secretBytes)
[BitConverter]::ToString($secretBytes).Replace('-', '').ToLowerInvariant()
$secretGenerator.Dispose()
notepad .env
```

Linux/macOS:

```bash
cp .env.example .env
openssl rand -hex 32
# Paste the printed secret into .env using your preferred editor.
```

Set `SECRET_KEY` to the generated value and change `ADMIN_PASSWORD` to your own local password. Keep the following settings for the bundled demo:

```dotenv
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=
DEMO_MODE=true
LLM_PROVIDER=offline
ENABLE_LOCAL_DECOYS=false
APP_BASE_URL=http://localhost:3000
CANARY_BASE_URL=http://localhost:8000
```

Keep `.env` private; it is ignored by Git. Run the remaining Compose commands from the repository root.

## 2. Start the application

```text
docker compose up -d --build --wait
docker compose ps
```

The backend applies database migrations automatically. Open [the console](http://localhost:3000) and sign in using `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`.

- Console: <http://localhost:3000>
- API health: <http://localhost:8000/health>
- API reference: <http://localhost:8000/docs>

## 3. Present an insider-threat scenario

Open **Live Showcase**, select **Employee data misuse** or **Administrator abuse**, and click **Start live demo**. Watch the attack, detection, and response feeds; use Pause, Next step, Replay, and Presenter view during your presentation.

The detection pipeline and stored evidence are real. Scenario actions and containment are simulated; they do not disable actual employee accounts. See the [showcase guide](live-showcase.md) for a presentation script.

## 4. Enable real local honeypots (optional)

```text
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build --wait
```

This overlay enables Docker access for the backend and worker. Changing only `ENABLE_LOCAL_DECOYS` in `.env` does not mount the socket. Linux hosts may also need the socket group setting described in the [honeypot testing guide](honeypot-testing.md).

Open **Local Decoys**, deploy an SSH decoy, and use its displayed localhost port. The [honeypot guide](honeypot-testing.md) covers login credentials, live connection counts, and expected events. No real decoy is needed for the synthetic showcase or automated browser tests.

## 5. Run automated tests

Follow [Testing Insidi_OS](testing.md) for Python unit tests, TypeScript checks, production builds, browser tests, and dependency checks. Set the browser test password to the password you chose in `.env`.

## Updating and stopping

For an existing checkout, pull updates and rebuild using the same mode you started with:

```text
git pull --ff-only
docker compose up -d --build --wait
```

For lab mode, replace the second command with the two-file lab command above. Existing database volumes are preserved, and migrations run on startup.

Stop the control plane from the repository root:

```text
docker compose down
```

For lab mode, use `docker compose -f docker-compose.yml -f docker-compose.lab.yml down`. Neither command removes database volumes. `down -v` deletes those volumes and their evidence.

Decoy containers are created separately from Compose and can keep running after the control plane stops. List them with `docker ps --filter name=honeypot`; stop a specific decoy using `docker stop` followed by its actual container name.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Docker server is unavailable | Start Docker Desktop, select Linux containers, and retry `docker version`. If it still fails, inspect Docker Desktop diagnostics. |
| Port already allocated | Check for another instance or a local PostgreSQL/Redis service using one of the four host ports. |
| Build or startup fails | Run `docker compose logs --tail=100 backend frontend worker`; check network access and the first error. Use the lab overlay in this command when running lab mode. |
| Login fails | Check your `.env` credentials and rebuild/recreate after changing them. Clear `ADMIN_PASSWORD_HASH` when using the development plaintext password setting. |
| Honeypot deployment fails | Use the lab overlay, check Docker socket permissions, and read backend/worker logs. |
| Active connections says zero | Keep an SSH connection open and allow three seconds for refresh. The active count falls back to zero when the TCP session closes; historical totals remain. |
| Browser tests return 401 or 429 | Pass your actual test credentials; for repeated runs, see the login-limit notes in [testing](testing.md). |

The local templates are intended for a controlled lab. Review [security boundaries](security.md) before hosting or integrating real organizational data.
