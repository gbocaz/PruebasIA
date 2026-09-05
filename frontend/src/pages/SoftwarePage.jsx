import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

const CATS = ["autorizado", "no_autorizado", "obligatorio", "opcional", "ignorar"];

export default function SoftwarePage() {
  const { canWrite } = useAuth();
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [presence, setPresence] = useState(null);

  function load() {
    api.get("/api/software", { params: q ? { q } : {} }).then((r) => setRows(r.data));
  }
  useEffect(() => { load(); }, []);

  async function setCat(id, category) {
    await api.patch(`/api/software/${id}`, { category });
    load();
  }

  async function ask(missing) {
    const { data } = await api.get("/api/software/search", { params: { name: q, missing } });
    setPresence(data);
  }

  return (
    <div>
      <h1 className="h4">Software</h1>
      <div className="d-flex gap-2 mb-3">
        <input className="form-control" placeholder="Chrome, Python, LibreOffice…" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn btn-primary" onClick={load}>Filtrar</button>
        <button className="btn btn-outline-primary" onClick={() => ask(false)}>¿Dónde está?</button>
        <button className="btn btn-outline-secondary" onClick={() => ask(true)}>¿Quién no lo tiene?</button>
      </div>
      {presence && (
        <div className="kpi mb-3">
          <strong>{presence.missing ? "Equipos sin" : "Equipos con"} {presence.query}: {presence.device_count}</strong>
          <div>{presence.devices.map((d) => d.hostname).join(", ") || "ninguno"}</div>
        </div>
      )}
      <table className="table">
        <thead><tr><th>Programa</th><th>Editor</th><th>Equipos</th><th>Categoría</th></tr></thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td>{s.publisher}</td>
              <td>{s.install_count}</td>
              <td>
                {canWrite ? (
                  <select className="form-select form-select-sm" value={s.category} onChange={(e) => setCat(s.id, e.target.value)}>
                    {CATS.map((c) => <option key={c}>{c}</option>)}
                  </select>
                ) : s.category}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
