"""Structured audit logging (one JSON record per product request) and rate limiting.

Records never contain secrets, tokens or raw data rows.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

audit_logger = logging.getLogger("product_api.audit")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def configure_audit_logging() -> None:
    """Send audit records to stdout as bare JSON lines (idempotent)."""
    if audit_logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False


def resolve_request_id(incoming: str | None) -> str:
    """Use a well-formed incoming X-Request-ID (correlation only, not trusted for authorisation)."""
    if incoming and _REQUEST_ID_RE.match(incoming):
        return incoming
    return str(uuid.uuid4())


def emit_audit(fields: dict, status_code: int) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request_id": None,
        "product_id": None,
        "product_version": None,
        "connector_subject": None,
        "consumer_participant_id": None,
        "purpose": None,
        "policy_or_contract_id": None,
        "site_alias": None,
        "date_range_days": None,
        "result_count": None,
        **fields,
        "outcome": "allowed" if status_code < 400 else "denied" if status_code < 500 else "error",
        "status_code": status_code,
    }
    audit_logger.info(json.dumps(record, default=str))


class RateLimiter:
    """Per-subject sliding one-minute window (in-memory, single process)."""

    def __init__(self, per_minute: int):
        self._limit = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, subject: str) -> bool:
        if self._limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            hits = self._hits[subject]
            while hits and now - hits[0] > 60:
                hits.popleft()
            if len(hits) >= self._limit:
                return False
            hits.append(now)
            return True
