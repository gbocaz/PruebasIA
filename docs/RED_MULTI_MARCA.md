# Red multi-marca y soporte remoto — guía paso a paso

## 1. Qué resuelve y qué no

TIC Control AI incorpora un **recolector por sede**. Se instala una vez en una máquina Windows o Linux dentro de la red y descubre equipos sin instalar el agente TIC Control en cada uno.

Puede obtener, según lo que publique cada dispositivo:

- estado online/offline;
- IP, MAC y nombre;
- fabricante, modelo, serie y sistema;
- puertos TCP de administración;
- RDP, VNC, SSH y panel web ya habilitados;
- información SNMP estándar;
- relaciones LLDP/CDP;
- tabla ARP del router y puerto de switch mediante IP-MIB/BRIDGE-MIB.

No existe una API universal que permita controlar todos los modelos de todas las marcas. La interoperabilidad se consigue por estándares:

| Fuente | Información | Marcas |
|---|---|---|
| TCP + ARP | Presencia, IP, MAC y servicios | Cualquier fabricante |
| SNMPv3/v2c | Nombre, descripción, modelo, serie | Cisco, TP-Link, UniFi y cualquier equipo compatible |
| ENTITY-MIB | Modelo y serie | Equipos administrables compatibles |
| LLDP | Vecinos y puertos | Estándar multi-marca |
| CDP | Vecinos y puertos | Principalmente Cisco |
| IP-MIB / BRIDGE-MIB | ARP y puerto del switch | Routers/switches compatibles |

Las APIs específicas de UniFi Network, Omada Controller y Cisco Catalyst Center se añadirán como adaptadores versionados. No deben sustituir la base SNMP/LLDP porque cambian entre versiones y familias.

### Pantallas y control remoto

Descubrir un equipo no otorga acceso a su pantalla. TIC Control solo puede abrir:

- **RDP** si Windows Remote Desktop ya está habilitado;
- **VNC** si ya existe un servidor VNC autorizado;
- **SSH** si el equipo ya publica SSH;
- **HTTP/HTTPS** para el panel oficial del dispositivo.

TIC Control no habilita estos servicios, no instala acceso oculto y no guarda sus contraseñas. Cada apertura requiere confirmación, aplica RBAC y queda en auditoría.

## 2. Arquitectura

```
Equipos / switches / AP / impresoras
       │ TCP, ARP, SNMP, LLDP/CDP
       ▼
Recolector de sede (una instalación)
       │ HTTPS saliente
       ▼
API TIC Control AI ── Base de datos ── Panel web
```

No se aceptan CIDR públicos. El servidor valida que el alcance sea privado, loopback o link-local y limita la cantidad de hosts. El recolector vuelve a validar antes de explorar.

## 3. Etapa 1 — instalar el servidor

Esta etapa levanta PostgreSQL, la API y el panel.

```bash
git clone URL_DEL_REPOSITORIO
cd PruebasIA
cp deploy/.env.example deploy/.env
```

Edite `deploy/.env`:

```dotenv
SECRET_KEY=GENERE_UN_VALOR_ALEATORIO_DE_32_BYTES_O_MAS
CREDENTIALS_KEY=GENERE_OTRO_VALOR_ALEATORIO_DE_32_BYTES_O_MAS
BOOTSTRAP_ADMIN_PASSWORD=UNA_CLAVE_INICIAL_SEGURA
DOMAIN=tic.ejemplo.edu
HTTPS_ONLY=true
COOKIE_SECURE=true
TRUSTED_PROXY_CIDRS=IP_O_CIDR_INTERNO_DEL_PROXY
```

Arranque:

```bash
docker compose up -d --build
docker compose ps
```

Qué hace:

1. PostgreSQL guarda inventario, red y auditoría.
2. FastAPI publica `/api`, `/agent`, `/collector` y `/docs`.
3. React sirve el panel.
4. Caddy o el proxy institucional debe terminar TLS.

Verifique:

```bash
curl https://tic.ejemplo.edu/health
```

Debe responder `{"status":"ok",...}`.

## 4. Etapa 2 — registrar una sede

1. Inicie sesión como `SUPERADMIN` o `ADMINISTRADOR TIC`.
2. Abra **Red**.
3. Pulse **Nueva sede**.
4. Escriba nombre, ubicación y uno o varios CIDR privados.
5. Guarde.

Ejemplos:

```text
Sede Central
192.168.10.0/24, 192.168.20.0/24, 10.30.0.0/23
```

Qué hace: define una lista de red explícitamente autorizada. El recolector no escanea fuera de ella. Para comenzar use rangos pequeños y aumente el límite solo después de validarlos.

## 5. Etapa 3 — preparar SNMP de solo lectura

SNMP no es obligatorio para saber si una IP responde, pero sí para obtener marca, modelo, serie y topología con calidad.

Recomendación:

1. Use **SNMPv3 authPriv**.
2. Cree un usuario exclusivo de solo lectura.
3. Limite UDP/161 mediante ACL a la IP del recolector.
4. Active LLDP en enlaces donde corresponda.
5. No reutilice credenciales administrativas del panel del equipo.

### Cisco IOS / IOS XE

La sintaxis varía por versión; valide con la guía oficial de su modelo. Un patrón típico es:

```text
snmp-server view TIC-READ iso included
snmp-server group TIC-GROUP v3 priv read TIC-READ
snmp-server user USUARIO TIC-GROUP v3 auth sha CLAVE_AUTH priv aes 128 CLAVE_PRIV
lldp run
```

Además, aplique una ACL para que solo el recolector llegue a UDP/161. CDP puede permanecer activo donde la política institucional lo permita.

### UniFi / Ubiquiti

En UniFi Network, abra la configuración del sistema/sitio y localice **SNMP Monitoring**. Active SNMPv3 cuando la versión lo permita y restrinja el acceso a la IP del recolector. Mantenga LLDP activo. Los nombres exactos del menú cambian según la versión del controlador.

### TP-Link Omada

En Omada Controller, abra la configuración del sitio y el apartado **SNMP** o **Services**. Cree una credencial de monitorización de solo lectura, preferentemente SNMPv3, y autorice únicamente al recolector. Active LLDP en switches administrables.

### Equipos antiguos

SNMPv2c está disponible como compatibilidad, pero la community viaja sin cifrar. Úselo solo en una VLAN de gestión aislada y con ACL.

## 6. Etapa 4 — guardar la credencial SNMP

1. En **Red**, seleccione la sede.
2. Abra **Credenciales SNMP**.
3. Seleccione SNMPv3.
4. Indique usuario, clave de autenticación y clave de privacidad.
5. Guarde.

Qué hace: cifra los secretos en la base de datos. El panel nunca los vuelve a mostrar. Solo un recolector autenticado de esa sede puede recibirlos por HTTPS y la respuesta lleva `Cache-Control: no-store`.

## 7. Etapa 5 — compilar el recolector

Requiere Go 1.24 o posterior:

```bash
cd agent
go mod download
go test ./...
go build -o tic-network-collector ./cmd/tic-network-collector
```

Qué hace: genera un ejecutable independiente. El agente por PC (`tic-agent`) y el recolector de red (`tic-network-collector`) son programas distintos.

## 8. Etapa 6 — crear token e instalar el recolector

En **Red → Recolectores**:

1. Pulse **Crear recolector**.
2. Dé un nombre descriptivo.
3. Copie el token; solo aparece una vez.

### Linux

```bash
sudo install -m 755 tic-network-collector /usr/local/bin/
sudo mkdir -p /etc/tic-control
sudo tic-network-collector configure \
  --server https://tic.ejemplo.edu \
  --token TOKEN_COPIADO \
  --poll-seconds 30 \
  --concurrency 64 \
  --timeout-ms 800

sudo install -m 644 \
  packaging/systemd/tic-network-collector.service \
  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tic-network-collector
sudo systemctl status tic-network-collector
```

Qué hace:

- guarda el token con permisos `0600`;
- envía heartbeat cada 30 segundos;
- consulta tareas mediante HTTPS saliente;
- ejecuta solo escaneos creados y confirmados en el panel;
- reintenta con backoff si Internet falla.

Logs:

```bash
sudo journalctl -u tic-network-collector -f
```

### Windows

Compile en Windows:

```powershell
go build -o tic-network-collector.exe .\cmd\tic-network-collector
```

Copie el binario a `C:\Program Files\TICControl\` y configure:

```powershell
& "C:\Program Files\TICControl\tic-network-collector.exe" configure `
  --server https://tic.ejemplo.edu `
  --token TOKEN_COPIADO

Set-ExecutionPolicy -Scope Process Bypass
.\packaging\windows\install-network-collector.ps1
```

Verifique:

```powershell
Get-Service TICControlNetworkCollector
```

## 9. Etapa 7 — descubrir equipos

1. Compruebe que **Recolectores online** sea mayor que cero.
2. Pulse **Descubrir equipos**.
3. Confirme el alcance.
4. Abra **Escaneos**.

Estados:

- `pending`: pendiente de entregar;
- `sent`: recibido por el recolector;
- `completed`: resultado guardado;
- `failed`: error visible para diagnóstico.

Qué hace cada método:

- TCP identifica servicios de administración conocidos.
- ARP obtiene MAC de la misma capa 2.
- SNMP consulta identidad, ENTITY-MIB, LLDP/CDP, ARP del router y BRIDGE-MIB.

En VLAN distintas, el recolector necesita rutas y ACL hacia esas subredes. Para asociar MAC y puertos a través de capa 3, los routers/switches deben publicar IP-MIB/BRIDGE-MIB.

## 10. Etapa 8 — revisar y dar soporte

En **Red → Dispositivos** filtre por IP, MAC, marca, modelo o nombre. Abra una ficha para ver:

- datos de identificación;
- puertos y servicios;
- `sysName`, `sysObjectID` y descripción SNMP;
- switch/puerto, VLAN y SSID cuando estén disponibles;
- botones de soporte autorizados.

### RDP

El botón descarga un archivo `.rdp` sin contraseña. Windows solicita credenciales y exige NLA. Recomendado:

- Windows Pro/Enterprise;
- NLA habilitado;
- firewall limitado a la red de soporte o VPN;
- cuentas nominativas, no compartidas;
- MFA mediante el mecanismo institucional cuando sea posible.

### VNC

Solo aparece si el puerto VNC está abierto. Use cifrado, contraseñas robustas y restricción por firewall. No exponga VNC directamente a Internet.

### SSH

Use claves, deshabilite autenticación por contraseña cuando sea viable y limite orígenes.

Cada solicitud queda como `network_remote_session` en **Auditoría** con usuario, IP administrativa, protocolo y destino.

## 11. Diagnóstico

### El recolector aparece offline

```bash
curl https://tic.ejemplo.edu/health
sudo journalctl -u tic-network-collector --since "15 minutes ago"
```

Revise DNS, TLS, salida TCP/443 y que el token no esté revocado.

### El equipo responde pero no muestra marca/modelo

Compruebe desde el host recolector:

```bash
snmpget -v3 -l authPriv -u USUARIO \
  -a SHA -A CLAVE_AUTH -x AES -X CLAVE_PRIV \
  IP .1.3.6.1.2.1.1.1.0
```

No copie claves reales a tickets o logs. Si falla, revise UDP/161, ACL, usuario y nivel SNMP.

### No aparece topología

Active LLDP, permita las MIB de solo lectura y verifique que el equipo publique LLDP-MIB. En Cisco también puede usarse CDP. Los equipos de consumo no administrables normalmente no publican topología.

## 12. Seguridad operativa

- Escanee solo redes propiedad de la institución y formalmente autorizadas.
- No introduzca rangos de Internet.
- Mantenga el recolector en una VLAN de gestión.
- Prefiera SNMPv3; rote credenciales y tokens.
- No habilite RDP/VNC por conveniencia sin una revisión de riesgos.
- Revise periódicamente `audit_logs`.
- Revoque el recolector desde el panel antes de retirar su máquina.
