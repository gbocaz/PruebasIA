import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
os.environ["SECRET_KEY"] = "unit-test-secret-key-please-change-32bytes"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "CambiarAdmin123!"
os.environ["APP_ENV"] = "test"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

Path("data/packages").mkdir(parents=True, exist_ok=True)
test_db = Path("data/test.db")
if test_db.exists():
    test_db.unlink()
