# Testing a local honeypot

The live showcase is synthetic. Local Decoys starts separate, real lab containers and records their logs. Enable the lab overlay:

```powershell
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d --build
```

The overlay mounts Docker's socket and adds its owning group to the non-root backend and worker. Docker Desktop's socket group is normally GID 0. On another host, set `DOCKER_SOCKET_GID` to the socket's actual numeric group before starting the overlay.

Deploy an SSH decoy and wait for **running**. Use its published host port, rather than its private container IP or service port 22. The console's Ports field shows mappings such as `127.0.0.1:32768->22/tcp`. Verify the actual binding:

```powershell
docker ps --filter name=honeypot --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker port <container-name> 22/tcp
```

Connect from the same Windows machine, substituting the reported host port:

```powershell
ssh -p <host-port> root@127.0.0.1
```

The SSH template uses the intentionally fake lab password `honeypot123`. Try one incorrect password to create a failed-login event, then reconnect with the correct lab password. At the decoy prompt, use `whoami`, `pwd`, and `exit`.

Open **Events** and **Alerts**. The worker checks container logs every five seconds and the console refreshes periodically; allow approximately fifteen seconds. A matched failed password creates `login_attempt`; accepted credentials create `login_success`, which receives score 60 and a high-severity alert in the decoy pipeline. This is different from a legitimate internal login with insider context. Routine commands typed into an SSH session are not captured as a shell-command audit trail by the current sshd template.

Inspect failures with:

```powershell
docker logs <container-name> --tail 30
docker compose -f docker-compose.yml -f docker-compose.lab.yml logs --tail=30 backend worker
```

New decoy ports bind to `127.0.0.1` for local testing. Their private Docker IPs are not the normal connection target from Windows. A separate VM needs explicitly arranged connectivity to the controlled lab; it cannot use the Windows host's loopback address as its own. Do not publish these simple templates to the internet.

HTTP decoys can be tested with `curl.exe -i http://127.0.0.1:<published-http-port>/`. The current HTTP template is a basic Nginx server, and its logs are not yet normalized with a dedicated HTTP parser. Use SSH authentication events or the live showcase for a reliable detection presentation.
