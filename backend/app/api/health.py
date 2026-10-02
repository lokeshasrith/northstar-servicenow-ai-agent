from fastapi import APIRouter
from sqlalchemy import text

from app.database.session import engine

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database}
