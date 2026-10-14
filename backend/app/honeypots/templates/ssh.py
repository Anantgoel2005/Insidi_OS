from __future__ import annotations


SSH_DOCKERFILE = r"""
FROM alpine:3.20

RUN apk add --no-cache openssh-server && \
    ssh-keygen -A && \
    echo 'root:honeypot123' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e", "-o", "LogLevel=VERBOSE"]
"""


def build_ssh_honeypot(docker_client, network_name: str, honeypot):
    import io
    tag = f"honeypot-ssh-{honeypot.id.hex[:8]}:latest"

    dockerfile = io.BytesIO(SSH_DOCKERFILE.encode())
    image, _ = docker_client.images.build(
        fileobj=dockerfile,
        tag=tag,
        rm=True,
    )

    container = docker_client.containers.run(
        image=image.id,
        name=f"honeypot-ssh-{honeypot.id.hex[:8]}",
        detach=True,
        network=network_name,
        ports={"22/tcp": ("127.0.0.1", None)},
        restart_policy={"Name": "unless-stopped"},
    )
    return container
