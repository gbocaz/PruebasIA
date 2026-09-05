import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/ui";

const labels = {
  rdp: "Descargar conexión RDP",
  vnc: "Abrir cliente VNC",
  ssh: "Abrir cliente SSH",
  http: "Abrir administración HTTP",
  https: "Abrir administración HTTPS",
};

export default function NetworkDevicePage() {
  const { id } = useParams();
  const { canSupport } = useAuth();
  const [device, setDevice] = useState(null);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");

  useEffect(() => {
    api.get(`/api/network/devices/${id}`).then((response) => setDevice(response.data));
  }, [id]);

  async function connect(protocol) {
    if (!window.confirm(`¿Iniciar una conexión ${protocol.toUpperCase()} auditada hacia ${device.ip_address}?`)) return;
    setError("");
    try {
      if (protocol === "rdp") {
        const response = await api.post(
          `/api/network/devices/${id}/remote-session`,
          { protocol, username, confirm: true },
          { responseType: "blob" },
        );
        const url = URL.createObjectURL(response.data);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${device.hostname || device.ip_address}.rdp`;
        anchor.click();
        URL.revokeObjectURL(url);
        return;
      }
      const { data } = await api.post(`/api/network/devices/${id}/remote-session`, {
        protocol,
        username,
        confirm: true,
      });
      if (data.url.startsWith("http")) {
        window.open(data.url, "_blank", "noopener,noreferrer");
      } else {
        window.location.href = data.url;
      }
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "No se pudo iniciar la conexión.");
    }
  }

  if (!device) return <div>Cargando…</div>;
  return (
    <div>
      <Link to="/red" className="small">← Volver a Red</Link>
      <div className="d-flex justify-content-between align-items-start mt-2 mb-3">
        <div>
          <h1 className="h4 mb-1">{device.hostname || device.sys_name || device.ip_address}</h1>
          <StatusBadge status={device.status} /> <span className="ms-2">{device.vendor} {device.model}</span>
        </div>
        <span className="badge text-bg-light">{device.device_type}</span>
      </div>
      {error && <div className="alert alert-danger">{error}</div>}
      <div className="row g-3 mb-3">
        <div className="col-md-6">
          <div className="kpi h-100">
            <h2 className="h6">Identificación</h2>
            <dl className="row small mb-0">
              <dt className="col-4">IP</dt><dd className="col-8">{device.ip_address}</dd>
              <dt className="col-4">MAC</dt><dd className="col-8">{device.mac_address || "No disponible"}</dd>
              <dt className="col-4">Marca</dt><dd className="col-8">{device.vendor}</dd>
              <dt className="col-4">Modelo</dt><dd className="col-8">{device.model || "No publicado"}</dd>
              <dt className="col-4">Serie</dt><dd className="col-8">{device.serial_number || "No publicada"}</dd>
              <dt className="col-4">SO</dt><dd className="col-8">{device.os_name || "No identificado"}</dd>
            </dl>
          </div>
        </div>
        <div className="col-md-6">
          <div className="kpi h-100">
            <h2 className="h6">Red</h2>
            <dl className="row small mb-0">
              <dt className="col-4">Puertos abiertos</dt><dd className="col-8">{device.open_ports.join(", ") || "Ninguno detectado"}</dd>
              <dt className="col-4">Servicios</dt><dd className="col-8">{device.remote_services.join(", ") || "Ninguno"}</dd>
              <dt className="col-4">Switch/puerto</dt><dd className="col-8">{device.switch_port || "No disponible"}</dd>
              <dt className="col-4">VLAN</dt><dd className="col-8">{device.vlan || "No disponible"}</dd>
              <dt className="col-4">SSID</dt><dd className="col-8">{device.ssid || "No disponible"}</dd>
              <dt className="col-4">Descubierto por</dt><dd className="col-8">{device.discovery_source}</dd>
            </dl>
          </div>
        </div>
      </div>
      <div className="kpi mb-3">
        <h2 className="h6">Información SNMP</h2>
        <div className="small"><strong>sysName:</strong> {device.sys_name || "—"}</div>
        <div className="small"><strong>sysObjectID:</strong> {device.sys_object_id || "—"}</div>
        <div className="small text-secondary mt-1">{device.sys_description || "El equipo no publicó descripción SNMP."}</div>
      </div>
      <div className="kpi">
        <h2 className="h6">Soporte remoto autorizado</h2>
        <p className="small text-secondary">
          TIC Control no instala ni evade acceso. Estos botones solo abren servicios ya habilitados.
          El sistema operativo o el equipo solicitará sus propias credenciales; TIC Control no las guarda.
        </p>
        {canSupport && device.remote_services.length > 0 ? (
          <>
            {(device.remote_services.includes("rdp") || device.remote_services.includes("ssh")) && (
              <input className="form-control form-control-sm mb-2" style={{ maxWidth: 320 }}
                placeholder="Usuario opcional (sin contraseña)" value={username}
                onChange={(event) => setUsername(event.target.value)} />
            )}
            <div className="d-flex gap-2 flex-wrap">
              {device.remote_services.map((protocol) => (
                <button className="btn btn-outline-primary" key={protocol} onClick={() => connect(protocol)}>
                  {labels[protocol] || `Abrir ${protocol}`}
                </button>
              ))}
            </div>
          </>
        ) : (
          <div className="text-secondary">No se detectaron protocolos de soporte remoto habilitados.</div>
        )}
      </div>
    </div>
  );
}
