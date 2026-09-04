import io

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


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
    r = client.post("/api/auth/login", json={"username": "admin", "password": "incorrecta"})
    assert r.status_code == 401


def test_login_and_me(client):
    headers = login(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "superadmin"


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
