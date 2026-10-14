from __future__ import annotations


def build_http_honeypot(docker_client, network_name: str, honeypot):
    """Deploy an HTTP honeypot serving a realistic fake web application."""
    container = docker_client.containers.run(
        image="nginx:alpine",
        name=f"honeypot-http-{honeypot.id.hex[:8]}",
        detach=True,
        network=network_name,
        ports={"80/tcp": ("127.0.0.1", None), "443/tcp": ("127.0.0.1", None)},
        environment={
            "HONEYPOT_NAME": honeypot.name,
        },
        restart_policy={"Name": "unless-stopped"},
    )
    return container
