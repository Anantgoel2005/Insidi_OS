from __future__ import annotations

import uuid
from typing import TypedDict

from sqlalchemy.orm import Session
from sqlalchemy import select

import docker as docker_pkg

from app.config import settings
from app.core.docker_client import get_docker
from app.models.honeypot import Honeypot, HoneypotStatus


class DeployResult(TypedDict):
    container_id: str
    ip_address: str
    ports: str


class HoneypotManager:
    NETWORK_NAME = "deception-net"

    def __init__(self) -> None:
        self._docker = get_docker()

    def _ensure_network(self) -> None:
        try:
            self._docker.networks.get(self.NETWORK_NAME)
        except Exception:
            self._docker.networks.create(
                self.NETWORK_NAME,
                driver="bridge",
                ipam=docker_pkg.types.IPAMConfig(
                    driver="default",
                    pool_configs=[
                        docker_pkg.types.IPAMPool(
                            subnet=settings.honeypot_subnet,
                            gateway=settings.honeypot_gateway,
                        )
                    ],
                ),
            )

    def deploy(self, db: Session, honeypot_id: uuid.UUID) -> DeployResult:
        self._ensure_network()

        honeypot = db.execute(select(Honeypot).where(Honeypot.id == honeypot_id)).scalar_one()
        honeypot.status = HoneypotStatus.DEPLOYING
        db.flush()

        try:
            if honeypot.honeypot_type.value == "ssh":
                container = self._deploy_ssh(honeypot)
            elif honeypot.honeypot_type.value == "http":
                container = self._deploy_http(honeypot)
            elif honeypot.honeypot_type.value == "database":
                container = self._deploy_database(honeypot)
            elif honeypot.honeypot_type.value == "smb":
                container = self._deploy_smb(honeypot)
            else:
                raise ValueError(f"Unknown honeypot type: {honeypot.honeypot_type.value}")

            container.reload()
            network_settings = container.attrs["NetworkSettings"]
            bridge = network_settings["Networks"].get(self.NETWORK_NAME, {})
            ip_addr = bridge.get("IPAddress", "0.0.0.0")

            honeypot.container_id = container.id
            honeypot.ip_address = ip_addr
            bindings = network_settings.get("Ports") or {}
            published = [
                f"{binding['HostIp']}:{binding['HostPort']}->{port}"
                for port, values in sorted(bindings.items())
                for binding in (values or [])
            ]
            honeypot.ports = ", ".join(published) or self._default_ports(honeypot.honeypot_type.value)
            honeypot.status = HoneypotStatus.RUNNING
            db.flush()

            return DeployResult(
                container_id=container.id,
                ip_address=ip_addr,
                ports=honeypot.ports or "",
            )
        except Exception as exc:
            honeypot.status = HoneypotStatus.ERROR
            db.flush()
            raise exc

    def stop(self, db: Session, honeypot_id: uuid.UUID) -> None:
        honeypot = db.execute(select(Honeypot).where(Honeypot.id == honeypot_id)).scalar_one()

        if honeypot.container_id:
            try:
                container = self._docker.containers.get(honeypot.container_id)
                container.stop(timeout=10)
                container.remove()
            except Exception:
                pass

        honeypot.status = HoneypotStatus.STOPPED
        honeypot.container_id = None
        honeypot.ip_address = None
        db.flush()

    def pause(self, db: Session, honeypot_id: uuid.UUID) -> None:
        honeypot = db.execute(select(Honeypot).where(Honeypot.id == honeypot_id)).scalar_one()

        if honeypot.container_id:
            try:
                container = self._docker.containers.get(honeypot.container_id)
                container.pause()
            except Exception:
                pass

        honeypot.status = HoneypotStatus.PAUSED
        db.flush()

    def unpause(self, db: Session, honeypot_id: uuid.UUID) -> None:
        honeypot = db.execute(select(Honeypot).where(Honeypot.id == honeypot_id)).scalar_one()

        if honeypot.container_id:
            try:
                container = self._docker.containers.get(honeypot.container_id)
                container.unpause()
            except Exception:
                pass

        honeypot.status = HoneypotStatus.RUNNING
        db.flush()

    def _deploy_ssh(self, honeypot: Honeypot):
        from app.honeypots.templates.ssh import build_ssh_honeypot
        return build_ssh_honeypot(self._docker, self.NETWORK_NAME, honeypot)

    def _deploy_http(self, honeypot: Honeypot):
        from app.honeypots.templates.http import build_http_honeypot
        return build_http_honeypot(self._docker, self.NETWORK_NAME, honeypot)

    def _deploy_database(self, honeypot: Honeypot):
        from app.honeypots.templates.database import build_database_honeypot
        return build_database_honeypot(self._docker, self.NETWORK_NAME, honeypot)

    def _deploy_smb(self, honeypot: Honeypot):
        from app.honeypots.templates.smb import build_smb_honeypot
        return build_smb_honeypot(self._docker, self.NETWORK_NAME, honeypot)

    @staticmethod
    def _default_ports(honeypot_type: str) -> str:
        mapping = {
            "ssh": "22/tcp",
            "http": "80/tcp,443/tcp",
            "database": "3306/tcp,5432/tcp",
            "smb": "445/tcp,139/tcp",
        }
        return mapping.get(honeypot_type, "")
