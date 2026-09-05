import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function GroupsPage() {
  const { canWrite } = useAuth();
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  async function load() {
    setRows((await api.get("/api/groups")).data);
  }
  useEffect(() => { load(); }, []);
  return (
    <div>
      <h1 className="h4">Grupos</h1>
      {canWrite && (
        <form className="d-flex gap-2 mb-3" onSubmit={async (e) => { e.preventDefault(); await api.post("/api/groups", { name, description }); setName(""); setDescription(""); load(); }}>
          <input className="form-control" placeholder="Nombre" value={name} onChange={(e) => setName(e.target.value)} />
          <input className="form-control" placeholder="Descripción" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button className="btn btn-primary">Crear</button>
        </form>
      )}
      <table className="table">
        <thead><tr><th>Grupo</th><th>Descripción</th><th>Equipos</th></tr></thead>
        <tbody>
          {rows.map((g) => (
            <tr key={g.id}><td>{g.name}</td><td>{g.description}</td><td>{g.device_count}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
