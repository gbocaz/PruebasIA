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

## Reservado (fases 4-7)

Red, mapa, IA, archivos, informes avanzados: el menú puede mostrarlos deshabilitados para no fingir módulos vacíos.
