import io

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import SessionLocal
from app.main import app
from app.models.ops import AuditLog
from app.models.user import User


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username="admin", password="CambiarAdmin123!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_rejects_bad_password(client):
    spoofed = "203.0.113.77"
    r = client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": spoofed},
        json={"username": "admin", "password": "incorrecta"},
    )
    assert r.status_code == 401
    with SessionLocal() as db:
        audit = db.query(AuditLog).filter(AuditLog.action == "login", AuditLog.result == "error").order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        assert audit.ip_address != spoofed


def test_login_and_me(client):
    headers = login(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "superadmin"


def test_totp_secret_is_encrypted(client):
    headers = login(client)
    setup = client.post("/api/auth/2fa/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    with SessionLocal() as db:
        admin = db.query(User).filter(User.username == "admin").one()
        assert admin.totp_secret != secret
        assert admin.totp_secret.startswith("gAAAA")
    code = pyotp.TOTP(secret).now()
    enabled = client.post("/api/auth/2fa/enable", headers=headers, json={"code": code})
    assert enabled.status_code == 200
    disabled = client.post(
        "/api/auth/2fa/disable",
        headers=headers,
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert disabled.status_code == 200


def test_visualizador_cannot_create_users(client):
    headers = login(client)
    created = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "visor",
            "email": "visor@example.com",
            "full_name": "Visor",
            "password": "ClaveSegura10",
            "role": "visualizador",
        },
    )
    assert created.status_code == 201
    visor_login = client.post("/api/auth/login", json={"username": "visor", "password": "ClaveSegura10"})
    visor_headers = {"Authorization": f"Bearer {visor_login.json()['access_token']}"}
    denied = client.post(
        "/api/users",
        headers=visor_headers,
        json={
            "username": "otro",
            "email": "otro@example.com",
            "full_name": "Otro",
            "password": "ClaveSegura10",
            "role": "soporte",
        },
    )
    assert denied.status_code == 403


def _enroll_agent(client):
    headers = login(client)
    token_res = client.post(
        "/api/agents/enrollment-tokens",
        headers=headers,
        json={"label": "lab", "max_uses": 5, "expires_hours": 24},
    )
    assert token_res.status_code == 201, token_res.text
    enroll_token = token_res.json()["token"]
    enrolled = client.post(
        "/agent/enroll",
        json={
            "token": enroll_token,
            "hostname": "PC-LAB-04",
            "os_family": "linux",
            "os_name": "Ubuntu",
            "os_version": "24.04",
            "architecture": "amd64",
            "agent_version": "0.1.0",
        },
    )
    assert enrolled.status_code == 200, enrolled.text
    return headers, enrolled.json()


def test_enroll_heartbeat_inventory_dashboard(client):
    headers, agent = _enroll_agent(client)
    agent_headers = {"Authorization": f"Bearer {agent['agent_token']}"}
    hb = client.post(
        "/agent/heartbeat",
        headers=agent_headers,
        json={
            "hostname": "PC-LAB-04",
            "os_family": "linux",
            "os_name": "Ubuntu",
            "os_version": "24.04",
            "architecture": "amd64",
            "ip_address": "192.168.1.50",
            "mac_address": "aa:bb:cc:dd:ee:04",
            "logged_user": "alumno",
            "cpu_model": "Test CPU",
            "cpu_percent": 12.5,
            "ram_total_mb": 8192,
            "ram_used_mb": 2048,
            "disk_total_gb": 100,
            "disk_used_gb": 40,
            "uptime_seconds": 3600,
            "agent_version": "0.1.0",
            "interfaces": [
                {
                    "name": "eth0",
                    "mac": "aa:bb:cc:dd:ee:04",
                    "ipv4": "192.168.1.50",
                    "ipv6": "",
                    "is_up": True,
                    "speed_mbps": 1000,
                    "bytes_sent": 1000,
                    "bytes_recv": 2000,
                }
            ],
        },
    )
    assert hb.status_code == 200, hb.text
    assert hb.json()["status"] == "online"
    inv = client.post(
        "/agent/inventory",
        headers=agent_headers,
        json={
            "software": [
                {"name": "Google Chrome", "version": "128.0", "publisher": "Google"},
                {"name": "LibreOffice", "version": "24.2", "publisher": "The Document Foundation"},
            ]
        },
    )
    assert inv.status_code == 200
    dash = client.get("/api/dashboard", headers=headers)
    assert dash.status_code == 200
    totals = dash.json()["totals"]
    assert totals["devices"] >= 1
    assert totals["online"] >= 1
    assert totals["programs"] >= 2
    search = client.get("/api/search", headers=headers, params={"q": "192.168.1.50"})
    assert any(d["hostname"] == "PC-LAB-04" for d in search.json()["devices"])
    chrome = client.get("/api/software/search", headers=headers, params={"name": "Chrome"})
    assert chrome.json()["device_count"] == 1
    missing = client.get("/api/software/search", headers=headers, params={"name": "Python", "missing": True})
    assert missing.json()["device_count"] >= 1


def test_unauthorized_software_alert_and_category(client):
    headers, agent = _enroll_agent(client)
    agent_headers = {"Authorization": f"Bearer {agent['agent_token']}"}
    client.post(
        "/agent/heartbeat",
        headers=agent_headers,
        json={"hostname": "PC-LAB-04", "os_family": "linux", "cpu_percent": 1, "ram_total_mb": 1024, "ram_used_mb": 100, "disk_total_gb": 50, "disk_used_gb": 10},
    )
    client.post("/agent/inventory", headers=agent_headers, json={"software": [{"name": "BitTorrent", "version": "1", "publisher": "Unknown"}]})
    catalog = client.get("/api/software", headers=headers).json()
    bt = next(s for s in catalog if s["name"] == "BitTorrent")
    patched = client.patch(f"/api/software/{bt['id']}", headers=headers, json={"category": "no_autorizado"})
    assert patched.status_code == 200
    client.post("/agent/inventory", headers=agent_headers, json={"software": [{"name": "BitTorrent", "version": "1", "publisher": "Unknown"}]})
    alerts = client.get("/api/alerts", headers=headers).json()
    assert any("no autorizado" in a["title"] for a in alerts)


def test_package_install_task_flow(client):
    headers, agent = _enroll_agent(client)
    agent_headers = {"Authorization": f"Bearer {agent['agent_token']}"}
    client.post(
        "/agent/heartbeat",
        headers=agent_headers,
        json={"hostname": "PC-LAB-04", "os_family": "linux", "cpu_percent": 1, "ram_total_mb": 1024, "ram_used_mb": 1, "disk_total_gb": 20, "disk_used_gb": 1},
    )
    files = {"file": ("demo.deb", io.BytesIO(b"fake-deb-content"), "application/octet-stream")}
    data = {
        "name": "DemoApp",
        "version": "1.0",
        "os_family": "linux",
        "architecture": "amd64",
        "install_command": "dpkg -i {file}",
        "notes": "paquete de prueba",
    }
    uploaded = client.post("/api/packages", headers=headers, data=data, files=files)
    assert uploaded.status_code == 201, uploaded.text
    pkg = uploaded.json()
    assert len(pkg["sha256"]) == 64
    device_id = agent["device_id"]
    job = client.post(
        "/api/installations",
        headers=headers,
        json={"package_id": pkg["id"], "target_type": "device", "target_id": device_id, "confirm": True},
    )
    assert job.status_code == 201, job.text
    _headers, other_agent = _enroll_agent(client)
    unauthorized = client.get(
        f"/agent/packages/{pkg['id']}/download",
        headers={"Authorization": f"Bearer {other_agent['agent_token']}"},
    )
    assert unauthorized.status_code == 403
    authorized = client.get(f"/agent/packages/{pkg['id']}/download", headers=agent_headers)
    assert authorized.status_code == 200
    assert authorized.content == b"fake-deb-content"
    tasks = client.get("/agent/tasks", headers=agent_headers)
    assert tasks.status_code == 200
    assert len(tasks.json()) == 1
    task = tasks.json()[0]
    assert task["type"] == "install_package"
    assert task["signature"]
    # Segunda lectura no duplica tareas pendientes nuevas
    again = client.get("/agent/tasks", headers=agent_headers).json()
    assert len(again) == 1
    result = client.post(
        "/agent/task-result",
        headers=agent_headers,
        json={"task_id": task["task_id"], "success": True, "message": "instalado"},
    )
    assert result.status_code == 200
    idem = client.post(
        "/agent/task-result",
        headers=agent_headers,
        json={"task_id": task["task_id"], "success": True, "message": "otra vez"},
    )
    assert idem.json().get("idempotent") is True
    empty = client.get("/agent/tasks", headers=agent_headers).json()
    assert empty == []
    jobs = client.get("/api/installations", headers=headers).json()
    assert jobs[0]["devices"][0]["status"] == "instalado"
    audit = client.get("/api/audit", headers=headers)
    assert audit.status_code == 200
    assert any(a["action"] == "install_create" for a in audit.json())


def test_groups_and_device_update(client):
    headers, agent = _enroll_agent(client)
    groups = client.get("/api/groups", headers=headers).json()
    lab = next(g for g in groups if g["name"] == "Laboratorio 1")
    devices = client.get("/api/devices", headers=headers).json()
    updated = client.patch(
        f"/api/devices/{devices[0]['id']}",
        headers=headers,
        json={"display_name": "PC Laboratorio 04", "group_ids": [lab["id"]], "exclude_chrome": True},
    )
    assert updated.status_code == 200
    assert "Laboratorio 1" in updated.json()["groups"]
    assert updated.json()["exclude_chrome"] is True


def test_restart_requires_confirmation(client):
    headers, _agent = _enroll_agent(client)
    device_id = client.get("/api/devices", headers=headers).json()[0]["id"]
    denied = client.post(
        f"/api/devices/{device_id}/actions",
        headers=headers,
        json={"action": "restart_agent", "confirm": False},
    )
    assert denied.status_code == 400


def test_network_discovery_collector_and_remote_support(client):
    headers = login(client)
    site = client.post(
        "/api/network/sites",
        headers=headers,
        json={
            "name": "Sede pruebas",
            "description": "Red autorizada para pruebas",
            "location": "Local",
            "cidrs": ["127.0.0.0/30"],
            "max_hosts_per_scan": 16,
        },
    )
    assert site.status_code == 201, site.text
    site_id = site.json()["id"]
    external = client.post(
        "/api/network/sites",
        headers=headers,
        json={
            "name": "No permitida",
            "cidrs": ["8.8.8.0/24"],
            "max_hosts_per_scan": 300,
        },
    )
    assert external.status_code == 422

    credential = client.post(
        f"/api/network/sites/{site_id}/credentials",
        headers=headers,
        json={
            "name": "SNMP laboratorio",
            "kind": "snmp_v3",
            "username": "tic-ro",
            "secret": "ClaveAutenticacion",
            "auth_protocol": "SHA",
            "privacy_protocol": "AES",
            "privacy_secret": "ClavePrivacidad",
        },
    )
    assert credential.status_code == 201, credential.text
    assert "secret" not in credential.json()

    created = client.post(
        f"/api/network/sites/{site_id}/collectors",
        headers=headers,
        json={"name": "Recolector local"},
    )
    assert created.status_code == 201, created.text
    collector_token = created.json()["token"]
    assert collector_token
    collector_headers = {"Authorization": f"Bearer {collector_token}"}

    heartbeat = client.post(
        "/collector/heartbeat",
        headers=collector_headers,
        json={"hostname": "collector-lab", "version": "0.1.0"},
    )
    assert heartbeat.status_code == 200
    config = client.get("/collector/config", headers=collector_headers)
    assert config.status_code == 200
    assert config.headers["cache-control"] == "no-store"
    assert config.json()["cidrs"] == ["127.0.0.0/30"]
    assert config.json()["credentials"][0]["secret"] == "ClaveAutenticacion"

    confirmation = client.post(
        "/api/network/scans",
        headers=headers,
        json={"site_id": site_id, "methods": ["tcp", "arp", "snmp"], "confirm": False},
    )
    assert confirmation.status_code == 400
    scan = client.post(
        "/api/network/scans",
        headers=headers,
        json={"site_id": site_id, "methods": ["tcp", "arp", "snmp"], "confirm": True},
    )
    assert scan.status_code == 201, scan.text
    scan_id = scan.json()["id"]
    tasks = client.get("/collector/tasks", headers=collector_headers)
    assert tasks.status_code == 200
    assert tasks.json()[0]["scan_id"] == scan_id

    result = client.post(
        f"/collector/scans/{scan_id}/results",
        headers=collector_headers,
        json={
            "devices": [
                {
                    "identity_key": "aa:bb:cc:dd:ee:ff",
                    "ip_address": "127.0.0.1",
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "hostname": "pc-remoto",
                    "vendor": "Cisco",
                    "model": "Equipo de prueba",
                    "device_type": "computador",
                    "status": "online",
                    "discovery_source": "tcp,snmp",
                    "sys_name": "pc-remoto",
                    "sys_description": "Cisco IOS test",
                    "open_ports": [22, 80, 3389],
                    "remote_services": ["ssh", "http", "rdp"],
                    "management_url": "http://127.0.0.1",
                }
            ],
            "links": [],
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["result_count"] == 1
    assert client.post(
        f"/collector/scans/{scan_id}/results",
        headers=collector_headers,
        json={"devices": []},
    ).json()["idempotent"] is True

    devices = client.get("/api/network/devices", headers=headers, params={"site_id": site_id})
    assert devices.status_code == 200
    device = devices.json()[0]
    assert device["vendor"] == "Cisco"
    assert "rdp" in device["remote_services"]

    denied = client.post(
        f"/api/network/devices/{device['id']}/remote-session",
        headers=headers,
        json={"protocol": "rdp", "confirm": False},
    )
    assert denied.status_code == 400
    rdp = client.post(
        f"/api/network/devices/{device['id']}/remote-session",
        headers=headers,
        json={"protocol": "rdp", "username": "soporte", "confirm": True},
    )
    assert rdp.status_code == 200
    assert "prompt for credentials:i:1" in rdp.text
    assert "password" not in rdp.text.lower()

    audit = client.get("/api/audit", headers=headers).json()
    assert any(row["action"] == "network_scan_create" for row in audit)
    assert any(row["action"] == "network_remote_session" for row in audit)
