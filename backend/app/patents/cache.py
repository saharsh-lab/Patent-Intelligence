"""Cache external API responses in PostgreSQL (`api_cache` table).

Patent data changes slowly, quotas are limited, and experiments must be
re-runnable on identical evidence, so every search and detail lookup is cached
for PATENT_CACHE_TTL_HOURS (default one week).
"""

import dataclasses
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import ApiCache
from app.patents.base import PatentRecord, PatentSearchPage


def cache_key(namespace: str, params: dict[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(f"{namespace}|{payload}".encode()).hexdigest()


class ApiCacheStore:
    def __init__(self, session: Session, ttl_hours: int):
        self.session = session
        self.ttl = timedelta(hours=ttl_hours)

    def get(self, namespace: str, params: dict[str, Any]) -> dict | None:
        if self.ttl <= timedelta(0):
            return None
        entry = self.session.get(ApiCache, cache_key(namespace, params))
        if entry is None:
            return None
        if entry.expires_at and entry.expires_at < datetime.now(UTC):
            return None
        return entry.value

    def set(self, namespace: str, params: dict[str, Any], value: dict) -> None:
        if self.ttl <= timedelta(0):
            return
        key = cache_key(namespace, params)
        self.session.execute(delete(ApiCache).where(ApiCache.key == key))
        self.session.add(
            ApiCache(
                key=key,
                namespace=namespace,
                value=value,
                expires_at=datetime.now(UTC) + self.ttl,
            )
        )
        self.session.commit()


# ---------------------------------------------------------------- (de)serialisation


def record_to_json(record: PatentRecord) -> dict:
    data = dataclasses.asdict(record)
    for key in ("publication_date", "filing_date", "priority_date"):
        if data[key]:
            data[key] = data[key].isoformat()
    return data


def record_from_json(data: dict) -> PatentRecord:
    data = dict(data)
    for key in ("publication_date", "filing_date", "priority_date"):
        if data.get(key):
            data[key] = date.fromisoformat(data[key])
    return PatentRecord(**data)


def page_to_json(page: PatentSearchPage) -> dict:
    return {
        "source": page.source,
        "total": page.total,
        "query_string": page.query_string,
        "results": [record_to_json(r) for r in page.results],
    }


def page_from_json(data: dict) -> PatentSearchPage:
    return PatentSearchPage(
        source=data["source"],
        total=data["total"],
        query_string=data["query_string"],
        results=[record_from_json(r) for r in data["results"]],
    )
