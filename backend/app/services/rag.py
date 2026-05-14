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
import uuid
from typing import Any

from app.core.config import get_settings

COLLECTION = "regulations"
EMBED_MODEL = "nvidia/nv-embed-v2"
VECTOR_SIZE = 1024
CHUNK_SIZE   = 800   # chars per chunk
CHUNK_OVERLAP = 100  # overlap between consecutive chunks

logger = logging.getLogger(__name__)


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

    async def ensure_collection(self) -> bool:
        """Idempotent: create the Qdrant collection if it doesn't exist."""
        try:
            from qdrant_client.models import Distance, VectorParams
            client = self._get_qdrant()
            existing = {c.name for c in (await client.get_collections()).collections}
            if COLLECTION not in existing:
                await client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection '%s'", COLLECTION)
            return True
        except Exception as e:
            logger.warning("Qdrant ensure_collection failed: %s", e)
            return False

    async def _embed_passage(self, text: str, tenant_id: str) -> list[float] | None:
        vectors = await self._get_orch().embed([text[:2000]], tenant_id=tenant_id)
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
        tenant_id: str = "polkorp",
    ) -> int:
        """Chunk, embed, and upsert a regulation. Returns number of chunks indexed."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct

        client = self._get_qdrant()

        # Remove stale points for this regulation
        try:
            await client.delete(
                collection_name=COLLECTION,
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
            await client.upsert(collection_name=COLLECTION, points=points)
        return len(points)

    async def retrieve(
        self,
        query: str,
        tenant_id: str,
        top_k: int = 4,
        country_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Embed query and return top-K relevant chunks filtered by tenant."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        vec = await self._embed_query(query, tenant_id=tenant_id)
        if vec is None:
            return []

        must = [FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
        if country_filter:
            must.append(FieldCondition(key="country", match=MatchValue(value=country_filter)))

        try:
            hits = await self._get_qdrant().search(
                collection_name=COLLECTION,
                query_vector=vec,
                limit=top_k,
                query_filter=Filter(must=must),
                with_payload=True,
                score_threshold=0.35,
            )
        except Exception as e:
            logger.warning("Qdrant search failed: %s", e)
            return []

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
        """Re-index every regulation in the DB. Useful for backfill. Returns stats."""
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
                tenant_id=tenant_id,
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


_rag: RAGService | None = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
