"""
M6 — Evidence Automation
=========================
Extracts structured compliance data from regulator PDFs (UIF, BCRA, BACEN).

Pipeline:
  1. PDF bytes → text extraction (PyMuPDF for programmatic PDFs)
  2. LLM structured extraction via orchestrator (task=OCR_EXTRACTION)
  3. Cross-reference extracted obligations against DB obligations
  4. Chain of custody: SHA-256(source_hash + structured_data + timestamp)
  5. Persist EvidenceDocument to DB
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator,
)


EXTRACTION_SYSTEM = """You are a compliance evidence extraction specialist for LATAM regulated industries.
Given regulatory document text, extract structured compliance data in JSON.

You MUST return valid JSON with this exact schema:
{
  "document_type": "circular|resolution|comunicacion|normativa|other",
  "regulator": "string (e.g. BCRA, UIF, BACEN, CMF, SBS)",
  "country": "2-letter ISO code (AR, BR, MX, CL, CO)",
  "reference": "document reference code (e.g. Com. A 7825, Res. 30/2017)",
  "title": "document title",
  "effective_date": "YYYY-MM-DD or null",
  "publication_date": "YYYY-MM-DD or null",
  "subject_sectors": ["list of regulated sectors"],
  "obligations": [
    {
      "description": "clear obligation description",
      "obligation_type": "reporting|record_keeping|capital|kyc|aml|monitoring|other",
      "frequency": "CONTINUOUS|DAILY|WEEKLY|MONTHLY|QUARTERLY|ANNUAL|EVENT_DRIVEN",
      "deadline_rule": "deadline description or null",
      "threshold_amount": "amount with currency or null",
      "penalty_description": "penalty description or null",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL"
    }
  ],
  "key_definitions": {"term": "definition"},
  "cross_references": ["other regulation codes referenced"],
  "summary_es": "2-3 sentence summary in Spanish",
  "confidence": 0
}

Set confidence 0-100 based on text quality (100=perfect text, 50=some OCR artifacts, 20=very degraded).
Return ONLY the JSON object, no markdown."""


def _extract_text_pymupdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Extract text from PDF using PyMuPDF. Returns (text, char_count)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()
        text = "\n\n".join(pages_text).strip()
        return text, len(text)
    except Exception as e:
        return f"[PDF text extraction failed: {e}]", 0


def _compute_custody_hash(
    source_hash: str,
    structured_data: dict,
    timestamp: str,
) -> str:
    canonical = json.dumps(structured_data, sort_keys=True, separators=(",", ":"))
    payload = f"{source_hash}:{canonical}:{timestamp}"
    return hashlib.sha256(payload.encode()).hexdigest()


class EvidenceEngine:
    """M6 — Evidence Automation: extract, structure, and custody-track compliance documents."""

    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def extract_from_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        tenant_id: str,
        regulation_context: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Full pipeline: PDF → text → structured extraction → custody chain → DB persist.

        Returns a dict with success, structured_data, document_id, custody_hash, etc.
        """
        source_hash = hashlib.sha256(pdf_bytes).hexdigest()

        # Dedup: if we've already processed this exact PDF, return the cached result
        existing = await self._find_by_source_hash(source_hash, tenant_id)
        if existing:
            existing["cached"] = True
            return existing

        # Step 1 — Text extraction
        extracted_text, char_count = _extract_text_pymupdf(pdf_bytes)

        if char_count < 50:
            # Scanned PDF — send metadata to model and note limited text
            extracted_text = (
                f"[SCANNED PDF — limited text layer detected]\n"
                f"Filename: {filename}\n"
                f"Context provided: {json.dumps(regulation_context or {})}\n"
                f"Raw text fragment: {extracted_text[:500]}"
            )

        # Step 2 — LLM structured extraction
        context_hint = ""
        if regulation_context:
            context_hint = f"\n\nContext: {json.dumps(regulation_context)}"

        user_prompt = (
            f"Extract structured compliance data from the following regulatory document.\n"
            f"Filename: {filename}{context_hint}\n\n"
            f"--- DOCUMENT TEXT ---\n{extracted_text[:12000]}\n--- END ---"
        )

        infer_result = await self.orch.infer(InferenceRequest(
            task=TaskType.OCR_EXTRACTION,
            system=EXTRACTION_SYSTEM,
            user_prompt=user_prompt,
            tenant_id=tenant_id,
            user_id=user_id,
            temperature=0.1,
            max_tokens=2048,
            json_mode=True,
        ))

        if not infer_result.success:
            return {
                "success": False,
                "error": infer_result.error,
                "source_hash": source_hash,
                "filename": filename,
            }

        structured_data = infer_result.parsed_json or {
            "raw_response": infer_result.response_text,
            "parse_error": "JSON parsing failed",
        }

        # Step 3 — Chain of custody
        now = datetime.now(timezone.utc)
        timestamp_iso = now.isoformat()
        custody_hash = _compute_custody_hash(source_hash, structured_data, timestamp_iso)

        # Step 4 — Cross-reference against known obligations in DB
        obligations_matched = await self._match_obligations(
            structured_data.get("obligations", [])
        )

        # Step 5 — Persist to DB
        doc_id = str(uuid.uuid4())
        db_record = await self._persist(
            doc_id=doc_id,
            tenant_id=tenant_id,
            filename=filename,
            source_hash=source_hash,
            extracted_text_chars=char_count,
            structured_data=structured_data,
            obligations_matched=obligations_matched,
            extraction_model=infer_result.model_used,
            extraction_confidence=structured_data.get("confidence", 0),
            custody_hash=custody_hash,
            custody_timestamp=now,
        )

        # Index extracted text in Qdrant for RAG — best-effort, non-blocking
        try:
            from app.services.rag import get_rag
            await get_rag().index_regulation(
                regulation_id=doc_id,
                country=structured_data.get("country", ""),
                regulator=structured_data.get("regulator", "evidence"),
                code=structured_data.get("reference", filename),
                title=structured_data.get("title", filename),
                text=extracted_text[:20000],
                tenant_id=tenant_id,
            )
        except Exception:
            pass

        return {
            "success": True,
            "document_id": doc_id,
            "filename": filename,
            "source_hash": source_hash,
            "extracted_text_chars": char_count,
            "structured_data": structured_data,
            "obligations_count": len(structured_data.get("obligations", [])),
            "obligations_matched": obligations_matched,
            "custody_hash": custody_hash,
            "custody_timestamp": timestamp_iso,
            "extraction_model": infer_result.model_used,
            "extraction_confidence": structured_data.get("confidence", 0),
            "latency_ms": infer_result.latency_total_ms,
            "cost_usd": infer_result.estimated_cost_usd,
            "db_persisted": db_record,
        }

    async def get_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Retrieve a previously extracted evidence document."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import EvidenceDocument
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = (
                select(EvidenceDocument)
                .where(
                    EvidenceDocument.id == document_id,
                    EvidenceDocument.tenant_id == tenant_id,
                )
            )
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()

        if not doc:
            return {"success": False, "error": "Document not found"}

        return {
            "success": True,
            "document_id": str(doc.id),
            "filename": doc.filename,
            "source_hash": doc.source_hash,
            "extracted_text_chars": doc.extracted_text_chars,
            "structured_data": doc.structured_data,
            "obligations_matched": doc.obligations_matched,
            "extraction_model": doc.extraction_model,
            "extraction_confidence": doc.extraction_confidence,
            "custody_hash": doc.custody_hash,
            "custody_timestamp": doc.custody_timestamp.isoformat(),
            "status": doc.status,
            "created_at": doc.created_at.isoformat(),
        }

    async def list_documents(
        self,
        tenant_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List evidence documents for a tenant, newest first."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import EvidenceDocument
        from sqlalchemy import select, desc

        async with AsyncSessionLocal() as session:
            stmt = (
                select(EvidenceDocument)
                .where(EvidenceDocument.tenant_id == tenant_id)
                .order_by(desc(EvidenceDocument.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            docs = result.scalars().all()

        return {
            "success": True,
            "count": len(docs),
            "documents": [
                {
                    "document_id": str(d.id),
                    "filename": d.filename,
                    "source_hash": d.source_hash,
                    "obligations_count": len((d.structured_data or {}).get("obligations", [])),
                    "extraction_confidence": d.extraction_confidence,
                    "status": d.status,
                    "created_at": d.created_at.isoformat(),
                }
                for d in docs
            ],
        }

    async def _match_obligations(self, extracted_obligations: list[dict]) -> list[dict]:
        """Cross-reference extracted obligation types against DB obligations."""
        if not extracted_obligations:
            return []
        from app.db.base import AsyncSessionLocal
        from app.db.models import Obligation
        from sqlalchemy import select

        # Normalise types: evidence schema uses lowercase, DB uses uppercase
        types = list({
            str(o.get("obligation_type", "")).upper()
            for o in extracted_obligations
            if o.get("obligation_type")
        })
        if not types:
            return []
        try:
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(Obligation)
                    .where(Obligation.obligation_type.in_(types))
                    .limit(50)
                )
                result = await session.execute(stmt)
                db_obligations = result.scalars().all()
            return [
                {
                    "obligation_id": str(ob.id),
                    "obligation_code": ob.obligation_code,
                    "obligation_type": ob.obligation_type,
                    "description": ob.description[:200],
                    "severity": ob.severity.value,
                }
                for ob in db_obligations
            ]
        except Exception:
            return []

    async def _find_by_source_hash(self, source_hash: str, tenant_id: str) -> dict | None:
        """Return formatted document dict if this PDF was already processed."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import EvidenceDocument
        from sqlalchemy import select

        try:
            async with AsyncSessionLocal() as session:
                stmt = select(EvidenceDocument).where(
                    EvidenceDocument.source_hash == source_hash,
                    EvidenceDocument.tenant_id == tenant_id,
                )
                result = await session.execute(stmt)
                doc = result.scalar_one_or_none()
            if not doc:
                return None
            return {
                "success": True,
                "document_id": str(doc.id),
                "filename": doc.filename,
                "source_hash": doc.source_hash,
                "extracted_text_chars": doc.extracted_text_chars,
                "structured_data": doc.structured_data,
                "obligations_matched": doc.obligations_matched or [],
                "obligations_count": len((doc.structured_data or {}).get("obligations", [])),
                "custody_hash": doc.custody_hash,
                "custody_timestamp": doc.custody_timestamp.isoformat(),
                "extraction_model": doc.extraction_model,
                "extraction_confidence": doc.extraction_confidence,
                "db_persisted": True,
            }
        except Exception:
            return None

    async def _persist(
        self,
        doc_id: str,
        tenant_id: str,
        filename: str,
        source_hash: str,
        extracted_text_chars: int,
        structured_data: dict,
        obligations_matched: list,
        extraction_model: str,
        extraction_confidence: int,
        custody_hash: str,
        custody_timestamp: datetime,
    ) -> bool:
        """Insert EvidenceDocument row. Returns True on success."""
        from app.db.base import AsyncSessionLocal
        from app.db.models import EvidenceDocument
        import uuid as _uuid

        try:
            async with AsyncSessionLocal() as session:
                doc = EvidenceDocument(
                    id=_uuid.UUID(doc_id),
                    tenant_id=tenant_id,
                    filename=filename,
                    source_type="pdf",
                    source_hash=source_hash,
                    extracted_text_chars=extracted_text_chars,
                    structured_data=structured_data,
                    obligations_matched=obligations_matched,
                    extraction_model=extraction_model,
                    extraction_confidence=extraction_confidence,
                    custody_hash=custody_hash,
                    custody_timestamp=custody_timestamp,
                    status="extracted",
                )
                session.add(doc)
                await session.commit()
            return True
        except Exception:
            return False
