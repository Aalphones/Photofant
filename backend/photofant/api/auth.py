"""GET /api/auth/status, POST /api/auth/unlock — password gate."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from photofant.settings import load_settings

router = APIRouter(prefix="/auth")


class AuthStatusResponse(BaseModel):
    has_password: bool


class UnlockRequest(BaseModel):
    password: str


class UnlockResponse(BaseModel):
    success: bool


@router.get("/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    """Returns whether a password is configured. Never reveals the password itself."""
    settings = load_settings()
    return AuthStatusResponse(has_password=bool(settings.get("password")))


@router.post("/unlock", response_model=UnlockResponse)
def unlock(body: UnlockRequest) -> UnlockResponse:
    """Check the submitted password against the stored one."""
    settings = load_settings()
    stored = settings.get("password")
    if not stored:
        return UnlockResponse(success=True)
    return UnlockResponse(success=body.password == stored)
