import { useEffect, useMemo, useState } from "react";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";

function errorText(error) {
  return error.response?.data?.detail || "No se pudo completar la operación.";
}

export default function AgentDeploymentPage() {
  const { canWrite } = useAuth();
  const [releases, setReleases] = useState([]);
  const [groups, setGroups] = useState([]);
  const [networkDevices, setNetworkDevices] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [kit, setKit] = useState(null);
  const [upload, setUpload] = useState({
    version: "",
    os_family: "windows",
    architecture: "amd64",
    notes: "",
    file: null,
  });
  const [kitForm, setKitForm] = useState({
    release_id: "",
    label: "",
    public_server_url: window.location.origin,
    group_id: "",
    max_uses: 1,
    expires_hours: 24,
  });

  async function load() {
    const [releaseResponse, groupResponse, networkResponse] = await Promise.all([
      api.get("/api/agent-deployment/releases"),
      api.get("/api/groups"),
      api.get("/api/network/devices"),
    ]);
    setReleases(releaseResponse.data);
    setGroups(groupResponse.data);
    setNetworkDevices(networkResponse.data);
    if (!kitForm.release_id && releaseResponse.data.length) {
      setKitForm((current) => ({ ...current, release_id: releaseResponse.data[0].id }));
    }
  }

  useEffect(() => {
    load().catch((requestError) => setError(errorText(requestError)));
  }, []);

  const managed = useMemo(
    () => networkDevices.filter((device) => device.managed_device_id).length,
    [networkDevices],
  );

  async function uploadRelease(event) {
    event.preventDefault();
    setError("");
    const form = new FormData();
    form.append("version", upload.version);
    form.append("os_family", upload.os_family);
    form.append("architecture", upload.architecture);
    form.append("notes", upload.notes);
    form.append("file", upload.file);
    try {
      const { data } = await api.post("/api/agent-deployment/releases", form);
      setMessage(`Agente ${data.version} cargado. SHA-256: ${data.sha256}`);
      setKitForm({ ...kitForm, release_id: data.id });
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  }

  async function createKit(event) {
    event.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/api/agent-deployment/kits", {
        ...kitForm,
        group_id: kitForm.group_id || null,
        max_uses: Number(kitForm.max_uses),
        expires_hours: Number(kitForm.expires_hours),
      });
      setKit(data);
      setMessage("Kit generado. Descárguelo ahora; el token no volverá a mostrarse.");
    } catch (requestError) {
      setError(errorText(requestError));
    }
  }

  function downloadScript() {
    const blob = new Blob([kit.install_script], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = kit.filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (!canWrite) {
    return <div>Solo SUPERADMIN o ADMINISTRADOR TIC puede preparar instaladores del agente.</div>;
  }

  return (
    <div>
      <h1 className="h4 mb-1">Despliegue de agentes</h1>
      <p className="text-secondary">
        Este módulo está separado de Software. Los paquetes de aquí instalan únicamente el agente TIC Control autorizado.
      </p>
      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-info">{message}</div>}

      <div className="row g-3 mb-4">
        <div className="col-md-4"><div className="kpi"><div className="small text-secondary">Detectados en red</div><div className="n">{networkDevices.length}</div></div></div>
        <div className="col-md-4"><div className="kpi"><div className="small text-secondary">Con agente vinculado</div><div className="n">{managed}</div></div></div>
        <div className="col-md-4"><div className="kpi"><div className="small text-secondary">Sin agente</div><div className="n">{networkDevices.length - managed}</div></div></div>
      </div>

      <div className="alert alert-warning">
        El agente no ofrece comandos arbitrarios ni acceso oculto. Inventario, instalaciones aprobadas,
        actualizaciones y soporte remoto requieren permisos, confirmación y auditoría.
      </div>

      <div className="row g-3">
        <div className="col-lg-6">
          <form className="kpi h-100" onSubmit={uploadRelease}>
            <h2 className="h6">1. Cargar binario aprobado del agente</h2>
            <div className="row g-2">
              <div className="col-md-4">
                <input className="form-control" required placeholder="Versión, ej. 0.2.0"
                  value={upload.version} onChange={(event) => setUpload({ ...upload, version: event.target.value })} />
              </div>
              <div className="col-md-4">
                <select className="form-select" value={upload.os_family}
                  onChange={(event) => setUpload({ ...upload, os_family: event.target.value })}>
                  <option value="windows">Windows</option>
                  <option value="linux">Linux</option>
                </select>
              </div>
              <div className="col-md-4">
                <select className="form-select" value={upload.architecture}
                  onChange={(event) => setUpload({ ...upload, architecture: event.target.value })}>
                  <option value="amd64">amd64</option>
                  <option value="arm64">arm64</option>
                  <option value="386">386</option>
                </select>
              </div>
              <div className="col-12">
                <input type="file" className="form-control" required
                  onChange={(event) => setUpload({ ...upload, file: event.target.files[0] })} />
              </div>
              <div className="col-12">
                <input className="form-control" placeholder="Notas de versión" value={upload.notes}
                  onChange={(event) => setUpload({ ...upload, notes: event.target.value })} />
              </div>
              <div className="col-12">
                <button className="btn btn-primary">Cargar y calcular SHA-256</button>
              </div>
            </div>
          </form>
        </div>

        <div className="col-lg-6">
          <form className="kpi h-100" onSubmit={createKit}>
            <h2 className="h6">2. Generar kit de instalación</h2>
            <select className="form-select mb-2" required value={kitForm.release_id}
              onChange={(event) => setKitForm({ ...kitForm, release_id: event.target.value })}>
              <option value="">Seleccione versión</option>
              {releases.map((release) => (
                <option key={release.id} value={release.id}>
                  {release.version} · {release.os_family}/{release.architecture}
                </option>
              ))}
            </select>
            <input className="form-control mb-2" required placeholder="Etiqueta del lote"
              value={kitForm.label} onChange={(event) => setKitForm({ ...kitForm, label: event.target.value })} />
            <input className="form-control mb-2" required placeholder="URL pública HTTPS"
              value={kitForm.public_server_url}
              onChange={(event) => setKitForm({ ...kitForm, public_server_url: event.target.value })} />
            <select className="form-select mb-2" value={kitForm.group_id}
              onChange={(event) => setKitForm({ ...kitForm, group_id: event.target.value })}>
              <option value="">Sin grupo inicial</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
            <div className="row g-2 mb-2">
              <div className="col">
                <label className="form-label small">Máximo de instalaciones</label>
                <input type="number" min="1" max="10000" className="form-control"
                  value={kitForm.max_uses}
                  onChange={(event) => setKitForm({ ...kitForm, max_uses: event.target.value })} />
              </div>
              <div className="col">
                <label className="form-label small">Caducidad (horas)</label>
                <input type="number" min="1" max="720" className="form-control"
                  value={kitForm.expires_hours}
                  onChange={(event) => setKitForm({ ...kitForm, expires_hours: event.target.value })} />
              </div>
            </div>
            <button className="btn btn-primary" disabled={!releases.length}>Generar instalador</button>
          </form>
        </div>
      </div>

      {kit && (
        <div className="kpi mt-3">
          <h2 className="h6">Kit listo: {kit.os_family}/{kit.architecture}</h2>
          <div className="small">Versión {kit.release_version} · SHA-256 <code>{kit.sha256}</code></div>
          <div className="small">Token {kit.token_prefix}… · caduca {new Date(kit.expires_at).toLocaleString()}</div>
          <ol className="small mt-2">{kit.instructions.map((instruction) => <li key={instruction}>{instruction}</li>)}</ol>
          <button className="btn btn-success" onClick={downloadScript}>Descargar {kit.filename}</button>
        </div>
      )}

      <div className="kpi mt-3">
        <h2 className="h6">Versiones aprobadas</h2>
        <div className="table-responsive">
          <table className="table mb-0">
            <thead><tr><th>Versión</th><th>Sistema</th><th>Arquitectura</th><th>SHA-256</th><th>Tamaño</th></tr></thead>
            <tbody>
              {releases.map((release) => (
                <tr key={release.id}>
                  <td>{release.version}</td>
                  <td>{release.os_family}</td>
                  <td>{release.architecture}</td>
                  <td><code>{release.sha256.slice(0, 20)}…</code></td>
                  <td>{Math.ceil(release.size_bytes / 1024)} KB</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
