import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function AlertsPage() {
  const { canSupport } = useAuth();
  const [rows, setRows] = useState([]);
  async function load() {
    setRows((await api.get("/api/alerts", { params: { acknowledged: false } })).data);
  }
  useEffect(() => { load(); }, []);
  return (
    <div>
      <h1 className="h4">Alertas</h1>
      {rows.map((a) => (
        <div className="kpi mb-2 d-flex justify-content-between" key={a.id}>
          <div>
            <span className="badge text-bg-secondary me-2">{a.level}</span>
            <strong>{a.title}</strong>
            <div className="small text-secondary">{a.message}</div>
          </div>
          {canSupport && <button className="btn btn-sm btn-outline-primary" onClick={async () => { await api.post(`/api/alerts/${a.id}/ack`); load(); }}>Reconocer</button>}
        </div>
      ))}
      {rows.length === 0 && <div className="text-secondary">No hay alertas abiertas.</div>}
    </div>
  );
}
