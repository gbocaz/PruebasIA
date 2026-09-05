import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.orm import Session

from app.api.routes import api_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.limiter import limiter
from app.seed import seed_if_empty
from app.services.status import refresh_offline_devices

settings = get_settings()
Path("data").mkdir(exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.agent_release_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="TIC Control AI",
    description="Plataforma de administración y supervisión de equipos Windows/Linux. Los agentes inician siempre la comunicación por HTTPS.",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse({"detail": "Demasiadas solicitudes"}, status_code=429),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if settings.https_only and request.url.scheme != "https" and request.headers.get("x-forwarded-proto") != "https":
        if request.url.path not in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return JSONResponse({"detail": "HTTPS obligatorio"}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


def _init():
    if settings.auto_create_schema:
        # Comodidad para SQLite/desarrollo. Producción ejecuta Alembic antes del proceso web.
        Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.on_event("startup")
async def startup():
    _init()

    async def offline_loop():
        while True:
            await asyncio.sleep(30)
            db = SessionLocal()
            try:
                refresh_offline_devices(db)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

    asyncio.create_task(offline_loop())


app.include_router(api_router)
