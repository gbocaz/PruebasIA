# Arquitectura — TIC Control AI

## Objetivo

Administrar, supervisar y mantener computadores Windows y Linux desde un panel web centralizado, accesible de forma segura desde Internet. Los agentes **siempre inician** la comunicación hacia el servidor por HTTPS. No hay conexiones entrantes hacia los equipos.

## Diagrama general

```
┌─────────────┐   HTTPS (salida)    ┌──────────────────┐
│  PC Windows │────────────────────►│                  │
│  PC Linux   │  heartbeat/inventory│   Reverse proxy  │
│  (Agente)   │  tasks / resultados │   Caddy / Nginx  │
└─────────────┘                     └────────┬─────────┘
┌─────────────┐ SNMP/LLDP/TCP/ARP            │
│ Red de sede │────────► Recolector ──HTTPS──┘
│ multi-marca │        (uno por sede)
└─────────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        ▼                        │
                    │              ┌─────────────────┐                │
                    │              │  API FastAPI    │                │
                    │              │  REST + OpenAPI │                │
                    │              └────────┬────────┘                │
                    │                       │                         │
                    │         ┌─────────────┼─────────────┐           │
                    │         ▼             ▼             ▼           │
                    │  ┌────────────┐ ┌──────────┐ ┌───────────┐      │
                    │  │ PostgreSQL │ │ Uploads  │ │  IA *     │      │
                    │  │ (SQLite    │ │ paquetes │ │  Ollama / │      │
                    │  │  en dev)   │ │ firmados │ │  API      │      │
                    │  └────────────┘ └──────────┘ └───────────┘      │
                    │                                                 │
                    │              ┌─────────────────┐                │
                    │              │  Panel React    │                │
                    │              │  (administradores)│              │
                    │              └─────────────────┘                │
                    └─────────────────────────────────────────────────┘

* El motor de IA es opcional. La plataforma funciona sin él.
```

## Componentes

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| Agente | Go, servicio Windows / systemd | Inventario, heartbeat, ejecución de tareas firmadas |
| Recolector de red | Go, servicio Windows / systemd | Descubrimiento TCP/ARP/SNMP/LLDP/CDP sin agente por dispositivo |
| API | Python, FastAPI, SQLAlchemy | Autenticación, RBAC, inventario, instalaciones, alertas, auditoría |
| Panel | React + Vite + Bootstrap | Administración sencilla y responsive |
| IA (fases 5-6) | Python + Ollama / OpenRouter | Análisis, resúmenes, recomendaciones. Nunca actúa sola sobre varios equipos |
| Proxy | Caddy o Nginx | TLS, reverse proxy |
| BD | PostgreSQL (prod), SQLite (dev), MySQL opcional | Estado persistente |

## Principios

1. **Pull, no push.** El agente consulta tareas (`GET /agent/tasks`). El servidor no abre puertos hacia los PCs.
2. **Mínimo privilegio.** RBAC estricto. El rol SOPORTE solo ejecuta acciones preautorizadas.
3. **Nada oculto.** Sin evasión de seguridad, sin captura de teclado, sin contraseñas de usuarios de los PCs.
4. **Toda acción queda en `audit_logs`.**
5. **Integridad.** Instaladores con SHA-256. Tareas con firma HMAC e identificador único.
6. **Degradación elegante.** Sin Internet el agente encola eventos. Sin IA el panel sigue operativo.

## Alcance de este repositorio (MVP ampliado)

Login, usuarios/roles, agente Windows/Linux, inventario de hardware y software, estado online/offline, grupos, dashboard, instalación remota controlada, historial, alertas y auditoría.

Incluye además sedes, recolectores, credenciales SNMP cifradas, descubrimiento multi-marca, enlaces LLDP/CDP y apertura auditada de protocolos remotos preexistentes. Las APIs propietarias por versión, tráfico avanzado, IA, archivos e informes avanzados se construyen después; no se simulan con módulos vacíos.
