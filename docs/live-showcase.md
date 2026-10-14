# Insidi_OS live showcase

Open **Live Showcase** at `/demo`. Choose employee data misuse or administrator abuse, select a pace and click **Start live demo**. Actions arrive progressively in three feeds: attacker activity, detection engine and system response. The top counters show persisted events, distinct alerts, peak risk and sandbox denials.

Use **Pause** to explain a stage, **Next step** to advance once, and **Resume** to continue. **Start in step mode** gives complete presentation control from the beginning. **Presenter view** hides navigation and widens the stage. Click a stage or a feed card to inspect its explanation. **Replay scenario** starts a fresh run; existing evidence is retained. **Open investigation** links to the event timeline. The optional instant generator remains available for quick investigations.

## Suggested two-minute walkthrough

1. Select employee data misuse at the four-second showcase pace. Explain that events and alerts are real backend records while attack actions and containment are synthetic.
2. Start. The valid login stays below the alert threshold. Contrast that with the next action: an out-of-scope decoy access generates a critical finding and isolates the synthetic decoy.
3. Pause after bulk collection to show the threshold and inspect the recorded evidence.
4. Resume. The external transfer triggers a real alert and blocks synthetic egress. The next retry is denied using the run's persisted containment state.
5. Show the retained investigation. Replay with administrator abuse: approved maintenance is benign, unapproved audit disabling restores the synthetic audit control, privilege escalation is denied, and credential export contains the synthetic account.

## Execution and trust boundary

The FastAPI lifespan starts a scheduler that checks every 500 ms for due runs. Each step goes through `process_event` with offline enrichment, captures the actual alert result and measured processing duration, updates the synthetic sandbox and commits the event and run state in one database transaction. The console polls the run every 700 ms; displaying an event never generates an attack. Playback continues if the page closes and resumes its UI state after refresh. Stop the run to halt it server-side.

Runs and response history are stored in `demo_runs` (migration `0002_live_demo`). Row locks with `SKIP LOCKED` prevent multiple API workers from processing the same scheduled step. Manual stepping uses a cursor to avoid duplicate events on retries. Demo alerts are deduplicated within their own run so a previous presentation does not suppress new alerts. At most ten running or paused runs are allowed. Stop unfinished runs before starting another.

Control endpoints require the existing analyst authentication and CSRF checks: `POST /api/v1/demo/live`, `GET /api/v1/demo/live/{session_id}`, and `POST /api/v1/demo/live/{session_id}/control`. They are unavailable when `DEMO_MODE=false`. Run state can be read from another authenticated browser using the session ID; the UI remembers its latest run in local storage.

**Containment is a synthetic sandbox response.** It changes only that run's JSON state, never an operating-system account, firewall, document, privilege or external endpoint. No attack commands execute and no exfiltration occurs. Denied attempts are still assessed as suspicious attempts. Alert recommendations continue to require analyst review for real operational containment. Do not present sandbox controls as installed enterprise enforcement.

The scheduler and console tolerate an interrupted connection by retaining database progress. A paused or stopped run may finish a step already processing under its row lock before the pause/stop request is acknowledged. Once acknowledged, it will not schedule another step. Replaying does not erase events or alerts from any run.

## Validation

Backend tests cover timed event processing, benign comparisons, persisted sandbox responses, denied retries, manual-step idempotency, demo gating and scheduler locking. Browser tests cover live progression, refresh recovery, presenter view, step mode, and the retained instant workflows.
