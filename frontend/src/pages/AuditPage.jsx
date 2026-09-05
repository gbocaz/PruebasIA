import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function AuditPage() {
  const { canAudit } = useAuth();
  const [rows, setRows] = useState([]);
  useEffect(() => {
    if (canAudit) api.get("/api/audit").then((r) => setRows(r.data));
  }, [canAudit]);
  if (!canAudit) return <div>Sin permiso de auditoría.</div>;
  return (
    <div>
      <h1 className="h4">Auditoría</h1>
      <table className="table small">
        <thead><tr><th>Fecha</th><th>Usuario</th><th>IP</th><th>Acción</th><th>Objetivo</th><th>Resultado</th></tr></thead>
        <tbody>
          {rows.map((a) => (
            <tr key={a.id}>
              <td>{new Date(a.created_at).toLocaleString()}</td>
              <td>{a.username}</td>
              <td>{a.ip_address}</td>
              <td>{a.action}</td>
              <td>{a.target_type} {a.target_id}</td>
              <td>{a.result}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
