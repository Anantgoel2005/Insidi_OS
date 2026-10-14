import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.api.endpoints.honeypots import _deploy_honeypot_background
from app.models.honeypot import Honeypot, HoneypotStatus, HoneypotType


def test_failed_docker_initialization_marks_deployment_error(monkeypatch):
    import sqlalchemy
    import sqlalchemy.orm
    from app.honeypots import manager

    engine = MagicMock()
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    failed = SimpleNamespace(status=HoneypotStatus.DEPLOYING)
    session.get.return_value = failed
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda url: engine)
    monkeypatch.setattr(sqlalchemy.orm, "Session", lambda engine: session)
    monkeypatch.setattr(manager, "HoneypotManager", MagicMock(side_effect=RuntimeError("Docker daemon is not reachable")))

    _deploy_honeypot_background(uuid.uuid4())
    assert failed.status == HoneypotStatus.ERROR
    session.commit.assert_called_once()
    engine.dispose.assert_called_once()


def test_deployment_reports_the_published_host_port(monkeypatch):
    from app.honeypots import manager

    monkeypatch.setattr(manager, "get_docker", lambda: MagicMock())
    deployed = MagicMock()
    deployed.id = "synthetic-container-id"
    deployed.attrs = {"NetworkSettings": {
        "Networks": {"deception-net": {"IPAddress": "172.28.0.2"}},
        "Ports": {"22/tcp": [{"HostIp": "127.0.0.1", "HostPort": "32768"}]},
    }}
    controller = manager.HoneypotManager()
    monkeypatch.setattr(controller, "_deploy_ssh", lambda honeypot: deployed)
    honeypot = Honeypot(id=uuid.uuid4(), name="test", honeypot_type=HoneypotType.SSH)
    session = MagicMock()
    session.execute.return_value.scalar_one.return_value = honeypot
    result = controller.deploy(session, honeypot.id)
    assert result["ports"] == "127.0.0.1:32768->22/tcp"
    assert honeypot.status == HoneypotStatus.RUNNING
