import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { StatusBadge } from "../components/ui";

export default function DevicesPage() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");
  useEffect(() => {
    const params = {};
    if (status) params.status = status;
    api.get("/api/devices", { params }).then((r) => setRows(r.data));
  }, [status]);
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h1 className="h4 mb-0">Equipos</h1>
        <select className="form-select w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Todos</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="advertencia">Advertencia</option>
          <option value="critico">Crítico</option>
          <option value="mantenimiento">Mantenimiento</option>
          <option value="excluido">Excluido</option>
        </select>
      </div>
      <div className="table-responsive kpi p-0">
        <table className="table mb-0">
          <thead>
            <tr>
              <th>Equipo</th>
              <th>Estado</th>
              <th>SO</th>
              <th>IP</th>
              <th>Usuario</th>
              <th>CPU</th>
              <th>RAM</th>
              <th>Último contacto</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td><Link to={`/equipos/${d.id}`}>{d.display_name || d.hostname}</Link></td>
                <td><StatusBadge status={d.status} /></td>
                <td>{d.os_name} {d.os_version}</td>
                <td>{d.ip_address}</td>
                <td>{d.logged_user}</td>
                <td>{d.cpu_percent?.toFixed(0)}%</td>
                <td>{d.ram_used_mb}/{d.ram_total_mb} MB</td>
                <td>{d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
