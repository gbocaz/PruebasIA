import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppLayout from "./layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import DevicesPage from "./pages/DevicesPage";
import DeviceDetailPage from "./pages/DeviceDetailPage";
import NetworkPage from "./pages/NetworkPage";
import NetworkDevicePage from "./pages/NetworkDevicePage";
import SoftwarePage from "./pages/SoftwarePage";
import PackagesPage from "./pages/PackagesPage";
import InstallationsPage from "./pages/InstallationsPage";
import GroupsPage from "./pages/GroupsPage";
import AlertsPage from "./pages/AlertsPage";
import UsersPage from "./pages/UsersPage";
import AuditPage from "./pages/AuditPage";
import SettingsPage from "./pages/SettingsPage";
import AgentDeploymentPage from "./pages/AgentDeploymentPage";

function Private({ children }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-4">Cargando sesión…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <AppLayout>{children}</AppLayout>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Private><DashboardPage /></Private>} />
          <Route path="/equipos" element={<Private><DevicesPage /></Private>} />
          <Route path="/equipos/:id" element={<Private><DeviceDetailPage /></Private>} />
          <Route path="/red" element={<Private><NetworkPage /></Private>} />
          <Route path="/red/dispositivos/:id" element={<Private><NetworkDevicePage /></Private>} />
          <Route path="/software" element={<Private><SoftwarePage /></Private>} />
          <Route path="/paquetes" element={<Private><PackagesPage /></Private>} />
          <Route path="/instalaciones" element={<Private><InstallationsPage /></Private>} />
          <Route path="/grupos" element={<Private><GroupsPage /></Private>} />
          <Route path="/alertas" element={<Private><AlertsPage /></Private>} />
          <Route path="/usuarios" element={<Private><UsersPage /></Private>} />
          <Route path="/auditoria" element={<Private><AuditPage /></Private>} />
          <Route path="/configuracion" element={<Private><SettingsPage /></Private>} />
          <Route path="/despliegue-agentes" element={<Private><AgentDeploymentPage /></Private>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
