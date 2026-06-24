"""
ComplianceOS — Qdrant RAG Service
===================================
Embeds regulatory text via the AIOrchestrator (nvidia/nv-embed-v2, 1024 dims)
and stores/retrieves vectors in Qdrant for Copilot context injection.

Architecture note: all embedding calls go through AIOrchestrator.embed()
to honour rate limiting, cost tracking, and audit trail — same as inference.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from typing import Any

from app.core.config import get_settings

COLLECTION = "regulations"  # legacy global collection name, kept for migration
EMBED_MODEL = "nvidia/nv-embed-v2"
VECTOR_SIZE = 1024
CHUNK_SIZE   = 800   # chars per chunk
CHUNK_OVERLAP = 100  # overlap between consecutive chunks

logger = logging.getLogger(__name__)


def _collection_name(tenant_id: str | None) -> str:
    """Per-tenant Qdrant collection name. Tenant-less regulations (crawler-ingested
    public regulations) live in the shared `_global` collection."""
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", tenant_id) if tenant_id else "global"
    return f"{COLLECTION}_{slug}"


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping ~CHUNK_SIZE-char windows."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]


class RAGService:
    """Async Qdrant RAG — embeddings routed through AIOrchestrator."""

    def __init__(self):
        self._orch = None    # lazy — avoids circular import on module load
        self._qdrant = None  # AsyncQdrantClient, created on first use

    def _get_orch(self):
        if self._orch is None:
            from app.services.ai_orchestrator import get_orchestrator
            self._orch = get_orchestrator()
        return self._orch

    def _get_qdrant(self):
        if self._qdrant is None:
            from qdrant_client import AsyncQdrantClient
            self._qdrant = AsyncQdrantClient(url=get_settings().qdrant_url)
        return self._qdrant

    async def ensure_collection(self, tenant_id: str | None = None) -> bool:
        """Idempotent: create the tenant's Qdrant collection if it doesn't exist."""
        name = _collection_name(tenant_id)
        try:
            from qdrant_client.models import Distance, VectorParams
            client = self._get_qdrant()
            existing = {c.name for c in (await client.get_collections()).collections}
            if name not in existing:
                await client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection '%s'", name)
            return True
        except Exception as e:
            logger.warning("Qdrant ensure_collection('%s') failed: %s", name, e)
            return False

    async def _embed_passage(self, text: str, tenant_id: str) -> list[float] | None:
        vectors = await self._get_orch().embed(
            [text[:2000]], tenant_id=tenant_id, low_priority=True
        )
        return vectors[0] if vectors else None

    async def _embed_query(self, text: str, tenant_id: str) -> list[float] | None:
        vectors = await self._get_orch().embed([text], tenant_id=tenant_id)
        return vectors[0] if vectors else None

    async def index_regulation(
        self,
        regulation_id: str,
        country: str,
        regulator: str,
        code: str,
        title: str,
        text: str,
        tenant_id: str | None = "polkorp",
    ) -> int:
        """Chunk, embed, and upsert a regulation. Returns number of chunks indexed."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

        target = _collection_name(tenant_id)
        client = self._get_qdrant()
        await self.ensure_collection(tenant_id=tenant_id)

        # Remove stale points for this regulation
        try:
            await client.delete(
                collection_name=target,
                points_selector=Filter(
                    must=[FieldCondition(
                        key="regulation_id", match=MatchValue(value=regulation_id)
                    )]
                ),
            )
        except Exception:
            pass

        chunks = _chunk_text(f"{title}\n\n{text}")
        points = []
        for i, chunk in enumerate(chunks):
            vec = await self._embed_passage(chunk, tenant_id=tenant_id)
            if vec is None:
                continue
            point_id = str(uuid.UUID(
                bytes=hashlib.md5(f"{regulation_id}:{i}".encode()).digest()
            ))
            points.append(PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "regulation_id": regulation_id,
                    "tenant_id": tenant_id,
                    "country": country,
                    "regulator": regulator,
                    "code": code,
                    "title": title,
                    "chunk_index": i,
                    "text": chunk,
                },
            ))

        if points:
            await client.upsert(collection_name=target, points=points)
        return len(points)

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 4,
        country_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Embed query and return top-K relevant chunks from the tenant's own
        collection, federated with the shared global (tenant-less) collection."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        vec = await self._embed_query(query, tenant_id=tenant_id)
        if vec is None:
            return []

        country_cond = (
            [FieldCondition(key="country", match=MatchValue(value=country_filter))]
            if country_filter else []
        )

        async def _search(collection: str, must: list) -> list:
            try:
                return await self._get_qdrant().search(
                    collection_name=collection,
                    query_vector=vec,
                    limit=top_k,
                    query_filter=Filter(must=must) if must else None,
                    with_payload=True,
                    score_threshold=0.35,
                )
            except Exception as e:
                logger.warning("Qdrant search('%s') failed: %s", collection, e)
                return []

        own_hits = await _search(
            _collection_name(tenant_id),
            [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))] + country_cond,
        )
        global_hits = []
        if tenant_id:
            global_hits = await _search(_collection_name(None), country_cond)

        hits = sorted(own_hits + global_hits, key=lambda h: h.score, reverse=True)[:top_k]

        return [
            {
                "score": round(h.score, 4),
                "text": h.payload.get("text", ""),
                "regulator": h.payload.get("regulator", ""),
                "code": h.payload.get("code", ""),
                "country": h.payload.get("country", ""),
                "title": h.payload.get("title", ""),
            }
            for h in hits
        ]

    async def context_for_query(
        self,
        question: str,
        tenant_id: str = "polkorp",
        top_k: int = 4,
    ) -> str:
        """Return a formatted context block ready to inject into a Copilot prompt."""
        chunks = await self.retrieve(question, tenant_id=tenant_id, top_k=top_k)
        if not chunks:
            return ""
        lines = ["## Regulatory context (ComplianceOS knowledge base):\n"]
        for i, c in enumerate(chunks, 1):
            lines.append(
                f"[{i}] {c['regulator']} {c['code']} ({c['country']}) — relevance {c['score']}\n"
                f"{c['text']}\n"
            )
        return "\n".join(lines)

    async def index_all_regulations(self, tenant_id: str = "polkorp") -> dict[str, Any]:
        """Re-index every regulation in the DB. Useful for backfill. Returns stats.

        Each regulation is indexed under its own `tenant_id` (None for
        crawler-ingested public regulations, which land in the shared global
        collection) — the `tenant_id` argument here is unused for routing and
        kept only for backward-compatible call signatures.
        """
        from app.db.base import AsyncSessionLocal
        from app.db.models import Regulation
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Regulation))
            regulations = result.scalars().all()

        total_chunks, indexed = 0, []
        for reg in regulations:
            chunks = await self.index_regulation(
                regulation_id=str(reg.id),
                country=reg.country,
                regulator=reg.regulator,
                code=reg.code,
                title=reg.title,
                text=reg.full_text or reg.title,
                tenant_id=reg.tenant_id,
            )
            total_chunks += chunks
            indexed.append({"code": reg.code, "country": reg.country, "chunks": chunks})

            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Regulation)
                    .where(Regulation.id == reg.id)
                    .values(embedding_status="indexed")
                )
                await session.commit()

        return {
            "regulations_indexed": len(indexed),
            "total_chunks": total_chunks,
            "detail": indexed,
        }

    async def migrate_legacy_collection(self) -> dict[str, Any]:
        """One-off migration: move points out of the legacy global '{COLLECTION}'
        collection into the new per-tenant collections, grouped by each point's
        `tenant_id` payload field. Does NOT delete the legacy collection — leaves
        it in place for manual verification/cleanup."""
        from qdrant_client.models import PointStruct

        client = self._get_qdrant()
        try:
            existing = {c.name for c in (await client.get_collections()).collections}
        except Exception as e:
            logger.warning("migrate_legacy_collection: could not list collections: %s", e)
            return {"migrated": 0, "error": str(e)}

        if COLLECTION not in existing:
            return {"migrated": 0, "detail": "legacy collection not found, nothing to migrate"}

        by_collection: dict[str, list[PointStruct]] = {}
        offset = None
        total = 0
        while True:
            records, offset = await client.scroll(
                collection_name=COLLECTION,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            if not records:
                break
            for r in records:
                target = _collection_name(r.payload.get("tenant_id"))
                by_collection.setdefault(target, []).append(
                    PointStruct(id=r.id, vector=r.vector, payload=r.payload)
                )
                total += 1
            if offset is None:
                break

        for target, points in by_collection.items():
            tenant_id = points[0].payload.get("tenant_id") if points else None
            await self.ensure_collection(tenant_id=tenant_id)
            await client.upsert(collection_name=target, points=points)

        return {
            "migrated": total,
            "collections": {name: len(pts) for name, pts in by_collection.items()},
        }


_rag: RAGService | None = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
