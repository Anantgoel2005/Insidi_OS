# Testing a local honeypot

The live showcase is synthetic. Local Decoys starts separate, real lab containers and records their logs. Enable the lab overlay:

```powershell
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build
```

The overlay mounts Docker's socket and adds its owning group to the non-root backend and worker. Docker Desktop's socket group is normally GID 0. On another host, set `DOCKER_SOCKET_GID` to the socket's actual numeric group before starting the overlay.

On a Linux host using `/var/run/docker.sock`, discover the group and start with it:

```bash
export DOCKER_SOCKET_GID="$(stat -c '%g' /var/run/docker.sock)"
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build --wait
```

For initial cloning and configuration, see [Install and run](getting-started.md).

Deploy an SSH decoy and wait for **running**. Use its published host port, rather than its private container IP or service port 22. The console's Ports field shows mappings such as `127.0.0.1:32768->22/tcp`. Verify the actual binding:

```powershell
docker ps --filter name=honeypot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# Replace the example with the SSH container name shown above.
$decoyName = 'honeypot-ssh-your-id'
docker port $decoyName 22/tcp
```

Connect from the same Windows machine, substituting the reported host port:

```powershell
# Replace 32768 with your decoy's actual published host port.
$decoyPort = 32768
ssh -p $decoyPort root@127.0.0.1
```

On Linux/macOS, use `docker port honeypot-ssh-your-id 22/tcp` with your actual container name, then `ssh -p 32768 root@127.0.0.1` with your actual port.

The SSH template uses the intentionally fake lab password `honeypot123`. Try one incorrect password to create a failed-login event, then reconnect with the correct lab password. At the decoy prompt, use `whoami`, `pwd`, and `exit`.

Open **Local Decoys**, **Events** and **Alerts**. Local Decoys refreshes every three seconds. **Active connections** is a live count of established TCP sockets inside the decoy, including connections that have not authenticated. **Total connections observed** is session history reconstructed from SSH endpoint logs; several password attempts in one connection count as one connection. **Unique source IPs** counts observed peers, which can be Docker bridge addresses rather than employee identities. Unavailable Docker monitoring is shown as unavailable, never as a misleading zero.

The worker checks SSH logs every two seconds. It recognizes connection, authentication and disconnection messages, and infers an opening when the first available log is an authentication record. Session IDs link the records for an investigation. Stable log fingerprints stored in PostgreSQL prevent repeated counting after worker restarts or overlapping reads; startup messages are ignored. New SSH containers use verbose logging. Existing decoys also work with their default authentication logs, without restarting an open SSH session.

A matched failed password creates `login_attempt`; accepted credentials create `login_success`, which receives score 60 and a high-severity alert in the decoy pipeline. This is different from a legitimate internal login with insider context. Routine commands typed into an SSH session are not captured as a shell-command audit trail by the current sshd template.

Inspect failures with:

```powershell
docker logs $decoyName --tail 30
docker compose -f docker-compose.yml -f docker-compose.lab.yml logs --tail=30 backend worker
```

New decoy ports bind to `127.0.0.1` for local testing. Their private Docker IPs are not the normal connection target from Windows. A separate VM needs explicitly arranged connectivity to the controlled lab; it cannot use the Windows host's loopback address as its own. Do not publish these simple templates to the internet.

HTTP decoys can be tested with `curl.exe -i http://127.0.0.1:32769/`, replacing `32769` with the displayed HTTP host port (use `curl` on Linux/macOS). The current HTTP template is a basic Nginx server, and its logs are not yet normalized with a dedicated HTTP parser. Use SSH authentication events or the live showcase for a reliable detection presentation.
