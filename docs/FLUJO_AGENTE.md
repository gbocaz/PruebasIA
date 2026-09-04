# Flujo agente ↔ servidor

## 1. Enrolamiento

1. Un administrador genera un token de enrolamiento (usos y caducidad limitados).
2. En el PC: `tic-agent enroll --server https://tic.institucion.tld --token <token>`
3. El agente envía hostname, SO, arquitectura y versión.
4. El servidor crea `devices` + `agents`, devuelve `device_id`, token de agente y secreto HMAC.
5. El agente guarda credenciales en disco con permisos restringidos. El token de enrolamiento no se reutiliza más allá de `max_uses`.

## 2. Operación normal

```
loop cada heartbeat (60 s por defecto):
    POST /agent/heartbeat     → actualiza last_seen, métricas, estado
    cada N ciclos:
        POST /agent/inventory → software + interfaces
    GET /agent/tasks
    para cada tarea:
        verificar firma, expiración e idempotencia
        ejecutar (solo tipos conocidos)
        POST /agent/task-result
```

Si el servidor marca el equipo `mantenimiento` o `excluido`, el heartbeat sigue (para no perder visibilidad) pero no se aplican automatizaciones de esas áreas.

## 3. Sin Internet

- El agente no se detiene.
- Eventos y resultados se escriben en una cola local (JSONL).
- Reintentos con *exponential backoff* y jitter (1 s → 60 s máximo).
- Al recuperar conexión, se sincroniza lo pendiente. No hay ráfagas de miles de peticiones.

## 4. Instalación remota

1. Administrador sube el instalador, revisa el SHA-256 y define el comando.
2. Elige destino y confirma.
3. El servidor crea `install_jobs` + `agent_tasks` tipo `install_package`.
4. El agente descarga `/agent/packages/{id}/download`, verifica el hash y **solo entonces** ejecuta el comando aprobado.
5. Nunca ejecuta archivos no aprobados ni comandos arbitrarios.

## 5. Actualización del agente (preparado)

Tarea `update_agent`: descargar binario, verificar hash/firma, reemplazar, reiniciar servicio, reportar versión. Si falla, rollback al binario anterior.
