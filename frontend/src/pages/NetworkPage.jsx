import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/ui";

function errorText(error) {
  return error.response?.data?.detail || "No se pudo completar la operación.";
}

export default function NetworkPage() {
  const { canWrite } = useAuth();
  const [sites, setSites] = useState([]);
  const [siteId, setSiteId] = useState("");
  const [devices, setDevices] = useState([]);
  const [collectors, setCollectors] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [scans, setScans] = useState([]);
  const [links, setLinks] = useState([]);
  const [tab, setTab] = useState("dispositivos");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [collectorToken, setCollectorToken] = useState("");
  const [showSiteForm, setShowSiteForm] = useState(false);
  const [siteForm, setSiteForm] = useState({
    name: "",
    location: "",
    description: "",
    cidrs: "192.168.1.0/24",
    max_hosts_per_scan: 4096,
  });
  const [credentialForm, setCredentialForm] = useState({
    name: "SNMP lectura",
    kind: "snmp_v3",
    username: "",
    secret: "",
    auth_protocol: "SHA",
    privacy_protocol: "AES",
    privacy_secret: "",
  });
  const [query, setQuery] = useState("");

  const currentSite = useMemo(() => sites.find((site) => site.id === siteId), [sites, siteId]);

  async function loadSites() {
    const { data } = await api.get("/api/network/sites");
    setSites(data);
    if (!siteId && data.length) setSiteId(data[0].id);
  }

  async function loadSiteData(id = siteId) {
    if (!id) return;
    const calls = [
      api.get("/api/network/devices", { params: { site_id: id } }),
      api.get(`/api/network/sites/${id}/collectors`),
      api.get("/api/network/scans", { params: { site_id: id } }),
      api.get("/api/network/links", { params: { site_id: id } }),
    ];
    if (canWrite) calls.push(api.get(`/api/network/sites/${id}/credentials`));
    const [d, c, s, l, creds] = await Promise.all(calls);
    setDevices(d.data);
    setCollectors(c.data);
    setScans(s.data);
    setLinks(l.data);
    setCredentials(creds?.data || []);
  }

  useEffect(() => {
    loadSites().catch((e) => setError(errorText(e)));
  }, []);

  useEffect(() => {
    loadSiteData(siteId).catch((e) => setError(errorText(e)));
  }, [siteId]);

  useEffect(() => {
    if (!siteId) return undefined;
    const timer = window.setInterval(() => {
      loadSites();
      loadSiteData(siteId);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [siteId, canWrite]);

  async function createSite(event) {
    event.preventDefault();
    setError("");
    try {
      const { data } = await api.post("/api/network/sites", {
        ...siteForm,
        cidrs: siteForm.cidrs.split(/[\s,]+/).filter(Boolean),
        max_hosts_per_scan: Number(siteForm.max_hosts_per_scan),
      });
      await loadSites();
      setSiteId(data.id);
      setShowSiteForm(false);
      setMessage("Sede creada. Instale ahora un recolector dentro de esa red.");
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function createCollector() {
    setError("");
    try {
      const name = window.prompt("Nombre del recolector", `Recolector ${currentSite?.name || ""}`);
      if (!name) return;
      const { data } = await api.post(`/api/network/sites/${siteId}/collectors`, { name });
      setCollectorToken(data.token);
      setMessage("Token generado. Se muestra una sola vez.");
      await loadSiteData();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function addCredential(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post(`/api/network/sites/${siteId}/credentials`, credentialForm);
      setCredentialForm({ ...credentialForm, secret: "", privacy_secret: "" });
      setMessage("Credencial SNMP cifrada y guardada.");
      await loadSiteData();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function startScan() {
    if (!window.confirm(`¿Escanear únicamente los CIDR autorizados de ${currentSite?.name}?`)) return;
    setError("");
    try {
      await api.post("/api/network/scans", {
        site_id: siteId,
        methods: ["tcp", "arp", "snmp"],
        confirm: true,
      });
      setMessage("Escaneo en cola. El recolector lo ejecutará sin instalar software en cada equipo.");
      await loadSiteData();
    } catch (e) {
      setError(errorText(e));
    }
  }

  const shownDevices = devices.filter((device) => {
    const text = `${device.hostname} ${device.ip_address} ${device.mac_address} ${device.vendor} ${device.model}`.toLowerCase();
    return text.includes(query.toLowerCase());
  });
  const online = devices.filter((device) => device.status === "online").length;
  const knownVendors = new Set(devices.map((device) => device.vendor)).size;

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center gap-2 mb-3 flex-wrap">
        <div>
          <h1 className="h4 mb-1">Red</h1>
          <div className="text-secondary small">
            Descubrimiento multi-marca con un recolector por sede; no requiere agente en cada dispositivo.
          </div>
        </div>
        <select className="form-select w-auto" value={siteId} onChange={(event) => setSiteId(event.target.value)}>
          <option value="">Seleccione sede</option>
          {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
        </select>
        {canWrite && <button className="btn btn-outline-primary" onClick={() => setShowSiteForm(true)}>Nueva sede</button>}
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {message && <div className="alert alert-info">{message}</div>}

      {(!siteId || showSiteForm) && canWrite && (
        <form className="kpi" onSubmit={createSite}>
          <h2 className="h6">1. Registrar una sede o red autorizada</h2>
          <div className="row g-2">
            <div className="col-md-3">
              <input className="form-control" required placeholder="Nombre de sede" value={siteForm.name}
                onChange={(event) => setSiteForm({ ...siteForm, name: event.target.value })} />
            </div>
            <div className="col-md-3">
              <input className="form-control" placeholder="Ubicación" value={siteForm.location}
                onChange={(event) => setSiteForm({ ...siteForm, location: event.target.value })} />
            </div>
            <div className="col-md-4">
              <input className="form-control" required placeholder="CIDR privados, separados por coma" value={siteForm.cidrs}
                onChange={(event) => setSiteForm({ ...siteForm, cidrs: event.target.value })} />
            </div>
            <div className="col-md-2">
              <button className="btn btn-primary w-100">Crear sede</button>
            </div>
          </div>
          <div className="form-text">
            Solo se aceptan rangos privados (por ejemplo 192.168.10.0/24). El límite evita escaneos accidentales extensos.
          </div>
        </form>
      )}

      {siteId && (
        <>
          <div className="row g-3 mb-3">
            {[
              ["Dispositivos", devices.length],
              ["Online", online],
              ["Fabricantes", knownVendors],
              ["Recolectores online", currentSite?.collectors_online || 0],
            ].map(([label, value]) => (
              <div className="col-6 col-lg-3" key={label}>
                <div className="kpi"><div className="text-secondary small">{label}</div><div className="n">{value}</div></div>
              </div>
            ))}
          </div>
          <div className="kpi mb-3">
            <div className="d-flex justify-content-between gap-2 flex-wrap">
              <div>
                <strong>{currentSite?.name}</strong> · {currentSite?.location || "Sin ubicación"}<br />
                <span className="small text-secondary">CIDR autorizados: {currentSite?.cidrs.join(", ")}</span>
              </div>
              {canWrite && (
                <div className="d-flex gap-2">
                  <button className="btn btn-outline-primary" onClick={createCollector}>Crear recolector</button>
                  <button className="btn btn-primary" onClick={startScan}>Descubrir equipos</button>
                </div>
              )}
            </div>
          </div>

          {collectorToken && (
            <div className="alert alert-warning">
              <strong>Copie el token ahora (solo se muestra una vez):</strong>
              <code className="d-block text-break my-2">{collectorToken}</code>
              <div className="small">Linux:</div>
              <code className="d-block text-break">
                sudo tic-network-collector configure --server https://SU-SERVIDOR --token {collectorToken}
              </code>
            </div>
          )}

          <div className="d-flex gap-2 flex-wrap mb-3">
            {[
              ["dispositivos", "Dispositivos"],
              ["topologia", "Topología LLDP/CDP"],
              ["recolectores", "Recolectores"],
              ["snmp", "Credenciales SNMP"],
              ["escaneos", "Escaneos"],
            ].map(([id, label]) => (
              <button key={id} className={`btn btn-sm ${tab === id ? "btn-primary" : "btn-outline-secondary"}`}
                onClick={() => setTab(id)}>{label}</button>
            ))}
          </div>

          {tab === "dispositivos" && (
            <>
              <input className="form-control mb-3" placeholder="Filtrar IP, MAC, nombre, marca o modelo"
                value={query} onChange={(event) => setQuery(event.target.value)} />
              <div className="table-responsive kpi p-0">
                <table className="table mb-0">
                  <thead><tr><th>Dispositivo</th><th>Estado</th><th>Gestión</th><th>IP / MAC</th><th>Marca / modelo</th><th>Tipo</th><th>Servicios</th><th>Origen</th></tr></thead>
                  <tbody>
                    {shownDevices.map((device) => (
                      <tr key={device.id}>
                        <td><Link to={`/red/dispositivos/${device.id}`}>{device.hostname || device.sys_name || "Sin nombre"}</Link></td>
                        <td><StatusBadge status={device.status} /></td>
                        <td>
                          {device.managed_device_id
                            ? <Link to={`/equipos/${device.managed_device_id}`} className="badge text-bg-success">Con agente</Link>
                            : <span className="badge text-bg-secondary">Sin agente</span>}
                        </td>
                        <td>{device.ip_address}<br /><span className="small text-secondary">{device.mac_address || "MAC no disponible"}</span></td>
                        <td>{device.vendor}<br /><span className="small text-secondary">{device.model || "Modelo no publicado"}</span></td>
                        <td>{device.device_type}</td>
                        <td>{device.remote_services.join(", ") || "—"}</td>
                        <td>{device.discovery_source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!shownDevices.length && <div className="text-secondary mt-3">No hay dispositivos descubiertos todavía.</div>}
            </>
          )}

          {tab === "topologia" && (
            <div className="row g-3">
              {links.map((link) => (
                <div className="col-md-6" key={link.id}>
                  <div className="kpi">
                    <span className="badge text-bg-secondary me-2">{link.protocol.toUpperCase()}</span>
                    <strong>{link.source_identity}</strong> puerto {link.source_port || "?"}
                    <div className="text-center text-secondary">↓</div>
                    <strong>{link.target_identity}</strong> puerto {link.target_port || "?"}
                  </div>
                </div>
              ))}
              {!links.length && <div className="text-secondary">Los enlaces aparecerán cuando switches o AP publiquen LLDP/CDP por SNMP.</div>}
            </div>
          )}

          {tab === "recolectores" && (
            <div>
              {collectors.map((collector) => (
                <div className="kpi mb-2" key={collector.id}>
                  <strong>{collector.name}</strong> · <StatusBadge status={collector.online ? "online" : "offline"} />
                  <div className="small text-secondary">
                    Host: {collector.hostname || "todavía no conectado"} · versión {collector.version || "—"} · token {collector.token_prefix}…
                  </div>
                </div>
              ))}
              {!collectors.length && <div className="text-secondary">Cree e instale un recolector dentro de la sede.</div>}
            </div>
          )}

          {tab === "snmp" && canWrite && (
            <div>
              <form className="kpi mb-3" onSubmit={addCredential}>
                <h2 className="h6">Credencial de solo lectura</h2>
                <div className="row g-2">
                  <div className="col-md-3">
                    <input className="form-control" required placeholder="Nombre" value={credentialForm.name}
                      onChange={(event) => setCredentialForm({ ...credentialForm, name: event.target.value })} />
                  </div>
                  <div className="col-md-2">
                    <select className="form-select" value={credentialForm.kind}
                      onChange={(event) => setCredentialForm({ ...credentialForm, kind: event.target.value })}>
                      <option value="snmp_v3">SNMPv3</option>
                      <option value="snmp_v2c">SNMPv2c</option>
                    </select>
                  </div>
                  <div className="col-md-2">
                    <input className="form-control" placeholder={credentialForm.kind === "snmp_v3" ? "Usuario" : "No aplica"}
                      disabled={credentialForm.kind === "snmp_v2c"} value={credentialForm.username}
                      onChange={(event) => setCredentialForm({ ...credentialForm, username: event.target.value })} />
                  </div>
                  <div className="col-md-2">
                    <input type="password" className="form-control" required
                      placeholder={credentialForm.kind === "snmp_v3" ? "Clave autenticación" : "Community"}
                      value={credentialForm.secret}
                      onChange={(event) => setCredentialForm({ ...credentialForm, secret: event.target.value })} />
                  </div>
                  {credentialForm.kind === "snmp_v3" && (
                    <div className="col-md-2">
                      <input type="password" className="form-control" required placeholder="Clave privacidad"
                        value={credentialForm.privacy_secret}
                        onChange={(event) => setCredentialForm({ ...credentialForm, privacy_secret: event.target.value })} />
                    </div>
                  )}
                  <div className="col-md-1"><button className="btn btn-primary w-100">Guardar</button></div>
                </div>
                <div className="form-text">Use un usuario SNMP exclusivo de lectura. SNMPv3 cifra autenticación y tráfico.</div>
              </form>
              {credentials.map((credential) => (
                <div className="kpi mb-2" key={credential.id}>
                  <strong>{credential.name}</strong> · {credential.kind} · {credential.username || "community oculta"} · {credential.auth_protocol}/{credential.privacy_protocol}
                </div>
              ))}
            </div>
          )}

          {tab === "escaneos" && (
            <table className="table">
              <thead><tr><th>Fecha</th><th>Estado</th><th>Métodos</th><th>Resultados</th><th>Error</th></tr></thead>
              <tbody>
                {scans.map((scan) => (
                  <tr key={scan.id}>
                    <td>{new Date(scan.requested_at).toLocaleString()}</td>
                    <td>{scan.status}</td>
                    <td>{scan.methods.join(", ")}</td>
                    <td>{scan.result_count}</td>
                    <td>{scan.error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
