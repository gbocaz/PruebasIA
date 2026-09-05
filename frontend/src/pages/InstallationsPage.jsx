import { useEffect, useState } from "react";
import api from "../api/client";

export default function InstallationsPage() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.get("/api/installations").then((r) => setRows(r.data));
  }, []);
  return (
    <div>
      <h1 className="h4">Instalaciones</h1>
      {rows.map((j) => (
        <div className="kpi mb-2" key={j.id}>
          <strong>{j.package_name} {j.package_version}</strong> · {j.target_type} · {new Date(j.created_at).toLocaleString()}
          <div className="small">
            {j.devices.map((d) => (
              <span key={d.device_id} className="me-3">{d.status}{d.message ? ` (${d.message})` : ""}</span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
