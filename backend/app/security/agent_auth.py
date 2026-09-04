from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.device import Agent, Device
from app.security.tokens import sha256_hex

_bearer = HTTPBearer(auto_error=False)


def get_current_agent(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Agent:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de agente requerido")
    token_hash = sha256_hex(creds.credentials)
    agent = (
        db.query(Agent)
        .options(joinedload(Agent.device).joinedload(Device.agent))
        .filter(Agent.token_hash == token_hash, Agent.revoked.is_(False))
        .one_or_none()
    )
    if agent is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agente no autorizado")
    return agent
