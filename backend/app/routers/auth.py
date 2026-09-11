"""Login endpoint. Not part of openapi.yaml (which predates auth being
added); exists so clients can obtain a bearer token for the endpoints
that now require one."""
from fastapi import APIRouter, HTTPException, status

from .. import models
from ..auth import auth_store

router = APIRouter(tags=["Auth"])


@router.post("/auth/login", response_model=models.Token)
def login(credentials: models.LoginRequest) -> models.Token:
    user = auth_store.authenticate(credentials.username, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    token = auth_store.issue_token(user.username)
    return models.Token(access_token=token)
