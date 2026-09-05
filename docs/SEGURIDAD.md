# Controles de seguridad

Implementados desde el MVP:

| Control | Cómo |
|---|---|
| HTTPS | Obligatorio detrás de Caddy/Nginx. La API puede exigir `HTTPS_ONLY`. |
| Contraseñas | Argon2id. Nunca se guardan contraseñas de usuarios de los PCs. |
| JWT | Access de 15 min. Refresh de 7 días, hasheado, revocable. |
| 2FA | TOTP opcional por usuario. |
| RBAC | Cinco roles. Decoradores en cada ruta. |
| Rate limiting | Login, enrolamiento y rutas de agente. |
| Auditoría | `audit_logs`: fecha, usuario, IP, acción, equipo, resultado. |
| CSRF | Cookie refresh `HttpOnly`, `SameSite=Lax`. API JSON. |
| Validación | Pydantic en todas las entradas. |
| SQLi | SQLAlchemy parametrizado. |
| XSS | React escapa por defecto; cabeceras `Content-Security-Policy`. |
| CORS | Orígenes explícitos. |
| Token por agente | Único, hasheado, revocable. Secreto HMAC cifrado en reposo. |
| Instaladores | SHA-256 obligatorio. Comando aprobado. Confirmación en acciones masivas. |
| Tareas | Firma, caducidad, `task_id` único. Sin comandos shell libres. |
| Least privilege | SOPORTE no carga paquetes ni crea usuarios. VISUALIZADOR/DIRECTIVO no mutan. |
| Alcance de red | Solo CIDR privados autorizados, límite de hosts y confirmación humana. |
| Recolector | Token único hasheado, HTTPS saliente, revocable y separado por sede. |
| SNMP | SNMPv3 preferido; secretos cifrados y nunca devueltos al panel. |
| Soporte remoto | Solo protocolos detectados y preexistentes; sin contraseñas; toda apertura se audita. |

## Lo que esta plataforma no hace

- No captura teclado, portapapeles, contraseñas, cookies ni contenido de navegador.
- No abre puertos hacia los computadores.
- No evade antivirus, EDR ni políticas del SO.
- No habilita RDP/VNC/SSH ni escanea rangos públicos.
- La IA no aísla, limita ni cambia la red por su cuenta.
