# Pantallas principales — TIC Control AI

Diseño sencillo: menú izquierdo, tarjetas grandes, tablas claras. Verde / amarillo / rojo / gris.

## Login

Usuario, contraseña y, si aplica, código 2FA. Sin elementos decorativos innecesarios.

## Dashboard

1. Totales: equipos, online, offline, alertas, programas detectados.
2. Equipos con mayor uso de CPU/RAM/disco (valores numéricos visibles).
3. Alertas recientes.
4. Software más instalado.
5. Accesos rápidos a instalaciones pendientes.

## Equipos

Tabla filtrable (estado, SO, grupo, búsqueda). Clic abre la ficha.

## Ficha de equipo

Cabecera: hostname, estado, SO, IP, MAC, usuario, última conexión, CPU/RAM/disco.

Pestañas: Resumen, Software, Red (interfaces), Eventos, Historial, Acciones.

Acciones con confirmación cuando el impacto es alto: actualizar inventario, instalar paquete, reiniciar servicio del agente.

## Software

Catálogo con categoría. Consultas: “¿en cuántos equipos está Chrome?”, “¿quién no tiene LibreOffice?”, “software no autorizado”.

## Paquetes e instalaciones

Carga de instalador, hash SHA-256, comando aprobado, destino (equipo, grupo o todos) y progreso por equipo.

## Grupos, Alertas, Usuarios, Auditoría, Configuración

CRUD de grupos y exclusiones; bandeja de alertas; RBAC; log de auditoría; tokens de enrolamiento.

## Red

Sedes, CIDR autorizados, recolectores, perfiles SNMP, ejecución confirmada de escaneos, inventario multi-marca y relaciones LLDP/CDP.

La ficha de red muestra IP, MAC, fabricante, modelo, serie, puertos y protocolos preexistentes. RDP descarga un archivo sin contraseña; VNC, SSH y web abren el cliente correspondiente después de confirmar y registrar la acción.

## Reservado (fases 4-7)

Adaptadores propietarios por versión, analítica de tráfico, IA, archivos e informes avanzados quedan reservados; no se muestran como funciones terminadas.
