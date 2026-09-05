# Modelo de datos — TIC Control AI

Claves UUID (`CHAR(36)`). Tiempos en UTC. Contraseñas con Argon2. Tokens de agente y refresh se almacenan **hasheados**.

## Entidades del MVP

```
users 1──* refresh_tokens
users 1──* audit_logs
users 1──* enrollment_tokens
users 1──* software_packages
users 1──* install_jobs

device_groups 1──* device_group_members *──1 devices
devices 1──1 agents
devices 1──* network_interfaces
devices 1──* device_metrics
devices 1──* device_software *──1 software
devices 1──* agent_tasks
devices 1──* events
devices 1──* alerts
devices 1──* install_job_devices *──1 install_jobs *──1 software_packages

network_sites 1──* network_collectors
network_sites 1──* network_credentials
network_sites 1──* network_scan_jobs
network_sites 1──* network_devices
network_sites 1──* network_links
agent_releases 1──* agent_deployment_kits *──1 enrollment_tokens
```

## Tablas

### users
`id`, `username`, `email`, `full_name`, `password_hash`, `role` (superadmin | administrador_tic | soporte | visualizador | directivo), `is_active`, `totp_secret`, `totp_enabled`, `last_login_at`, `created_at`, `updated_at`

### refresh_tokens
`id`, `user_id`, `token_hash`, `expires_at`, `revoked_at`, `user_agent`, `ip_address`, `created_at`

### enrollment_tokens
`id`, `label`, `token_hash`, `token_prefix`, `max_uses`, `use_count`, `expires_at`, `group_id`, `created_by`, `revoked_at`, `created_at`

### devices
Inventario de equipo + estado operativo. Flags de exclusión: fondo, Chrome, software, tráfico, IA.

Estados: `online`, `offline`, `advertencia`, `critico`, `excluido`, `mantenimiento`.

### agents
`device_id` único, `token_hash`, `hmac_secret_encrypted`, `version`, `heartbeat_interval_seconds`, `revoked`.

### device_groups / device_group_members
Grupos (Laboratorio 1, Profesores, etc.) y pertenencia N:N.

### software / device_software
Catálogo institucional y presencia por equipo (versión, fechas de detección). Categorías: autorizado, no_autorizado, obligatorio, opcional, ignorar.

### software_packages
Instaladores aprobados: nombre, versión, SO, arquitectura, `sha256`, comando de instalación, archivo, administrador que lo cargó.

### install_jobs / install_job_devices
Trabajo de instalación y estado por equipo: pendiente, descargando, instalando, instalado, error.

### agent_tasks
Cola pull: `task_id`, `device_id`, `type`, `payload_json`, `signature`, `expires_at`, `status`, `result_json`. Idempotencia por `task_id`.

### network_interfaces
Interfaces reportadas por el agente (nombre, MAC, IPv4/IPv6, velocidad, contadores).

### device_metrics
Muestras periódicas (CPU, RAM, disco, tráfico). No se guarda cada segundo; el intervalo es el heartbeat.

### alerts / events / audit_logs / system_settings
Alertas (info/advertencia/importante/critico), eventos de equipo, auditoría de administración, configuración clave/valor.

### network_sites / network_collectors
Sedes con CIDR privados autorizados, límite de hosts y recolectores autenticados mediante token individual hasheado.

### network_credentials
Perfiles SNMPv3 o SNMPv2c. Secretos cifrados en reposo; las respuestas administrativas nunca los devuelven.

### network_scan_jobs / network_devices / network_links
Escaneos confirmados, inventario neutral de fabricante y relaciones LLDP/CDP. Los dispositivos guardan IP, MAC, marca, modelo, serie, tipo, puertos y protocolos remotos detectados.

### agent_releases / agent_deployment_kits
Binarios del agente separados de paquetes de aplicaciones. Cada versión tiene plataforma, arquitectura y SHA-256. Un kit referencia un token de enrolamiento limitado y genera un script visible de instalación.

## Tablas previstas (fases posteriores)

`network_metrics`, `traffic_metrics`, `policies`, `device_policies`, `ai_analysis`, `file_analysis`.

No se crean APIs vacías sobre ellas en el MVP.
