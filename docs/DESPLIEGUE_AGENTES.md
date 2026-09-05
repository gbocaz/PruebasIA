# Despliegue separado del agente TIC Control

## Objetivo

El agente TIC Control **no es un paquete de software institucional común**. Tiene su propio módulo:

```text
Equipos detectados en Red
        ↓
Despliegue de agentes
        ↓
Binario aprobado + SHA-256
        ↓
Kit temporal Windows/Linux
        ↓
Enrolamiento individual
        ↓
Equipo administrado
```

Los paquetes de Chrome, LibreOffice u otras aplicaciones siguen en **Software → Paquetes**. Las versiones de `tic-agent` se administran en **Desplegar agentes**.

## Qué permite el agente

- heartbeat y estado online/offline;
- inventario de hardware, interfaces y software;
- CPU, RAM, disco y tiempo encendido;
- historial y alertas;
- pertenencia a grupos;
- instalar paquetes previamente aprobados;
- actualizar inventario;
- reiniciar el servicio del agente;
- recibir futuras acciones administrativas tipadas.

No acepta una consola de comandos arbitrarios. Una plataforma que “pueda hacer todo” sin restricciones sería equivalente a una puerta trasera. Cada capacidad nueva debe tener:

1. tipo de tarea explícito;
2. parámetros validados;
3. rol permitido;
4. confirmación proporcional al impacto;
5. firma y caducidad;
6. resultado y auditoría.

La pantalla se atiende mediante RDP/VNC/SSH ya habilitados y autorizados, no mediante acceso oculto.

## Etapa 1 — compilar los binarios aprobados

Requiere Go 1.24 o posterior.

### Linux amd64

```bash
cd agent
go test ./...
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
  go build -trimpath -ldflags="-s -w" \
  -o dist/tic-agent-linux-amd64 ./cmd/tic-agent
sha256sum dist/tic-agent-linux-amd64
```

### Windows amd64

```bash
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 \
  go build -trimpath -ldflags="-s -w" \
  -o dist/tic-agent-windows-amd64.exe ./cmd/tic-agent
sha256sum dist/tic-agent-windows-amd64.exe
```

Qué hace: genera ejecutables independientes. Conserve los hashes del proceso de compilación y, para producción, firme el `.exe` con el certificado institucional de firma de código.

## Etapa 2 — cargar una versión

1. Inicie sesión como `SUPERADMIN` o `ADMINISTRADOR TIC`.
2. Abra **Desplegar agentes**.
3. Indique versión, sistema y arquitectura.
4. Seleccione el binario correspondiente.
5. Pulse **Cargar y calcular SHA-256**.
6. Compare el hash mostrado con el hash de compilación.

Qué hace: guarda el binario en el repositorio separado `agent-releases`, calcula SHA-256 y registra administrador, fecha, plataforma y versión.

## Etapa 3 — generar un kit temporal

1. Seleccione la versión aprobada.
2. Escriba una etiqueta, por ejemplo `Laboratorio 1 septiembre`.
3. Indique la URL HTTPS pública del servidor.
4. Seleccione el grupo inicial.
5. Limite la cantidad máxima de instalaciones.
6. Configure una caducidad corta.
7. Pulse **Generar instalador**.
8. Descargue el `.ps1` o `.sh`; el token solo se muestra en esa respuesta.

Qué contiene el script:

- URL del servidor;
- token de enrolamiento limitado;
- identificador de la versión;
- hash SHA-256 esperado;
- pasos visibles para instalar y registrar el servicio.

No contiene contraseñas de administradores ni credenciales permanentes del agente.

## Etapa 4 — instalar en Windows

1. Revise el script descargado.
2. Cópielo al equipo autorizado por GPO, Intune, herramienta RMM existente o manualmente.
3. Abra PowerShell como administrador.
4. Ejecute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\instalar-tic-agent-VERSION.ps1
```

El script:

1. descarga el binario usando el token temporal;
2. verifica SHA-256;
3. rechaza el archivo si el hash difiere;
4. guarda el token en un archivo temporal;
5. enrola el equipo;
6. elimina el token temporal;
7. instala e inicia `TICControlAgent`.

Verificación:

```powershell
Get-Service TICControlAgent
Get-Content "$env:ProgramData\TICControl\agent.json"
```

El archivo de configuración contiene la credencial individual emitida después del enrolamiento. Restrinja sus permisos a `SYSTEM` y administradores.

## Etapa 5 — instalar en Linux

Revise y ejecute:

```bash
sudo sh ./instalar-tic-agent-VERSION.sh
```

El script:

1. exige `root`;
2. descarga por HTTPS;
3. verifica SHA-256;
4. instala `/usr/local/bin/tic-agent`;
5. enrola con un archivo de token temporal `0600`;
6. crea una unidad systemd visible;
7. habilita e inicia `tic-agent`.

Verificación:

```bash
sudo systemctl status tic-agent
sudo journalctl -u tic-agent -n 50
sudo stat /etc/tic-control/agent.json
```

## Etapa 6 — vinculación con equipos detectados

El módulo **Red** descubre dispositivos sin agente. Después de instalar el agente:

1. el primer heartbeat informa la MAC;
2. el backend busca la misma MAC en `network_devices`;
3. marca el dispositivo como **Con agente**;
4. la ficha de red ofrece **Abrir equipo administrado**.

La vinculación no se realiza solo por IP porque sedes diferentes pueden reutilizar direcciones privadas.

## Distribución masiva

Para múltiples equipos:

- cree un kit con `max_uses` igual al lote;
- use GPO/Intune para Windows;
- use Ansible, SSH administrativo o su gestor de configuración para Linux;
- no envíe el script por correo o canales públicos;
- revoque el token al terminar;
- revise `agent_deployment_kit_create` y los enrolamientos en Auditoría.

No se intenta instalar automáticamente en todos los equipos descubiertos. Un sondeo de red no demuestra que exista autorización administrativa ni un canal seguro de instalación.

## Diagnóstico

### El hash no coincide

No continúe. Elimine el archivo, revise proxy/caché y vuelva a cargar el binario aprobado.

### El token caducó

Genere un kit nuevo. No amplíe tokens antiguos innecesariamente.

### El equipo aparece en Red pero no se vincula

Compare la MAC reportada por el agente y la detectada por ARP/SNMP. Interfaces Wi-Fi/Ethernet distintas pueden tener MAC diferentes; en ese caso la futura asociación manual deberá requerir confirmación y auditoría.

### El servicio no inicia

Windows:

```powershell
Get-WinEvent -LogName Application -MaxEvents 50
Get-Service TICControlAgent
```

Linux:

```bash
sudo systemctl status tic-agent
sudo journalctl -u tic-agent --since "15 minutes ago"
```
