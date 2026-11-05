"""Liveness and readiness endpoints (for edge orchestration only; never route publicly)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_repository

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready(repository=Depends(get_repository)) -> dict:
    # Deliberately generic: no connection details are leaked.
    if not repository.ping():
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}
