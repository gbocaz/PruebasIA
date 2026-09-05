import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function SettingsPage() {
  const { canWrite } = useAuth();
  const [tokens, setTokens] = useState([]);
  const [plain, setPlain] = useState("");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  useEffect(() => {
    if (canWrite) api.get("/api/agents/enrollment-tokens").then((r) => setTokens(r.data));
  }, [canWrite]);
  return (
    <div>
      <h1 className="h4">Configuración</h1>
      <div className="kpi mb-3">
        <h2 className="h6">Cambiar contraseña</h2>
        <form className="d-flex gap-2" onSubmit={async (e) => { e.preventDefault(); await api.post("/api/auth/change-password", pw); alert("Contraseña actualizada"); }}>
          <input className="form-control" type="password" placeholder="Actual" value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} />
          <input className="form-control" type="password" placeholder="Nueva (mín. 10)" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} />
          <button className="btn btn-outline-primary">Guardar</button>
        </form>
      </div>
      {canWrite && (
        <div className="kpi">
          <h2 className="h6">Tokens de enrolamiento de agentes</h2>
          <button className="btn btn-primary mb-2" onClick={async () => {
            const { data } = await api.post("/api/agents/enrollment-tokens", { label: "lote", max_uses: 50, expires_hours: 72 });
            setPlain(data.token);
            setTokens((await api.get("/api/agents/enrollment-tokens")).data);
          }}>Generar token</button>
          {plain && <div className="alert alert-warning">Copie ahora el token (solo se muestra una vez): <code>{plain}</code></div>}
          <table className="table small">
            <thead><tr><th>Etiqueta</th><th>Prefijo</th><th>Usos</th><th>Caduca</th></tr></thead>
            <tbody>
              {tokens.map((t) => (
                <tr key={t.id}><td>{t.label}</td><td>{t.token_prefix}</td><td>{t.use_count}/{t.max_uses}</td><td>{t.expires_at ? new Date(t.expires_at).toLocaleString() : "—"}</td></tr>
              ))}
            </tbody>
          </table>
          <button className="btn btn-outline-secondary" onClick={async () => {
            const res = await api.get("/api/reports/inventory.csv", { responseType: "blob" });
            const url = URL.createObjectURL(res.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = "inventario.csv";
            a.click();
          }}>Descargar inventario CSV</button>
        </div>
      )}
    </div>
  );
}
