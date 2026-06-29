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
    Column, String, Text, DateTime, Integer, Boolean, Numeric,
    ForeignKey, Enum as SAEnum, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE ENTITIES (graph entity registry)
# ═══════════════════════════════════════════════════════════════════

class EntityType(str, enum.Enum):
    COMPANY    = "company"
    INDIVIDUAL = "individual"
    SECTOR     = "sector"   # virtual entity representing a regulated sector


class ComplianceEntity(Base):
    """
    Companies, individuals, or virtual sector nodes that are subject to
    regulatory obligations.  APPLIES_TO edges in the compliance graph link
    obligation vertices to entity vertices.
    """
    __tablename__ = "compliance_entities"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(String(64), nullable=False, index=True)
    name        = Column(String(255), nullable=False)
    entity_type = Column(SAEnum(EntityType), nullable=False)
    sectors     = Column(JSONB, default=list)   # ["PSP", "bank", "crypto"]
    properties  = Column(JSONB, default=dict)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_entity_tenant_type", "tenant_id", "entity_type"),
    )


# ═══════════════════════════════════════════════════════════════════
# TENANT
# ═══════════════════════════════════════════════════════════════════

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)  # used as tenant_id in JWT
    data_residency_policy = Column(String, default="global")  # global | latam | ar | br
    timezone_iana = Column(String, default="UTC")  # IANA timezone (e.g. America/Argentina/Buenos_Aires)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settings = Column(JSONB, default=dict)


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
    tenant_id = Column(String(64), nullable=True, index=True)  # None = shared/global regulation
    country = Column(String(2), nullable=False, index=True)
    regulator = Column(String(64), nullable=False, index=True)
    code = Column(String(128), nullable=False)
    title = Column(String(512), nullable=False)
    sector = Column(String(64))
    published_at = Column(DateTime(timezone=True))
    effective_from = Column(DateTime(timezone=True))
    source_url = Column(String(1024))
    source_hash = Column(String(64))
    full_text = Column(Text, nullable=True)
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
    tenant_id = Column(String(64), nullable=False, index=True, server_default="system")
    label = Column(String(255), nullable=False)
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_vertex_type_entity", "vertex_type", "entity_id"),
        Index("ix_graph_vertex_tenant", "tenant_id"),
        Index("ix_graph_vertex_tenant_type_entity", "tenant_id", "vertex_type", "entity_id"),
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
    tenant_id = Column(String(64), nullable=False, index=True, server_default="system")
    edge_type = Column(String(64), nullable=False, index=True)
    properties = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    from_vertex = relationship("GraphVertex", foreign_keys=[from_vertex_id])
    to_vertex = relationship("GraphVertex", foreign_keys=[to_vertex_id])

    __table_args__ = (
        Index("ix_edge_from", "from_vertex_id"),
        Index("ix_edge_to", "to_vertex_id"),
        Index("ix_edge_type_from", "edge_type", "from_vertex_id"),
        Index("ix_graph_edge_tenant", "tenant_id"),
        Index("ix_graph_edge_tenant_type", "tenant_id", "edge_type"),
    )


# ═══════════════════════════════════════════════════════════════════
# WEBHOOKS
# ═══════════════════════════════════════════════════════════════════

class WebhookEvent(str, enum.Enum):
    CRAWL_COMPLETE     = "crawl.complete"
    DEADLINE_ALERT     = "deadline.alert"
    REGULATION_PARSED  = "regulation.parsed"


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id                = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id         = Column(String, nullable=False, index=True)
    name              = Column(String, nullable=False)
    url               = Column(String, nullable=False)
    secret            = Column(String, nullable=True)   # HMAC-SHA256 signing secret
    events            = Column(JSONB, default=list)     # list of WebhookEvent values to subscribe to
    is_active         = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_status_code  = Column(Integer, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_webhooks_tenant", "tenant_id"),
    )


# ═══════════════════════════════════════════════════════════════════
# API KEYS
# ═══════════════════════════════════════════════════════════════════

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)              # human label e.g. "CI pipeline"
    key_prefix = Column(String(8), nullable=False)     # first 8 chars, shown in list
    hashed_key = Column(String, nullable=False, unique=True)  # SHA-256 hex of full key
    scopes = Column(JSONB, default=list)               # e.g. ["read", "write", "crawl"]
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_api_keys_tenant", "tenant_id"),
        Index("ix_api_keys_prefix", "key_prefix"),
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


# ═══════════════════════════════════════════════════════════════════
# DEADLINE ALERTS
# ═══════════════════════════════════════════════════════════════════

class AlertSeverity(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class DeadlineAlert(Base):
    """
    Tracks approaching obligation deadlines.
    Created/updated daily by the deadline checker background job.
    """
    __tablename__ = "deadline_alerts"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String, nullable=False, index=True)
    obligation_id   = Column(String, nullable=False)   # FK-style ref, no hard FK for simplicity
    regulation_code = Column(String, nullable=False)
    regulator       = Column(String, nullable=False)
    country         = Column(String, nullable=False)
    title           = Column(String, nullable=False)
    deadline        = Column(DateTime(timezone=True), nullable=False)
    days_remaining  = Column(Integer, nullable=False)
    severity        = Column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_alerts_tenant_ack", "tenant_id", "is_acknowledged"),
        UniqueConstraint("tenant_id", "obligation_id", name="uq_alert_tenant_obligation"),
    )


# ═══════════════════════════════════════════════════════════════════
# M9 — TICKETING
# ═══════════════════════════════════════════════════════════════════

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(SAEnum(TicketPriority), default=TicketPriority.MEDIUM)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_tickets_tenant_status", "tenant_id", "status"),
    )


# ═══════════════════════════════════════════════════════════════════
# M10 — TRANSACTION MONITORING (AML)
# ═══════════════════════════════════════════════════════════════════

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    REPORTED = "reported"


class Transaction(Base):
    """An inbound/outbound financial transaction screened for AML risk.

    Persisted PENDING first, then scored synchronously by
    TransactionMonitoringEngine.score_transaction so a record always exists
    even if AI scoring fails (audit trail requirement, premortem F3/F5).
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)

    external_ref = Column(String(255), nullable=True)  # source system transaction id
    subject_identifier = Column(String(255), nullable=False)  # customer/account id
    counterparty_identifier = Column(String(255), nullable=True)
    counterparty_country = Column(String(2), nullable=True)

    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(8), nullable=False)
    channel = Column(String(32), nullable=False)  # wire | card | crypto | cash | ach
    country = Column(String(2), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)

    status = Column(SAEnum(TransactionStatus), default=TransactionStatus.PENDING, index=True)
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(SAEnum(RiskLevel), nullable=True, index=True)
    rule_flags = Column(JSONB, default=list)      # deterministic rules triggered, e.g. ["velocity_24h", "high_risk_geo"]
    ai_analysis = Column(JSONB, default=dict)     # raw AI typology/rationale output
    case_id = Column(String(64), nullable=True)   # FK-style ref to compliance_cases.id, no hard FK (tenant_id type mismatch on that table)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    scored_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_txn_tenant_subject", "tenant_id", "subject_identifier"),
        Index("ix_txn_tenant_status", "tenant_id", "status"),
        Index("ix_txn_tenant_occurred", "tenant_id", "occurred_at"),
    )


class TransactionRule(Base):
    """Tenant-configurable deterministic AML rule (threshold/velocity/geography/structuring)."""
    __tablename__ = "transaction_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    rule_code = Column(String(64), nullable=False)
    rule_type = Column(String(32), nullable=False)  # amount_threshold | velocity | geography | structuring
    description = Column(String(500), nullable=False)
    config = Column(JSONB, default=dict)  # e.g. {"max_amount": 10000, "currency": "USD"}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tenant_id", "rule_code", name="uq_rule_tenant_code"),
    )


# ═══════════════════════════════════════════════════════════════════
# PREMORTEM — FAILURE MODE & RISK ANALYSIS
# ═══════════════════════════════════════════════════════════════════

class FailureModeSeverity(str, enum.Enum):
    CRITICAL = "critical"    # System down, data loss
    HIGH = "high"            # Major functional loss
    MEDIUM = "medium"        # Degradation, latency
    LOW = "low"              # Minor impact


class FailureModeStatus(str, enum.Enum):
    IDENTIFIED = "identified"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    MONITORING = "monitoring"


class PremortermFailureMode(Base):
    __tablename__ = "premortem_failure_modes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    scenario = Column(String(500), nullable=False)  # e.g., "AI model fails to parse regulation PDFs"
    description = Column(Text, nullable=False)      # Detailed failure description
    impact = Column(Text, nullable=False)           # What breaks, who's affected
    likelihood = Column(String(50), nullable=False) # high/medium/low
    severity = Column(SAEnum(FailureModeSeverity), default=FailureModeSeverity.HIGH)
    category = Column(String(100), nullable=False)  # e.g., "ai_reliability", "data_isolation", "crawler", "audit"
    affected_modules = Column(JSONB, default=list)  # ["M1", "M4"]
    status = Column(SAEnum(FailureModeStatus), default=FailureModeStatus.IDENTIFIED)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_premortem_tenant_category", "tenant_id", "category"),
        Index("ix_premortem_severity", "severity"),
    )


class PremortermMitigation(Base):
    __tablename__ = "premortem_mitigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    failure_mode_id = Column(UUID(as_uuid=True), ForeignKey("premortem_failure_modes.id"), nullable=False)
    mitigation = Column(Text, nullable=False)       # Specific action to prevent failure
    owner = Column(String(255), nullable=True)      # Who's responsible
    effort_estimate = Column(String(50), nullable=True)  # "1d", "1w", "2w"
    priority = Column(Integer, default=0)           # Sort order
    status = Column(String(50), default="pending")  # pending/in_progress/completed
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_premortem_mit_failure", "failure_mode_id"),
    )


class PremortermFinding(Base):
    __tablename__ = "premortem_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    finding_type = Column(String(100), nullable=False)  # "observation", "risk", "recommendation"
    priority = Column(String(50), default="medium")     # critical/high/medium/low
    related_failure_modes = Column(JSONB, default=list)  # [failure_mode_id, ...]
    status = Column(String(50), default="open")         # open/acknowledged/addressed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_premortem_finding_type", "finding_type"),
    )
