from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from .. import models
from ..auth import require_auth
from ..store import store

router = APIRouter(tags=["Deals"])


@router.get("/deals", response_model=List[models.Deal])
def list_deals(
    contactId: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
) -> List[models.Deal]:
    return store.list_deals(contact_id=contactId, stage=stage)


@router.post("/deals", response_model=models.Deal, status_code=201)
def create_deal(payload: models.DealInput, _username: str = Depends(require_auth)) -> models.Deal:
    return store.create_deal(payload)


@router.get("/deals/{deal_id}", response_model=models.Deal)
def get_deal(deal_id: str) -> models.Deal:
    return store.get_deal(deal_id)


@router.patch("/deals/{deal_id}", response_model=models.Deal)
def update_deal(
    deal_id: str, payload: models.DealInput, _username: str = Depends(require_auth)
) -> models.Deal:
    return store.update_deal(deal_id, payload)
