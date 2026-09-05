import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

const ROLES = ["superadmin", "administrador_tic", "soporte", "visualizador", "directivo"];

export default function UsersPage() {
  const { canUsers } = useAuth();
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState({ username: "", email: "", full_name: "", password: "", role: "soporte" });
  async function load() {
    setRows((await api.get("/api/users")).data);
  }
  useEffect(() => { load(); }, []);
  if (!canUsers) return <div>Solo el superadministrador gestiona usuarios.</div>;
  return (
    <div>
      <h1 className="h4">Usuarios</h1>
      <form className="row g-2 mb-3" onSubmit={async (e) => { e.preventDefault(); await api.post("/api/users", form); load(); }}>
        <div className="col-md-2"><input className="form-control" placeholder="Usuario" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
        <div className="col-md-3"><input className="form-control" placeholder="Correo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
        <div className="col-md-2"><input className="form-control" placeholder="Nombre" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></div>
        <div className="col-md-2"><input className="form-control" type="password" placeholder="Contraseña" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
        <div className="col-md-2">
          <select className="form-select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLES.map((r) => <option key={r}>{r}</option>)}
          </select>
        </div>
        <div className="col-md-1"><button className="btn btn-primary w-100">Alta</button></div>
      </form>
      <table className="table">
        <thead><tr><th>Usuario</th><th>Rol</th><th>Activo</th><th>2FA</th></tr></thead>
        <tbody>
          {rows.map((u) => (
            <tr key={u.id}><td>{u.username}</td><td>{u.role}</td><td>{u.is_active ? "sí" : "no"}</td><td>{u.totp_enabled ? "sí" : "no"}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
