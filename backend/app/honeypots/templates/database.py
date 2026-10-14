from __future__ import annotations


def build_database_honeypot(docker_client, network_name: str, honeypot):
    """Deploy a fake database honeypot (MySQL protocol with decoy data)."""
    container = docker_client.containers.run(
        image="mysql:8.0",
        name=f"honeypot-db-{honeypot.id.hex[:8]}",
        detach=True,
        network=network_name,
        ports={"3306/tcp": ("127.0.0.1", None)},
        environment={
            "MYSQL_ROOT_PASSWORD": "FakeRootPassword123!",
            "MYSQL_DATABASE": f"decoy_{honeypot.id.hex[:6]}",
            "MYSQL_USER": "admin",
            "MYSQL_PASSWORD": "AdminPassword123!",
        },
        restart_policy={"Name": "unless-stopped"},
    )
    return container
