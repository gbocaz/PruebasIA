import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [need2fa, setNeed2fa] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      const res = await login(username, password, totp);
      if (res.requires_2fa) setNeed2fa(true);
    } catch {
      setError("No se pudo iniciar sesión. Verifique usuario, contraseña o código 2FA.");
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1 className="h4 mb-1">TIC Control AI</h1>
        <p className="text-secondary mb-4">Acceso de administración</p>
        {error && <div className="alert alert-danger">{error}</div>}
        <label className="form-label">Usuario</label>
        <input className="form-control mb-3" value={username} onChange={(e) => setUsername(e.target.value)} />
        <label className="form-label">Contraseña</label>
        <input type="password" className="form-control mb-3" value={password} onChange={(e) => setPassword(e.target.value)} />
        {need2fa && (
          <>
            <label className="form-label">Código 2FA</label>
            <input className="form-control mb-3" value={totp} onChange={(e) => setTotp(e.target.value)} />
          </>
        )}
        <button className="btn btn-primary w-100">Entrar</button>
      </form>
    </div>
  );
}
