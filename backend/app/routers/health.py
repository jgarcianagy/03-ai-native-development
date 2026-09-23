import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .. import database

router = APIRouter(tags=["Health"])

# Set at deploy time (deploy/gcp.sh) so CI can confirm the new revision is live.
APP_VERSION = os.environ.get("APP_VERSION", "dev")


@router.get("/health")
def get_health() -> JSONResponse:
    """Liveness + database connectivity. 503 if the database is unreachable."""
    try:
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable", "version": APP_VERSION})
    return JSONResponse(status_code=200, content={"status": "ok", "version": APP_VERSION})
