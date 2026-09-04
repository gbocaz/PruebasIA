from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300/minute"],
    enabled=get_settings().app_env != "test",
)
