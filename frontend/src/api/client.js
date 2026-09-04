import axios from "axios";

const api = axios.create({ withCredentials: true });

export function setAccessToken(token) {
  api.defaults.headers.common.Authorization = token ? `Bearer ${token}` : "";
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original?._retry && !original?.url?.includes("/api/auth/login")) {
      original._retry = true;
      try {
        const refreshed = await api.post("/api/auth/refresh");
        setAccessToken(refreshed.data.access_token);
        original.headers.Authorization = `Bearer ${refreshed.data.access_token}`;
        return api(original);
      } catch {
        setAccessToken("");
      }
    }
    throw error;
  }
);

export default api;
