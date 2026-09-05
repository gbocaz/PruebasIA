import hashlib
import shlex
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.enums import OsFamily
from app.limiter import limiter
from app.models.deployment import AgentDeploymentKit, AgentRelease
from app.models.device import DeviceGroup
from app.models.user import EnrollmentToken, User, new_id
from app.schemas.deployment import AgentReleaseOut, DeploymentKitCreate, DeploymentKitOut
from app.security.audit import write_audit
from app.security.deps import get_current_user
from app.security.rbac import ADMIN_ROLES, READ_ROLES, client_ip, require_roles
from app.security.tokens import as_utc, new_token, sha256_hex, utcnow

router = APIRouter(prefix="/api/agent-deployment", tags=["agent-deployment"])
bootstrap_router = APIRouter(prefix="/agent/bootstrap", tags=["agent-bootstrap"])
_bootstrap_bearer = HTTPBearer(auto_error=False)


@router.get("/releases", response_model=list[AgentReleaseOut])
def list_releases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_roles(user, READ_ROLES)
    return db.query(AgentRelease).order_by(AgentRelease.created_at.desc()).all()


@router.post("/releases", response_model=AgentReleaseOut, status_code=201)
async def upload_release(
    request: Request,
    version: str = Form(..., min_length=1, max_length=32),
    os_family: OsFamily = Form(...),
    architecture: str = Form(..., min_length=1, max_length=32),
    notes: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    if os_family not in {OsFamily.WINDOWS, OsFamily.LINUX}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Solo se admiten agentes Windows o Linux")
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El binario está vacío")
    if os_family == OsFamily.WINDOWS and not data.startswith(b"MZ"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo no parece un ejecutable Windows PE")
    if os_family == OsFamily.LINUX and not data.startswith(b"\x7fELF"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo no parece un ejecutable Linux ELF")
    if len(data) > settings.max_package_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Binario demasiado grande")
    release_id = new_id()
    directory = Path(settings.agent_release_dir) / release_id
    directory.mkdir(parents=True, exist_ok=True)
    filename = Path(file.filename or ("tic-agent.exe" if os_family == OsFamily.WINDOWS else "tic-agent")).name
    destination = directory / filename
    destination.write_bytes(data)
    row = AgentRelease(
        id=release_id,
        version=version,
        os_family=os_family.value,
        architecture=architecture,
        sha256=hashlib.sha256(data).hexdigest(),
        original_filename=filename,
        storage_path=str(destination),
        size_bytes=len(data),
        notes=notes[:4000],
        created_by=user.id,
        created_at=utcnow(),
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="agent_release_upload",
        target_type="agent_release",
        target_id=row.id,
        details=f"{row.os_family}/{row.architecture} {row.version} sha256={row.sha256}",
    )
    return row


def _public_server_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "URL pública no válida")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "URL pública no válida")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "HTTPS es obligatorio salvo en localhost")
    return value.rstrip("/")


def _linux_script(server: str, token: str, release: AgentRelease) -> str:
    server_q = shlex.quote(server)
    token_q = shlex.quote(token)
    release_q = shlex.quote(release.id)
    sha_q = shlex.quote(release.sha256)
    transport_flags = "--proto '=https' --tlsv1.2" if server.startswith("https://") else ""
    return f"""#!/usr/bin/env sh
set -eu
[ "$(id -u)" -eq 0 ] || {{ echo "Ejecute como root"; exit 1; }}
SERVER={server_q}
TOKEN={token_q}
RELEASE={release_q}
EXPECTED_SHA256={sha_q}
TMP_BINARY="$(mktemp)"
TOKEN_FILE="$(mktemp)"
CURL_CONFIG="$(mktemp)"
cleanup() {{ rm -f "$TMP_BINARY" "$TOKEN_FILE" "$CURL_CONFIG"; }}
trap cleanup EXIT
chmod 600 "$TOKEN_FILE" "$CURL_CONFIG"
printf '%s' "$TOKEN" > "$TOKEN_FILE"
printf 'url = "%s/agent/bootstrap/releases/%s"\\nheader = "Authorization: Bearer %s"\\noutput = "%s"\\n' \
  "$SERVER" "$RELEASE" "$TOKEN" "$TMP_BINARY" > "$CURL_CONFIG"
curl --fail --silent --show-error {transport_flags} --config "$CURL_CONFIG"
printf '%s  %s\\n' "$EXPECTED_SHA256" "$TMP_BINARY" | sha256sum -c -
install -m 0755 "$TMP_BINARY" /usr/local/bin/tic-agent
mkdir -p /etc/tic-control
/usr/local/bin/tic-agent enroll --server "$SERVER" --token-file "$TOKEN_FILE"
cat > /etc/systemd/system/tic-agent.service <<'UNIT'
[Unit]
Description=Agente TIC Control AI
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
ExecStart=/usr/local/bin/tic-agent run --config /etc/tic-control/agent.json
Restart=always
RestartSec=5
User=root
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now tic-agent
echo "TIC Control Agent instalado y activo."
"""


def _windows_script(server: str, token: str, release: AgentRelease) -> str:
    # Las comillas simples de PowerShell se duplican para impedir interpolación.
    server_ps = server.replace("'", "''")
    token_ps = token.replace("'", "''")
    release_ps = release.id.replace("'", "''")
    return f"""# Ejecutar en PowerShell como administrador
$ErrorActionPreference = 'Stop'
$server = '{server_ps}'
$token = '{token_ps}'
$release = '{release_ps}'
$expected = '{release.sha256}'
$destination = 'C:\\Program Files\\TICControl\\tic-agent.exe'
$tokenFile = Join-Path $env:TEMP ('tic-enroll-' + [guid]::NewGuid() + '.token')
New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
try {{
  Invoke-WebRequest -UseBasicParsing `
    -Headers @{{ Authorization = ('Bearer ' + $token) }} `
    -Uri ($server + '/agent/bootstrap/releases/' + $release) `
    -OutFile $destination
  $actual = (Get-FileHash -Algorithm SHA256 $destination).Hash.ToLowerInvariant()
  if ($actual -ne $expected.ToLowerInvariant()) {{ throw 'El hash SHA-256 no coincide.' }}
  Set-Content -NoNewline -Encoding Ascii -Path $tokenFile -Value $token
  & $destination enroll --server $server --token-file $tokenFile
  & $destination install-service
  Start-Service TICControlAgent
  Write-Host 'TIC Control Agent instalado y activo.'
}} finally {{
  Remove-Item -Force -ErrorAction SilentlyContinue $tokenFile
}}
"""


@router.post("/kits", response_model=DeploymentKitOut, status_code=201)
def create_kit(
    request: Request,
    body: DeploymentKitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    release = db.get(AgentRelease, body.release_id)
    if release is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión de agente no encontrada")
    if body.group_id and db.get(DeviceGroup, body.group_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado")
    server = _public_server_url(body.public_server_url)
    token = new_token(24)
    expires_at = utcnow() + timedelta(hours=body.expires_hours)
    enrollment = EnrollmentToken(
        label=f"Despliegue: {body.label}",
        token_hash=sha256_hex(token),
        token_prefix=token[:8],
        max_uses=body.max_uses,
        expires_at=expires_at,
        group_id=body.group_id,
        created_by=user.id,
    )
    db.add(enrollment)
    db.flush()
    kit = AgentDeploymentKit(
        release_id=release.id,
        enrollment_token_id=enrollment.id,
        label=body.label,
        public_server_url=server,
        created_by=user.id,
    )
    db.add(kit)
    db.flush()
    if release.os_family == OsFamily.WINDOWS.value:
        script = _windows_script(server, token, release)
        filename = f"instalar-tic-agent-{release.version}.ps1"
        instructions = [
            "Copie el script únicamente a los equipos autorizados.",
            "Ejecute PowerShell como administrador.",
            "Revise el contenido y ejecute el archivo .ps1.",
        ]
    else:
        script = _linux_script(server, token, release)
        filename = f"instalar-tic-agent-{release.version}.sh"
        instructions = [
            "Copie el script únicamente a los equipos autorizados.",
            "Revise el contenido.",
            "Ejecute: sudo sh ./instalar-tic-agent.sh",
        ]
    write_audit(
        db,
        user=user,
        ip=client_ip(request),
        action="agent_deployment_kit_create",
        target_type="agent_release",
        target_id=release.id,
        details=f"kit={kit.id}; max_uses={body.max_uses}; expires={expires_at.isoformat()}",
    )
    return DeploymentKitOut(
        kit_id=kit.id,
        release_id=release.id,
        release_version=release.version,
        os_family=release.os_family,
        architecture=release.architecture,
        sha256=release.sha256,
        token=token,
        token_prefix=token[:8],
        expires_at=expires_at,
        install_script=script,
        filename=filename,
        instructions=instructions,
    )


@bootstrap_router.get("/releases/{release_id}")
@limiter.limit("30/minute")
def download_agent_release(
    release_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bootstrap_bearer),
    db: Session = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de despliegue requerido")
    token_hash = sha256_hex(credentials.credentials)
    kit = (
        db.query(AgentDeploymentKit)
        .join(EnrollmentToken, EnrollmentToken.id == AgentDeploymentKit.enrollment_token_id)
        .filter(
            AgentDeploymentKit.release_id == release_id,
            EnrollmentToken.token_hash == token_hash,
        )
        .one_or_none()
    )
    now = utcnow()
    enrollment = kit.enrollment_token if kit else None
    if (
        kit is None
        or enrollment is None
        or enrollment.revoked_at is not None
        or (enrollment.expires_at and as_utc(enrollment.expires_at) < now)
        or enrollment.use_count >= enrollment.max_uses
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de despliegue inválido o caducado")
    release = kit.release
    path = Path(release.storage_path)
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Binario del agente no disponible")
    return FileResponse(path, filename=release.original_filename, media_type="application/octet-stream")
