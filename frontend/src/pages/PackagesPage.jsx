import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ConfirmButton } from "../components/ui";

export default function PackagesPage() {
  const { canWrite } = useAuth();
  const [rows, setRows] = useState([]);
  const [devices, setDevices] = useState([]);
  const [groups, setGroups] = useState([]);
  const [form, setForm] = useState({ name: "", version: "", os_family: "linux", architecture: "amd64", install_command: "", notes: "", file: null });
  const [target, setTarget] = useState({ type: "device", id: "" });
  const [msg, setMsg] = useState("");

  async function load() {
    const [p, d, g] = await Promise.all([api.get("/api/packages"), api.get("/api/devices"), api.get("/api/groups")]);
    setRows(p.data);
    setDevices(d.data);
    setGroups(g.data);
  }
  useEffect(() => { load(); }, []);

  async function upload(e) {
    e.preventDefault();
    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => { if (k !== "file") fd.append(k, v); });
    fd.append("file", form.file);
    await api.post("/api/packages", fd);
    setMsg("Paquete cargado y hasheado");
    load();
  }

  async function install(pkg) {
    await api.post("/api/installations", {
      package_id: pkg.id,
      target_type: target.type,
      target_id: target.type === "all" ? "" : target.id,
      confirm: true,
    });
    setMsg("Instalación encolada");
  }

  return (
    <div>
      <h1 className="h4">Paquetes</h1>
      {msg && <div className="alert alert-info">{msg}</div>}
      {canWrite && (
        <form className="kpi mb-4" onSubmit={upload}>
          <div className="row g-2">
            <div className="col-md-3"><input className="form-control" placeholder="Nombre" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="col-md-2"><input className="form-control" placeholder="Versión" required value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} /></div>
            <div className="col-md-2">
              <select className="form-select" value={form.os_family} onChange={(e) => setForm({ ...form, os_family: e.target.value })}>
                <option value="linux">Linux</option>
                <option value="windows">Windows</option>
              </select>
            </div>
            <div className="col-md-2"><input className="form-control" placeholder="Arquitectura" value={form.architecture} onChange={(e) => setForm({ ...form, architecture: e.target.value })} /></div>
            <div className="col-md-3"><input className="form-control" type="file" required onChange={(e) => setForm({ ...form, file: e.target.files[0] })} /></div>
            <div className="col-12"><input className="form-control" placeholder="Comando aprobado, use {file} como ruta local" required value={form.install_command} onChange={(e) => setForm({ ...form, install_command: e.target.value })} /></div>
            <div className="col-12"><button className="btn btn-primary">Cargar paquete</button></div>
          </div>
        </form>
      )}
      <div className="kpi mb-3">
        <div className="small text-secondary mb-2">Destino de instalación</div>
        <div className="d-flex gap-2 flex-wrap">
          <select className="form-select w-auto" value={target.type} onChange={(e) => setTarget({ ...target, type: e.target.value })}>
            <option value="device">Equipo individual</option>
            <option value="group">Grupo</option>
            <option value="all">Todos</option>
          </select>
          {target.type === "device" && (
            <select className="form-select w-auto" value={target.id} onChange={(e) => setTarget({ ...target, id: e.target.value })}>
              <option value="">Seleccione equipo</option>
              {devices.map((d) => <option key={d.id} value={d.id}>{d.hostname}</option>)}
            </select>
          )}
          {target.type === "group" && (
            <select className="form-select w-auto" value={target.id} onChange={(e) => setTarget({ ...target, id: e.target.value })}>
              <option value="">Seleccione grupo</option>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          )}
        </div>
      </div>
      <table className="table">
        <thead><tr><th>Nombre</th><th>SO</th><th>SHA-256</th><th>Comando</th><th></th></tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}>
              <td>{p.name} {p.version}</td>
              <td>{p.os_family}/{p.architecture}</td>
              <td className="small">{p.sha256.slice(0, 16)}…</td>
              <td className="small">{p.install_command}</td>
              <td>
                {canWrite && (
                  <ConfirmButton className="btn btn-sm btn-outline-primary" message="¿Instalar este paquete aprobado en el destino seleccionado?" onConfirm={() => install(p)}>
                    Instalar
                  </ConfirmButton>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
