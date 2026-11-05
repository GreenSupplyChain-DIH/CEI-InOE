"""Product endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AuthorisationContext
from app.dependencies import get_authorisation_context, get_registry, get_repository
from app.schemas.product_v1 import (
    PRODUCT_ID,
    PRODUCT_VERSION,
    SiteEnergyQuery,
    SiteEnergySummary,
)
from app.services.site_energy_consumption import build_summary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/site-energy-consumption-summary",
    response_model=SiteEnergySummary,
    summary="Daily site energy consumption summary (v1)",
)
def site_energy_consumption_summary(
    request: Request,
    query: Annotated[SiteEnergyQuery, Query()],
    ctx: AuthorisationContext = Depends(get_authorisation_context),
    registry=Depends(get_registry),
    repository=Depends(get_repository),
) -> SiteEnergySummary:
    max_days = request.app.state.settings.max_days
    days = (query.end_date - query.start_date).days + 1

    audit = request.state.audit
    audit.update(
        product_id=PRODUCT_ID,
        product_version=PRODUCT_VERSION,
        site_alias=query.site,
        date_range_days=days,
    )

    # Reject rather than silently truncate.
    if days > max_days:
        raise HTTPException(
            422,
            f"Date window must not exceed {max_days} days",
        )

    # Unknown and not-permitted sites are indistinguishable to the caller.
    site = registry.get(query.site)
    if site is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    try:
        summary = build_summary(site, query.start_date, query.end_date, repository)
    except SQLAlchemyError:
        logger.exception("Upstream database error")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Data temporarily unavailable")

    audit["result_count"] = len(summary.data)
    return summary
