import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../api/client";
import { Bar, ConfirmButton, StatusBadge } from "../components/ui";
import { useAuth } from "../auth/AuthContext";

const TABS = ["Resumen", "Software", "Red", "Eventos", "Historial", "Acciones"];

export default function DeviceDetailPage() {
  const { id } = useParams();
  const { canWrite, canSupport } = useAuth();
  const [tab, setTab] = useState("Resumen");
  const [device, setDevice] = useState(null);
  const [software, setSoftware] = useState([]);
  const [ifaces, setIfaces] = useState([]);
  const [events, setEvents] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [msg, setMsg] = useState("");

  async function load() {
    const [d, s, i, e, m] = await Promise.all([
      api.get(`/api/devices/${id}`),
      api.get(`/api/devices/${id}/software`),
      api.get(`/api/devices/${id}/interfaces`),
      api.get(`/api/devices/${id}/events`),
      api.get(`/api/devices/${id}/metrics`, { params: { hours: 24 } }),
    ]);
    setDevice(d.data);
    setSoftware(s.data);
    setIfaces(i.data);
    setEvents(e.data);
    setMetrics(m.data);
  }

  useEffect(() => {
    load();
  }, [id]);

  async function action(name, confirm = false) {
    const { data } = await api.post(`/api/devices/${id}/actions`, { action: name, confirm });
    setMsg(`Tarea ${data.task_id} en cola`);
  }

  if (!device) return <div>Cargando…</div>;
  return (
    <div>
      <h1 className="h4">{device.display_name || device.hostname}</h1>
      <div className="mb-3">
        <StatusBadge status={device.status} /> {device.os_name} {device.os_version} · {device.ip_address} · {device.mac_address} · {device.logged_user}
      </div>
      <div className="d-flex gap-2 mb-3 flex-wrap">
        {TABS.map((t) => (
          <button key={t} className={`btn btn-sm ${tab === t ? "btn-primary" : "btn-outline-secondary"}`} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {msg && <div className="alert alert-info">{msg}</div>}
      {tab === "Resumen" && (
        <div className="row g-3">
          <div className="col-md-4 kpi">
            <div className="small text-secondary">CPU {device.cpu_percent.toFixed(0)}%</div>
            <Bar value={device.cpu_percent} />
            <div className="small mt-2">{device.cpu_model}</div>
          </div>
          <div className="col-md-4 kpi">
            <div className="small text-secondary">RAM {device.ram_used_mb}/{device.ram_total_mb} MB</div>
            <Bar value={device.ram_used_mb} max={device.ram_total_mb || 1} suffix="MB" />
          </div>
          <div className="col-md-4 kpi">
            <div className="small text-secondary">Disco {device.disk_used_gb.toFixed(1)}/{device.disk_total_gb.toFixed(1)} GB</div>
            <Bar value={device.disk_used_gb} max={device.disk_total_gb || 1} suffix="GB" />
          </div>
          <div className="col-12 kpi small">
            Grupos: {device.groups.join(", ") || "ninguno"} · Agente {device.agent_version} · Último contacto {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : "—"}
          </div>
        </div>
      )}
      {tab === "Software" && (
        <table className="table">
          <thead><tr><th>Programa</th><th>Versión</th><th>Editor</th><th>Categoría</th><th>Detectado</th></tr></thead>
          <tbody>
            {software.map((s) => (
              <tr key={s.software_id}><td>{s.name}</td><td>{s.version}</td><td>{s.publisher}</td><td>{s.category}</td><td>{new Date(s.detected_at).toLocaleDateString()}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {tab === "Red" && (
        <table className="table">
          <thead><tr><th>Interfaz</th><th>MAC</th><th>IPv4</th><th>Velocidad</th><th>Enviado</th><th>Recibido</th></tr></thead>
          <tbody>
            {ifaces.map((i) => (
              <tr key={i.name + i.mac}><td>{i.name}</td><td>{i.mac}</td><td>{i.ipv4}</td><td>{i.speed_mbps} Mbps</td><td>{i.bytes_sent}</td><td>{i.bytes_recv}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {tab === "Eventos" && events.map((e) => (
        <div key={e.id} className="small mb-1">{new Date(e.created_at).toLocaleString()} · {e.type} · {e.message}</div>
      ))}
      {tab === "Historial" && (
        <div className="kpi">
          {metrics.map((m) => (
            <div key={m.collected_at} className="small">{new Date(m.collected_at).toLocaleString()} · CPU {m.cpu_percent.toFixed(0)}% · RAM {m.ram_used_mb} MB · disco {m.disk_used_gb.toFixed(1)} GB</div>
          ))}
          {metrics.length === 0 && <div className="text-secondary">Sin muestras todavía.</div>}
        </div>
      )}
      {tab === "Acciones" && canSupport && (
        <div className="d-flex gap-2">
          <button className="btn btn-outline-primary" onClick={() => action("collect_inventory")}>Actualizar inventario</button>
          {canWrite && (
            <ConfirmButton className="btn btn-outline-danger" message="¿Reiniciar el servicio del agente en este equipo?" onConfirm={() => action("restart_agent", true)}>
              Reiniciar servicio del agente
            </ConfirmButton>
          )}
        </div>
      )}
    </div>
  );
}
