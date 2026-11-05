"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.auth import AuthorisationContext
from app.repositories.energy_repository import EnergyRepository
from app.services.site_access import SiteRegistry


def get_authorisation_context(request: Request) -> AuthorisationContext:
    """Authenticate the connector, apply the rate limit and record audit context."""
    state = request.app.state
    ctx = state.authenticator.authenticate(request)

    audit = request.state.audit
    audit.update(
        connector_subject=ctx.connector_subject,
        consumer_participant_id=ctx.participant_id,
        purpose=ctx.purpose,
        policy_or_contract_id=ctx.contract_id,
    )
    if ctx.request_id:
        audit["request_id"] = ctx.request_id

    if not state.rate_limiter.allow(ctx.connector_subject):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
    return ctx


def get_registry(request: Request) -> SiteRegistry:
    return request.app.state.registry


def get_repository(request: Request) -> EnergyRepository:
    return request.app.state.repository
