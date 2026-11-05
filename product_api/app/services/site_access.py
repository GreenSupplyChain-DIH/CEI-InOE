"""Product-site registry: pseudonymous alias -> allow-listed local datasources.

The registry file is sensitive configuration (it links public aliases to
internal datasource ids). Mount it as a secret; never commit the real file or
expose it through the API. See ``policies/site_product_registry.example.yaml``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatasourceConfig:
    id: int
    # Timezone in which ``fact_energy_hourly.ts`` is stored for this datasource.
    # Naive local time today (assumed Asia/Nicosia, to be verified); set to
    # "UTC" per datasource once its data has been migrated to UTC.
    ts_timezone: str


@dataclass(frozen=True)
class SiteConfig:
    alias: str
    timezone: str  # reporting timezone that defines the calendar day
    datasources: tuple[DatasourceConfig, ...]


class SiteRegistry:
    def __init__(self, sites: dict[str, SiteConfig]):
        self._sites = sites

    def get(self, alias: str) -> SiteConfig | None:
        return self._sites.get(alias)

    def __len__(self) -> int:
        return len(self._sites)

    @classmethod
    def from_dict(cls, raw: dict) -> "SiteRegistry":
        sites: dict[str, SiteConfig] = {}
        for alias, entry in (raw.get("sites") or {}).items():
            tz = _checked_tz(entry["timezone"], alias)
            sources = tuple(
                DatasourceConfig(
                    id=int(ds["id"]),
                    ts_timezone=_checked_tz(ds.get("ts_timezone", tz), alias),
                )
                for ds in entry.get("datasources", [])
            )
            if not sources:
                raise ValueError(f"site '{alias}' has no datasources")
            sites[alias] = SiteConfig(alias=alias, timezone=tz, datasources=sources)
        return cls(sites)

    @classmethod
    def from_file(cls, path: str | Path) -> "SiteRegistry":
        with open(path, "r", encoding="utf-8") as fh:
            registry = cls.from_dict(yaml.safe_load(fh) or {})
        # Log only a count: aliases and datasource ids are sensitive.
        logger.info("Loaded site registry with %d site(s)", len(registry))
        return registry


def _checked_tz(name: str, alias: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"site '{alias}': unknown timezone '{name}'") from exc
    return name
