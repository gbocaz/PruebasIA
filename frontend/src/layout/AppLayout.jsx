import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useState } from "react";
import api from "../api/client";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/equipos", label: "Equipos" },
  { to: "/despliegue-agentes", label: "Desplegar agentes" },
  { to: "/red", label: "Red" },
  { to: "/software", label: "Software" },
  { to: "/paquetes", label: "Paquetes" },
  { to: "/instalaciones", label: "Instalaciones" },
  { to: "/grupos", label: "Grupos" },
  { to: "/alertas", label: "Alertas" },
  { to: "/usuarios", label: "Usuarios" },
  { to: "/auditoria", label: "Auditoría" },
  { to: "/configuracion", label: "Configuración" },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);

  async function search(e) {
    e.preventDefault();
    if (!q.trim()) return;
    const { data } = await api.get("/api/search", { params: { q } });
    setResults(data);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">TIC Control AI</div>
        <div className="muted">Administración de equipos</div>
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.to === "/"}>
            {l.label}
          </NavLink>
        ))}
        <div className="coming-soon px-3 mt-3 small">IA · Archivos · Informes avanzados</div>
        <div className="mt-auto p-3 small">{user?.username}<br /><span className="text-white-50">{user?.role}</span></div>
      </aside>
      <div className="content">
        <div className="topbar">
          <form className="flex-grow-1" onSubmit={search}>
            <input
              className="form-control"
              placeholder="Buscar equipo, IP, MAC, programa o usuario"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </form>
          <button className="btn btn-outline-secondary" onClick={async () => { await logout(); navigate("/login"); }}>
            Salir
          </button>
        </div>
        {results && (
          <div className="page pb-0">
            <div className="kpi">
              <div className="d-flex justify-content-between">
                <strong>Resultados</strong>
                <button className="btn btn-sm btn-link" onClick={() => setResults(null)}>cerrar</button>
              </div>
              {results.devices.map((d) => (
                <div key={d.id}>
                  <a href={`/equipos/${d.id}`}>{d.hostname}</a> · {d.ip_address} · {d.status}
                </div>
              ))}
              {results.software.map((s) => (
                <div key={s.id}>{s.name} · {s.publisher}</div>
              ))}
            </div>
          </div>
        )}
        <div className="page">{children}</div>
      </div>
    </div>
  );
}
