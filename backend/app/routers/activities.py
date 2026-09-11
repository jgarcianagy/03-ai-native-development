from fastapi import APIRouter, Depends

from .. import models
from ..auth import require_auth
from ..store import store

router = APIRouter(tags=["Activities"])


@router.post("/activities", response_model=models.Activity, status_code=201)
def create_activity(
    payload: models.ActivityInput, _username: str = Depends(require_auth)
) -> models.Activity:
    return store.create_activity(payload)
