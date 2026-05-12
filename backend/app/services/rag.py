"""
ComplianceOS — Qdrant RAG Service
===================================
Embeddings: nvidia/nv-embedqa-e5-v5 (1024 dims, asymmetric query/passage)
Vector DB: Qdrant (local container)

Usage:
  - Index a regulation:    await rag.index_regulation(reg_id, text, metadata)
  - Retrieve context:      chunks = await rag.retrieve(query, top_k=5)
  - Copilot integration:   context_block = await rag.context_for_query(question)
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)

from app.core.config import get_settings

COLLECTION = "regulations"
EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
VECTOR_SIZE = 1024
CHUNK_SIZE  = 800   # chars
CHUNK_OVERLAP = 100


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of ~CHUNK_SIZE chars."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c) > 50]


class RAGService:
    """Thin wrapper around Qdrant + NVIDIA embeddings."""

    def __init__(self):
        s = get_settings()
        self._openai = AsyncOpenAI(
            base_url=s.nvidia_base_url,
            api_key=s.nvidia_api_key or "missing",
            timeout=30.0,
        )
        self._qdrant = QdrantClient(url=s.qdrant_url)
        self._ensure_collection()

    def _ensure_collection(self):
        existing = {c.name for c in self._qdrant.get_collections().collections}
        if COLLECTION not in existing:
            self._qdrant.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )

    async def _embed(self, text: str, input_type: str = "passage") -> list[float]:
        resp = await self._openai.embeddings.create(
            model=EMBED_MODEL,
            input=text[:2000],  # model hard limit
            encoding_format="float",
            extra_body={"input_type": input_type, "truncate": "END"},
        )
        return resp.data[0].embedding

    async def index_regulation(
        self,
        regulation_id: str,
        country: str,
        regulator: str,
        code: str,
        title: str,
        text: str,
    ) -> int:
        """Chunk, embed, and upsert a regulation into Qdrant. Returns chunk count."""
        # Remove stale points for this regulation first
        self._qdrant.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="regulation_id", match=MatchValue(value=regulation_id))]
            ),
        )

        chunks = _chunk_text(f"{title}\n\n{text}")
        points = []
        for i, chunk in enumerate(chunks):
            vec = await self._embed(chunk, input_type="passage")
            point_id = str(uuid.UUID(
                bytes=hashlib.md5(f"{regulation_id}:{i}".encode()).digest()
            ))
            points.append(PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "regulation_id": regulation_id,
                    "country": country,
                    "regulator": regulator,
                    "code": code,
                    "title": title,
                    "chunk_index": i,
                    "text": chunk,
                },
            ))

        if points:
            self._qdrant.upsert(collection_name=COLLECTION, points=points)
        return len(points)

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        country_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Embed query, retrieve top-K relevant regulation chunks."""
        vec = await self._embed(query, input_type="query")

        search_filter = None
        if country_filter:
            search_filter = Filter(
                must=[FieldCondition(key="country", match=MatchValue(value=country_filter))]
            )

        hits = self._qdrant.search(
            collection_name=COLLECTION,
            query_vector=vec,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
            score_threshold=0.4,
        )
        return [
            {
                "score": h.score,
                "text": h.payload.get("text", ""),
                "regulator": h.payload.get("regulator"),
                "code": h.payload.get("code"),
                "country": h.payload.get("country"),
                "title": h.payload.get("title"),
            }
            for h in hits
        ]

    async def context_for_query(
        self,
        question: str,
        top_k: int = 4,
    ) -> str:
        """Return a formatted context block ready to inject into a Copilot prompt."""
        chunks = await self.retrieve(question, top_k=top_k)
        if not chunks:
            return ""

        lines = ["## Regulatory context retrieved from ComplianceOS knowledge base:\n"]
        for i, c in enumerate(chunks, 1):
            lines.append(
                f"[{i}] {c['regulator']} {c['code']} ({c['country']}) — score {c['score']:.2f}\n"
                f"{c['text']}\n"
            )
        return "\n".join(lines)

    async def index_all_regulations(self) -> dict[str, Any]:
        """Re-index every regulation currently in the DB. Returns stats."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import Regulation
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Regulation))
            regulations = result.scalars().all()

        total_chunks = 0
        indexed = []
        for reg in regulations:
            text = reg.full_text or reg.title
            chunks = await self.index_regulation(
                regulation_id=str(reg.id),
                country=reg.country,
                regulator=reg.regulator,
                code=reg.code,
                title=reg.title,
                text=text,
            )
            total_chunks += chunks
            indexed.append({"code": reg.code, "country": reg.country, "chunks": chunks})

            # Mark as indexed in DB
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Regulation)
                    .where(Regulation.id == reg.id)
                    .values(embedding_status="indexed")
                )
                await session.commit()

        return {"regulations_indexed": len(indexed), "total_chunks": total_chunks, "detail": indexed}


_rag: RAGService | None = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
