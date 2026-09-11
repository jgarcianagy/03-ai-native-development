from fastapi import APIRouter

from .. import models
from ..store import store

router = APIRouter(tags=["Pipeline"])


@router.get("/pipeline", response_model=models.Pipeline)
def get_pipeline() -> models.Pipeline:
    return store.get_pipeline()
