import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api, { setAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  async function loadMe() {
    const { data } = await api.get("/api/auth/me");
    setUser(data);
  }

  useEffect(() => {
    api
      .post("/api/auth/refresh")
      .then(async (res) => {
        setAccessToken(res.data.access_token);
        await loadMe();
      })
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      async login(username, password, totp_code) {
        const { data } = await api.post("/api/auth/login", { username, password, totp_code: totp_code || null });
        if (data.requires_2fa) return { requires_2fa: true };
        setAccessToken(data.access_token);
        await loadMe();
        return { requires_2fa: false };
      },
      async logout() {
        try {
          await api.post("/api/auth/logout");
        } finally {
          setAccessToken("");
          setUser(null);
        }
      },
      canWrite: user && ["superadmin", "administrador_tic"].includes(user.role),
      canSupport: user && ["superadmin", "administrador_tic", "soporte"].includes(user.role),
      canUsers: user && user.role === "superadmin",
      canAudit: user && ["superadmin", "administrador_tic", "directivo"].includes(user.role),
    }),
    [user, ready]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
