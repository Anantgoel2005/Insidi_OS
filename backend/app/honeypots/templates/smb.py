from __future__ import annotations


SMB_DOCKERFILE = r"""
FROM alpine:3.20

RUN apk add --no-cache samba-server samba-common-tools && \
    mkdir -p /tmp/share && \
    echo "Fake payroll report\nEmployee SSN: 123-45-6789\nAPI Key: sk-decoy-key-2025" > /tmp/share/credentials.txt && \
    echo "VPN Config for corporate network\nServer: vpn.internal.corp\nUser: admin\nPass: Winter2025!" > /tmp/share/vpn_config.ovpn && \
    printf '[global]\nworkgroup = WORKGROUP\nserver string = Corp File Server\nlog file = /var/log/samba/%m.log\nmax log size = 50\nsecurity = user\nmap to guest = bad user\n\n[Documents]\npath = /tmp/share\nbrowsable = yes\nread only = no\nguest ok = yes\n' > /etc/samba/smb.conf

EXPOSE 139 445

CMD ["smbd", "--foreground", "--no-process-group"]
"""


def build_smb_honeypot(docker_client, network_name: str, honeypot):
    import io
    tag = f"honeypot-smb-{honeypot.id.hex[:8]}:latest"

    dockerfile = io.BytesIO(SMB_DOCKERFILE.encode())
    image, _ = docker_client.images.build(
        fileobj=dockerfile,
        tag=tag,
        rm=True,
    )

    container = docker_client.containers.run(
        image=image.id,
        name=f"honeypot-smb-{honeypot.id.hex[:8]}",
        detach=True,
        network=network_name,
        ports={"139/tcp": ("127.0.0.1", None), "445/tcp": ("127.0.0.1", None)},
        restart_policy={"Name": "unless-stopped"},
    )
    return container
