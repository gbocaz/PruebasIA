from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.network import NetworkCollector
from app.security.tokens import sha256_hex

_bearer = HTTPBearer(auto_error=False)


def get_current_collector(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> NetworkCollector:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de recolector requerido")
    collector = (
        db.query(NetworkCollector)
        .filter(
            NetworkCollector.token_hash == sha256_hex(creds.credentials),
            NetworkCollector.revoked.is_(False),
        )
        .one_or_none()
    )
    if collector is None or not collector.site.enabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Recolector no autorizado")
    return collector
