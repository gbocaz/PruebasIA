import ipaddress
import json
from datetime import timedelta
from urllib.parse import quote

from fastapi import HTTPException, status

from app.models.network import NetworkCollector, NetworkDevice, NetworkScanJob, NetworkSite
from app.schemas.network import NetworkDeviceOut, ScanOut
from app.security.tokens import as_utc, utcnow


def validate_private_cidrs(cidrs: list[str], max_hosts: int) -> list[str]:
    normalized: list[str] = []
    total = 0
    for raw in cidrs:
        try:
            network = ipaddress.ip_network(raw, strict=False)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"CIDR inválido: {raw}") from exc
        if not (network.is_private or network.is_loopback or network.is_link_local):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Solo se permiten redes privadas, loopback o link-local: {network}",
            )
        usable = max(1, network.num_addresses - (2 if network.version == 4 and network.prefixlen < 31 else 0))
        total += usable
        if total > max_hosts:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Los CIDR contienen {total} hosts; el límite configurado es {max_hosts}",
            )
        normalized.append(str(network))
    return normalized


def collector_online(collector: NetworkCollector) -> bool:
    last_seen = as_utc(collector.last_seen_at)
    return bool(last_seen and not collector.revoked and utcnow() - last_seen < timedelta(minutes=3))


def site_to_out(site: NetworkSite, device_count: int = 0) -> dict:
    collectors = site.collectors
    return {
        "id": site.id,
        "name": site.name,
        "description": site.description,
        "location": site.location,
        "cidrs": json.loads(site.cidrs_json or "[]"),
        "enabled": site.enabled,
        "max_hosts_per_scan": site.max_hosts_per_scan,
        "collector_count": len(collectors),
        "collectors_online": sum(1 for item in collectors if collector_online(item)),
        "device_count": device_count,
        "created_at": site.created_at,
    }


def scan_to_out(scan: NetworkScanJob) -> ScanOut:
    return ScanOut(
        id=scan.id,
        site_id=scan.site_id,
        collector_id=scan.collector_id,
        status=scan.status,
        methods=json.loads(scan.methods_json or "[]"),
        requested_at=scan.requested_at,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        result_count=scan.result_count,
        error=scan.error,
    )


def device_to_out(device: NetworkDevice) -> NetworkDeviceOut:
    return NetworkDeviceOut(
        id=device.id,
        site_id=device.site_id,
        ip_address=device.ip_address,
        mac_address=device.mac_address,
        hostname=device.hostname,
        vendor=device.vendor,
        model=device.model,
        serial_number=device.serial_number,
        device_type=device.device_type,
        os_name=device.os_name,
        status=device.status,
        discovery_source=device.discovery_source,
        sys_name=device.sys_name,
        sys_description=device.sys_description,
        sys_object_id=device.sys_object_id,
        open_ports=json.loads(device.open_ports_json or "[]"),
        remote_services=json.loads(device.remote_services_json or "[]"),
        management_url=device.management_url,
        switch_port=device.switch_port,
        vlan=device.vlan,
        ssid=device.ssid,
        first_seen_at=device.first_seen_at,
        last_seen_at=device.last_seen_at,
    )


def remote_target(device: NetworkDevice, protocol: str, username: str) -> dict:
    services = set(json.loads(device.remote_services_json or "[]"))
    if protocol not in services:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{protocol.upper()} no fue detectado como servicio disponible en este equipo",
        )
    ip = device.ip_address
    safe_user = quote(username, safe="")
    if protocol == "rdp":
        # No incluye credenciales. El sistema operativo solicitará autenticación.
        body = "\r\n".join(
            [
                f"full address:s:{ip}",
                f"username:s:{username}" if username else "username:s:",
                "prompt for credentials:i:1",
                "authentication level:i:2",
                "enablecredsspsupport:i:1",
                "redirectclipboard:i:0",
                "redirectdrives:i:0",
            ]
        )
        return {"kind": "file", "filename": f"{device.hostname or ip}.rdp", "content": body + "\r\n"}
    if protocol == "ssh":
        authority = f"{safe_user}@" if safe_user else ""
        return {"kind": "url", "url": f"ssh://{authority}{ip}"}
    if protocol == "vnc":
        return {"kind": "url", "url": f"vnc://{ip}"}
    url = device.management_url
    if not url or not url.startswith(f"{protocol}://"):
        url = f"{protocol}://{ip}"
    return {"kind": "url", "url": url}
