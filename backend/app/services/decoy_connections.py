"""Read current TCP state from the decoy's own network namespace."""
import asyncio

from app.config import settings
from app.models.honeypot import Honeypot, HoneypotStatus

SERVICE_PORTS = {"ssh": {22}, "http": {80, 443}, "database": {3306, 5432}, "smb": {139, 445}}


def count_established(output: str, ports: set[int]) -> int:
    count = 0
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[3] != "01":  # Linux TCP_ESTABLISHED
            continue
        try:
            port = int(fields[1].rsplit(":", 1)[1], 16)
        except (ValueError, IndexError):
            continue
        count += int(port in ports)
    return count


def _read_count(container_id: str, ports: set[int]) -> int:
    from app.core.docker_client import get_docker
    result = get_docker().containers.get(container_id).exec_run(["cat", "/proc/net/tcp", "/proc/net/tcp6"])
    if result.exit_code != 0:
        raise RuntimeError("Cannot read decoy TCP state")
    return count_established(result.output.decode("utf-8", errors="replace"), ports)


async def connection_snapshot(honeypot: Honeypot) -> tuple[int | None, str]:
    if not settings.enable_local_decoys:
        return None, "disabled"
    if honeypot.status != HoneypotStatus.RUNNING:
        return None, "inactive"
    if not honeypot.container_id:
        return None, "unavailable"
    try:
        count = await asyncio.wait_for(asyncio.to_thread(_read_count, honeypot.container_id, SERVICE_PORTS[honeypot.honeypot_type.value]), timeout=3)
        return count, "live"
    except Exception:
        # Unreachable Docker must not be displayed as zero connected clients.
        return None, "unavailable"
