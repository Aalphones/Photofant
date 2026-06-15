from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION)
