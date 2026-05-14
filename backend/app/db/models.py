"""
ComplianceOS — Domain Models

Core idea: regulation as structured data. Not PDFs. Not text.
Machine-readable obligations that AI agents and humans can act on.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, Integer, Boolean,
    ForeignKey, Enum as SAEnum, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


# ═══════════════════════════════════════════════════════════════════
# TENANT
# ═══════════════════════════════════════════════════════════════════

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(64))
    jurisdictions = Column(JSONB, default=list)
    data_residency_policy = Column(JSONB, default=dict)
    config = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════
# M1 — REGULATORY INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════

class ObligationSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ObligationFrequency(str, enum.Enum):
    CONTINUOUS = "CONTINUOUS"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class Regulation(Base):
    """The source: a specific regulatory document (Comunicación A, Resolución, etc.)"""
    __tablename__ = "regulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country = Column(String(2), nullable=False, index=True)
    regulator = Column(String(64), nullable=False, index=True)
    code = Column(String(128), nullable=False)
    title = Column(String(512), nullable=False)
    sector = Column(String(64))
    published_at = Column(DateTime(timezone=True))
    effective_from = Column(DateTime(timezone=True))
    source_url = Column(String(1024))
    source_hash = Column(String(64))
    full_text = Column(String)
    embedding_status = Column(String(32), default="pending")
    metadata_json = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    obligations = relationship("Obligation", back_populates="regulation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_regulation_country_regulator", "country", "regulator"),
    )


class Obligation(Base):
    """Machine-readable obligation extracted from a regulation. The atomic unit of compliance."""
    __tablename__ = "obligations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_id = Column(UUID(as_uuid=True), ForeignKey("regulations.id"), nullable=False)

    obligation_code = Column(String(64), nullable=False)
    obligation_type = Column(String(64), nullable=False)
    description = Column(String, nullable=False)
    frequency = Column(SAEnum(ObligationFrequency), nullable=False)
    deadline_rule = Column(String(255))
    severity = Column(SAEnum(ObligationSeverity), nullable=False)
    applies_to_sectors = Column(JSONB, default=list)
    evidence_required = Column(JSONB, default=list)
    controls_required = Column(JSONB, default=list)
    penalty_range_usd = Column(String(128))
    parent_obligation_id = Column(UUID(as_uuid=True), ForeignKey("obligations.id"), nullable=True)
    extracted_by_model = Column(String(128))
    verified_by_human = Column(Boolean, default=False)
    verified_by_user_id = Column(String(64))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    regulation = relationship("Regulation", back_populates="obligations")

    __table_args__ = (
        Index("ix_obligation_code", "obligation_code"),
        Index("ix_obligation_type_severity", "obligation_type", "severity"),
    )


# ═══════════════════════════════════════════════════════════════════
# M3 — KYC/AML CASES
# ═══════════════════════════════════════════════════════════════════

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    CLOSED_NO_ACTION = "CLOSED_NO_ACTION"
    REPORTED = "REPORTED"
    REJECTED = "REJECTED"


class ComplianceCase(Base):
    """A KYC/AML investigation or onboarding case."""
    __tablename__ = "compliance_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    case_code = Column(String(64), unique=True, nullable=False)
    subject_type = Column(String(32))
    subject_identifier = Column(String(255))
    risk_level = Column(SAEnum(RiskLevel), nullable=False, index=True)
    status = Column(SAEnum(CaseStatus), default=CaseStatus.OPEN, index=True)
    ai_risk_score = Column(Integer)
    ai_analysis = Column(JSONB, default=dict)
    red_flags = Column(JSONB, default=list)
    obligations_triggered = Column(JSONB, default=list)
    assigned_to_user_id = Column(String(64))
    requires_human_review = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True))


# ═══════════════════════════════════════════════════════════════════
# M5 — AI GOVERNANCE: MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════

class AIModelRegistry(Base):
    """Track every AI model in use, version, evaluation scores. Required for AI governance."""
    __tablename__ = "ai_model_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(String(255), nullable=False, index=True)
    provider = Column(String(64), nullable=False)
    version_hash = Column(String(64))
    use_cases = Column(JSONB, default=list)
    benchmark_scores = Column(JSONB, default=dict)
    approved_for_production = Column(Boolean, default=False)
    approved_by_user_id = Column(String(64))
    approved_at = Column(DateTime(timezone=True))
    deprecated = Column(Boolean, default=False)
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════
# M6 — EVIDENCE AUTOMATION
# ═══════════════════════════════════════════════════════════════════

class EvidenceDocument(Base):
    """
    M6 — Structured evidence extracted from regulator PDFs.
    Includes chain of custody: source hash + extraction hash + timestamp.
    """
    __tablename__ = "evidence_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    filename = Column(String(512), nullable=False)
    source_type = Column(String(32), default="pdf")
    source_hash = Column(String(64), nullable=False, index=True)  # SHA-256 of raw input bytes

    # Extraction results
    extracted_text_chars = Column(Integer, nullable=False, default=0)
    structured_data = Column(JSONB, default=dict)       # AI-parsed compliance data
    obligations_matched = Column(JSONB, default=list)   # obligation_codes cross-referenced

    extraction_model = Column(String(128))
    extraction_confidence = Column(Integer, default=0)  # 0-100 from AI

    # Chain of custody — tamper-evident
    custody_hash = Column(String(64), nullable=False, unique=True)
    custody_timestamp = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(32), default="extracted", index=True)  # extracted | verified | rejected
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_evidence_tenant_created", "tenant_id", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE GRAPH
# ═══════════════════════════════════════════════════════════════════

class GraphVertex(Base):
    """
    Graph node. vertex_type: regulation | obligation | entity | control | regulator
    entity_id references the PK of the source table (regulation.id, obligation.id, etc.)
    """
    __tablename__ = "graph_vertices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vertex_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)    # FK by convention only
    label = Column(String(255), nullable=False)
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_vertex_type_entity", "vertex_type", "entity_id"),
    )


class GraphEdge(Base):
    """
    Directed graph edge. edge_type: REQUIRES | APPLIES_TO | SATISFIES | ISSUED_BY | CROSS_REFERENCES
    from_vertex_id → to_vertex_id
    """
    __tablename__ = "graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_vertex_id = Column(UUID(as_uuid=True), ForeignKey("graph_vertices.id"), nullable=False)
    to_vertex_id = Column(UUID(as_uuid=True), ForeignKey("graph_vertices.id"), nullable=False)
    edge_type = Column(String(64), nullable=False, index=True)
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    from_vertex = relationship("GraphVertex", foreign_keys=[from_vertex_id])
    to_vertex = relationship("GraphVertex", foreign_keys=[to_vertex_id])

    __table_args__ = (
        Index("ix_edge_from", "from_vertex_id"),
        Index("ix_edge_to", "to_vertex_id"),
        Index("ix_edge_type_from", "edge_type", "from_vertex_id"),
    )


# ═══════════════════════════════════════════════════════════════════
# AUTH — USERS
# ═══════════════════════════════════════════════════════════════════

class UserRole(str, enum.Enum):
    ADMIN   = "admin"
    ANALYST = "analyst"
    VIEWER  = "viewer"


class User(Base):
    """Application user. JWT claims carry tenant_id + role at login."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)  # tenant slug
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.ANALYST, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
