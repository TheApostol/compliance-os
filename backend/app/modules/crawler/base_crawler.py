"""
Base crawler: fetch, dedup by source_hash, and pipeline orchestration.
Subclasses implement fetch_index() and fetch_document().
"""

from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 30.0
MAX_DOCS_PER_RUN = 20  # cap per run to respect the 40 RPM NVIDIA limit


@dataclass
class IndexEntry:
    url: str
    title: str
    published_at: datetime | None = None


class BaseCrawler(ABC):
    def __init__(self, regulator: str, country: str):
        self.regulator = regulator
        self.country = country

    @abstractmethod
    async def fetch_index(self) -> list[IndexEntry]:
        """Return list of document entries from the regulator's publication page."""
        ...

    @abstractmethod
    async def fetch_document(self, url: str) -> tuple[bytes, str]:
        """Return (content_bytes, content_type) where content_type is 'pdf' or 'html'."""
        ...

    async def run(self, tenant_id: str = "polkorp") -> dict[str, Any]:
        """Fetch index, dedup, parse new documents through M1. Returns run stats."""
        stats: dict[str, Any] = {
            "regulator": self.regulator,
            "country": self.country,
            "crawled": 0,
            "skipped_duplicate": 0,
            "errors": 0,
            "documents": [],
        }

        try:
            index = await self.fetch_index()
        except Exception as e:
            logger.error("%s index fetch failed: %s", self.regulator, e)
            stats["errors"] += 1
            return stats

        for entry in index[:MAX_DOCS_PER_RUN]:
            try:
                content_bytes, content_type = await self.fetch_document(entry.url)
                source_hash = hashlib.sha256(content_bytes).hexdigest()

                if await self._already_processed(source_hash):
                    stats["skipped_duplicate"] += 1
                    continue

                doc_result = await self._process_document(
                    content_bytes=content_bytes,
                    content_type=content_type,
                    title=entry.title,
                    url=entry.url,
                    published_at=entry.published_at,
                    source_hash=source_hash,
                    tenant_id=tenant_id,
                )
                stats["crawled"] += 1
                stats["documents"].append({
                    "title": entry.title,
                    "url": entry.url,
                    "obligations_parsed": doc_result.get("obligations_persisted", 0),
                })
            except Exception as e:
                logger.warning("%s document error %s: %s", self.regulator, entry.url, e)
                stats["errors"] += 1

        return stats

    async def _already_processed(self, source_hash: str) -> bool:
        """True if this exact document (by SHA-256) is already in the DB."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import Regulation
        from sqlalchemy import select, exists as sa_exists

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(sa_exists().where(Regulation.source_hash == source_hash))
                return bool((await session.execute(stmt)).scalar())
        except Exception:
            return False

    async def _process_document(
        self,
        content_bytes: bytes,
        content_type: str,
        title: str,
        url: str,
        published_at: datetime | None,
        source_hash: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Extract text, run M1 parse, store source_hash for dedup."""
        from app.modules.regulatory.engine import RegulatoryIntelligence
        from app.services.ai_orchestrator import get_orchestrator

        if content_type == "pdf":
            from app.modules.evidence.engine import _extract_text_pymupdf
            text, char_count = _extract_text_pymupdf(content_bytes)
            if char_count < 100:
                logger.warning("Scanned/empty PDF skipped: %s", url)
                return {"obligations_persisted": 0}
        else:
            # Strip HTML tags and collapse whitespace
            text = re.sub(r"<[^>]+>", " ", content_bytes.decode("utf-8", errors="replace"))
            text = re.sub(r"\s+", " ", text).strip()

        orch = get_orchestrator()
        m1 = RegulatoryIntelligence(orchestrator=orch)
        result = await m1.parse_regulation(
            country=self.country,
            regulator=self.regulator,
            code=url.rstrip("/").split("/")[-1][:64],
            title=title,
            text=text[:20000],
            tenant_id=tenant_id,
        )

        # Stamp source_hash on the newly created Regulation row so dedup works next run
        if result.get("success"):
            await self._stamp_source_hash(
                country=self.country,
                regulator=self.regulator,
                code=url.rstrip("/").split("/")[-1][:64],
                source_hash=source_hash,
                source_url=url,
            )

        return result

    @staticmethod
    async def _stamp_source_hash(
        country: str, regulator: str, code: str, source_hash: str, source_url: str
    ) -> None:
        from app.db.base import AsyncSessionLocal
        from app.db.models import Regulation
        from sqlalchemy import select, update

        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Regulation)
                    .where(
                        Regulation.country == country,
                        Regulation.regulator == regulator,
                        Regulation.code == code,
                    )
                )
                reg = (await session.execute(stmt)).scalar_one_or_none()
                if reg:
                    await session.execute(
                        update(Regulation)
                        .where(Regulation.id == reg.id)
                        .values(source_hash=source_hash, source_url=source_url)
                    )
                    await session.commit()
        except Exception as e:
            logger.warning("stamp_source_hash failed: %s", e)

    @staticmethod
    async def _get(url: str, timeout: float = CRAWL_TIMEOUT) -> httpx.Response:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "ComplianceOS/0.2 (+https://complianceos.io/bot)"},
        ) as client:
            return await client.get(url)
