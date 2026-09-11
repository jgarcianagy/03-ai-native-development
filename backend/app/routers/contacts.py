from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from .. import models
from ..auth import require_auth
from ..store import store

router = APIRouter(tags=["Contacts"])


@router.get("/contacts", response_model=List[models.Contact])
def list_contacts(
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags"),
) -> List[models.Contact]:
    tag_list = tags.split(",") if tags else None
    return store.list_contacts(search=search, tags=tag_list)


@router.post("/contacts", response_model=models.Contact, status_code=201)
def create_contact(
    payload: models.ContactInput, _username: str = Depends(require_auth)
) -> models.Contact:
    return store.create_contact(payload)


@router.get("/contacts/{contact_id}", response_model=models.Contact)
def get_contact(contact_id: str) -> models.Contact:
    return store.get_contact(contact_id)


@router.patch("/contacts/{contact_id}", response_model=models.Contact)
def update_contact(
    contact_id: str,
    payload: models.ContactInput,
    _username: str = Depends(require_auth),
) -> models.Contact:
    return store.update_contact(contact_id, payload)


@router.get("/contacts/{contact_id}/activities", response_model=List[models.Activity])
def list_activities(contact_id: str) -> List[models.Activity]:
    return store.list_activities(contact_id)


@router.get("/tags", response_model=List[str])
def list_tags() -> List[str]:
    return store.list_tags()
