# Diseño de API — TIC Control AI

Base: `/api`. Protocolo de agentes: `/agent`. Documentación interactiva: `/docs` (OpenAPI/Swagger). `/redoc` disponible.

Autenticación de administradores: `Authorization: Bearer <access_jwt>` (15 minutos). Refresh por cookie httpOnly `tic_refresh` o cuerpo JSON.

Autenticación de agentes: `Authorization: Bearer <agent_token>` emitido en el enrolamiento.

## Administración

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| POST | `/api/auth/login` | público | Login (+ TOTP si está activo) |
| POST | `/api/auth/refresh` | cookie/body | Nuevo access token |
| POST | `/api/auth/logout` | autenticado | Revoca refresh |
| GET | `/api/auth/me` | autenticado | Usuario actual |
| POST | `/api/auth/change-password` | autenticado | Cambio de contraseña |
| POST | `/api/auth/2fa/setup` | autenticado | Inicia TOTP |
| POST | `/api/auth/2fa/enable` | autenticado | Confirma TOTP |
| POST | `/api/auth/2fa/disable` | autenticado | Desactiva TOTP |
| GET/POST/PATCH | `/api/users` | superadmin (escritura) | Usuarios y roles |
| GET | `/api/devices` | según rol | Listado + filtros |
| GET/PATCH | `/api/devices/{id}` | según rol | Ficha y estado |
| GET | `/api/devices/{id}/software` | según rol | Software del equipo |
| GET | `/api/devices/{id}/metrics` | según rol | Histórico |
| GET | `/api/devices/{id}/events` | según rol | Eventos |
| POST | `/api/devices/{id}/actions` | admin/soporte limitado | Inventario, reinicio agente |
| GET/POST/PATCH/DELETE | `/api/groups` | admin | Grupos |
| GET | `/api/software` | autenticado | Catálogo |
| PATCH | `/api/software/{id}` | admin | Categoría |
| GET | `/api/software/search` | autenticado | ¿Dónde está X? ¿Quién no lo tiene? |
| GET/POST/DELETE | `/api/packages` | admin | Paquetes firmados |
| POST | `/api/installations` | admin | Instalar en equipo/grupo/todos |
| GET | `/api/installations` | autenticado | Trabajos |
| GET | `/api/alerts` | autenticado | Alertas |
| POST | `/api/alerts/{id}/ack` | admin/soporte | Reconocer |
| GET | `/api/audit` | admin/directivo | Auditoría |
| GET | `/api/search` | autenticado | Equipo, IP, MAC, programa, usuario |
| GET | `/api/dashboard` | autenticado | KPI del MVP |
| GET/POST | `/api/agents/enrollment-tokens` | admin | Tokens de alta |
| GET | `/api/reports/inventory.csv` | autenticado | Exportación |

## Protocolo del agente (el PC inicia)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/agent/enroll` | Alta con token de enrolamiento |
| POST | `/agent/heartbeat` | Estado + métricas ligeras |
| POST | `/agent/inventory` | Software e interfaces |
| POST | `/agent/metrics` | Métricas adicionales |
| GET | `/agent/tasks` | Tareas pendientes no expiradas |
| POST | `/agent/task-result` | Resultado (idempotente) |
| GET | `/agent/packages/{id}/download` | Descarga del instalador aprobado |

## Tareas

Campos: `task_id`, `device_id`, `type`, `params`, `signature`, `created_at`, `expires_at`.

Tipos MVP: `collect_inventory`, `install_package`, `restart_agent`, `update_agent`.

Una tarea ejecutada no se reenvía. La firma HMAC se calcula con el secreto del agente.
