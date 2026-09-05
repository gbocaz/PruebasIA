import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { Bar, StatusBadge } from "../components/ui";

export default function DashboardPage() {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get("/api/dashboard").then((r) => setData(r.data));
  }, []);
  if (!data) return <div>Cargando…</div>;
  const t = data.totals;
  const cards = [
    ["Equipos totales", t.devices],
    ["Online", t.online],
    ["Offline", t.offline],
    ["Alertas", t.alerts],
    ["Programas detectados", t.programs],
    ["Disponibilidad %", t.available_pct],
  ];
  return (
    <div>
      <h1 className="h4 mb-3">Dashboard</h1>
      <div className="row g-3 mb-4">
        {cards.map(([label, n]) => (
          <div className="col-6 col-lg-2" key={label}>
            <div className="kpi">
              <div className="text-secondary small">{label}</div>
              <div className="n">{n}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="row g-3">
        <div className="col-lg-6">
          <div className="kpi">
            <h2 className="h6">Uso de recursos (valores visibles)</h2>
            {data.top_cpu.map((d) => (
              <div key={d.id} className="mb-2">
                <div className="d-flex justify-content-between small">
                  <Link to={`/equipos/${d.id}`}>{d.hostname}</Link>
                  <StatusBadge status={d.status} />
                </div>
                <div className="small text-secondary">CPU {d.cpu_percent.toFixed(0)}%</div>
                <Bar value={d.cpu_percent} />
              </div>
            ))}
            {data.top_cpu.length === 0 && <div className="text-secondary">Sin equipos todavía.</div>}
          </div>
        </div>
        <div className="col-lg-6">
          <div className="kpi mb-3">
            <h2 className="h6">Software más instalado</h2>
            {data.top_software.map((s) => (
              <div key={s.name} className="d-flex justify-content-between">
                <span>{s.name}</span>
                <strong>{s.count}</strong>
              </div>
            ))}
            {data.top_software.length === 0 && <div className="text-secondary">Sin inventario.</div>}
          </div>
          <div className="kpi">
            <h2 className="h6">Alertas recientes</h2>
            {data.recent_alerts.map((a) => (
              <div key={a.id} className="small mb-1">
                <span className={`badge me-2 badge-${a.level === "critico" ? "critico" : a.level === "advertencia" ? "advertencia" : "offline"}`}>{a.level}</span>
                {a.title}
              </div>
            ))}
            {data.recent_alerts.length === 0 && <div className="text-secondary">Sin alertas.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
