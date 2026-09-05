# TIC Control AI

Plataforma web para administrar, supervisar y mantener computadores Windows y Linux desde un panel central. Los agentes **siempre inician** la comunicación por HTTPS; el servidor no abre conexiones hacia los PCs.

Documentación de diseño:

- [Arquitectura](docs/ARQUITECTURA.md)
- [Modelo de datos](docs/MODELO_DATOS.md)
- [API](docs/API.md)
- [Pantallas](docs/PANTALLAS.md)
- [Flujo agente ↔ servidor](docs/FLUJO_AGENTE.md)
- [Seguridad](docs/SEGURIDAD.md)
- [Red multi-marca e instalación del recolector](docs/RED_MULTI_MARCA.md)
- [Fases](docs/FASES.md)

## Estructura

```
backend/     API FastAPI (Python)
frontend/    Panel React + Vite + Bootstrap
agent/       Agente Go (Windows Service / systemd)
deploy/      Caddy y variables de entorno
docs/        Diseño
docker-compose.yml
```

## Requisitos

- Python 3.12
- Node.js 20+
- Go 1.24+
- Docker (opcional, recomendado en producción)
- PostgreSQL en producción; SQLite basta para desarrollo

## Desarrollo local

```bash
# API
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data/packages
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Panel (otra terminal)
cd frontend
npm install
npm run dev
```

Abra http://127.0.0.1:5173

Usuario inicial:

- usuario: `admin`
- contraseña: `CambiarAdmin123!` (cámbiela de inmediato; también con `BOOTSTRAP_ADMIN_PASSWORD`)

API y Swagger: http://127.0.0.1:8000/docs

### Enrolar un agente en la misma máquina

1. Inicie sesión → Configuración → Generar token.
2. Compile y enrolé:

```bash
cd agent
go mod tidy
go build -o tic-agent ./cmd/tic-agent
mkdir -p /tmp/tic-control
./tic-agent enroll --server http://127.0.0.1:8000 --token TOKEN --config /tmp/tic-control/agent.json
./tic-agent run --config /tmp/tic-control/agent.json
```

El equipo aparece en **Equipos** tras el primer heartbeat (unos segundos).

### Windows

```powershell
go build -o tic-agent.exe ./cmd/tic-agent
.\tic-agent.exe enroll --server https://tic.institucion.tld --token TOKEN
# Como administrador:
.\packaging\windows\install.ps1
```

### Linux (systemd)

```bash
sudo install -m 755 tic-agent /usr/local/bin/tic-agent
sudo mkdir -p /etc/tic-control
sudo tic-agent enroll --server https://tic.institucion.tld --token TOKEN
sudo install -m 644 packaging/systemd/tic-agent.service /etc/systemd/system/
sudo systemctl enable --now tic-agent
```

## Docker Compose

```bash
cp deploy/.env.example deploy/.env
# edite SECRET_KEY, CREDENTIALS_KEY, BOOTSTRAP_ADMIN_PASSWORD y el proxy confiable
docker compose up --build
```

- Panel: http://localhost:8080
- API: http://localhost:8000/docs

En producción coloque Caddy o Nginx con TLS delante (`deploy/caddy/Caddyfile`). Active `HTTPS_ONLY=true` y `COOKIE_SECURE=true`.

## Pruebas

```bash
cd backend && python3 -m pytest -q
cd agent && go test ./...
```

## Qué incluye el MVP

Login y 2FA opcional, RBAC, agente Windows/Linux, heartbeat, inventario de hardware y software, grupos, dashboard, instalación remota con SHA-256 y comando aprobado, alertas, historial de métricas y auditoría.

También incluye descubrimiento de red multi-marca mediante un recolector por sede:

- no requiere instalar agente en cada dispositivo descubierto;
- redes privadas expresamente autorizadas;
- TCP, ARP, SNMPv3/SNMPv2c, ENTITY-MIB, IP-MIB y BRIDGE-MIB;
- vecinos LLDP/CDP;
- Cisco, TP-Link/Omada, UniFi/Ubiquiti y dispositivos estándar;
- apertura auditada de RDP/VNC/SSH/web cuando ya están habilitados.

Instalación detallada: [docs/RED_MULTI_MARCA.md](docs/RED_MULTI_MARCA.md).

## Qué no incluye aún (fases 4-7)

Adaptadores de API específicos para versiones concretas de UniFi Network, Omada y Cisco Catalyst Center; análisis de tráfico avanzado, motor de IA, ordenador de archivos e informes PDF.

## Seguridad operativa

- No capture ni almacene contraseñas de usuarios de los PCs.
- No envíe comandos arbitrarios: solo tipos de tarea conocidos y comandos de paquete aprobados.
- Las acciones masivas piden confirmación.
- Rote `SECRET_KEY` y los tokens de enrolamiento.
- Cada agente tiene credencial propia, revocable.
