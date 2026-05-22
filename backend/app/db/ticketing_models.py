"""
ComplianceOS — Ticketing Industry Compliance Models (M9)

Machine-readable tables for the Ticketing Event Compliance Module.
All tables are tenant-scoped and multi-country aware.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Boolean, Float,
    ForeignKey, Enum as SAEnum, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


# ═══════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════

class TicketingCountryRisk(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class TicketingObligationCategory(str, enum.Enum):
    CONSUMER_PROTECTION   = "consumer_protection"
    ECOMMERCE             = "ecommerce"
    REFUNDS_CANCELLATIONS = "refunds_cancellations"
    TICKET_RESALE         = "ticket_resale"
    DATA_PRIVACY          = "data_privacy"
    PAYMENTS_PSP          = "payments_psp"
    TAX_INVOICING         = "tax_invoicing"
    MARKETING_COMMS       = "marketing_comms"
    PUBLIC_EVENTS_PERMITS = "public_events_permits"
    TERMS_CONDITIONS      = "terms_conditions"
    COMPLAINT_HANDLING    = "complaint_handling"
    EVIDENCE_RETENTION    = "evidence_retention"


class TicketingRiskLevel(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class TicketingImplementationStatus(str, enum.Enum):
    NOT_STARTED     = "not_started"
    IN_PROGRESS     = "in_progress"
    IMPLEMENTED     = "implemented"
    VERIFIED        = "verified"
    NOT_APPLICABLE  = "not_applicable"


class TicketingEventStatus(str, enum.Enum):
    DRAFT                   = "draft"
    UNDER_REVIEW            = "under_review"
    APPROVED                = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    BLOCKED                 = "blocked"
    LIVE                    = "live"
    COMPLETED               = "completed"
    CANCELLED               = "cancelled"


class TicketingLaunchDecision(str, enum.Enum):
    APPROVED                 = "APPROVED"
    APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"
    BLOCKED                  = "BLOCKED"


class TicketingDocumentType(str, enum.Enum):
    TERMS_AND_CONDITIONS      = "terms_and_conditions"
    REFUND_POLICY             = "refund_policy"
    PRIVACY_POLICY            = "privacy_policy"
    PROMOTER_AGREEMENT        = "promoter_agreement"
    VENUE_AUTHORIZATION       = "venue_authorization"
    CHARGEBACK_EVIDENCE       = "chargeback_evidence"
    COMPLAINT_RESPONSE        = "complaint_response"
    CANCELLATION_NOTICE       = "cancellation_notice"
    POSTPONEMENT_NOTICE       = "postponement_notice"
    RESALE_POLICY             = "resale_policy"
    DATA_PROCESSING_AGREEMENT = "data_processing_agreement"


class TicketingClaimStatus(str, enum.Enum):
    OPEN         = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED     = "resolved"
    ESCALATED    = "escalated"
    CLOSED       = "closed"


class TicketingRefundStatus(str, enum.Enum):
    PENDING   = "pending"
    APPROVED  = "approved"
    PROCESSED = "processed"
    DENIED    = "denied"
    DISPUTED  = "disputed"


class TicketingChargebackStatus(str, enum.Enum):
    RECEIVED         = "received"
    UNDER_REVIEW     = "under_review"
    EVIDENCE_SUBMITTED = "evidence_submitted"
    WON              = "won"
    LOST             = "lost"


# ═══════════════════════════════════════════════════════════════════
# COUNTRY RISK PROFILES
# ═══════════════════════════════════════════════════════════════════

class TicketingCountry(Base):
    """Country-level risk profiles and regulatory requirements for ticketing platforms."""
    __tablename__ = "ticketing_countries"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(String(64), nullable=False, index=True)
    country_code = Column(String(2), nullable=False)
    country_name = Column(String(128), nullable=False)
    risk_level   = Column(SAEnum(TicketingCountryRisk), nullable=False, default=TicketingCountryRisk.MEDIUM)
    risk_score   = Column(Integer, default=50)  # 0-100

    # Regulatory flags
    requires_boton_arrepentimiento = Column(Boolean, default=False)
    requires_aaip_registration     = Column(Boolean, default=False)
    requires_electronic_invoice    = Column(Boolean, default=False)
    requires_anti_resale_controls  = Column(Boolean, default=False)
    requires_promoter_permit       = Column(Boolean, default=False)
    withdrawal_period_days         = Column(Integer, default=10)

    # Regulators
    currency            = Column(String(8), default="USD")
    regulator_consumer  = Column(String(128))
    regulator_data_privacy = Column(String(128))
    regulator_payments  = Column(String(128))
    regulator_tax       = Column(String(128))

    notes              = Column(Text)
    regulatory_summary = Column(JSONB, default=dict)
    created_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tenant_id", "country_code", name="uq_ticketing_country_tenant"),
        Index("ix_ticketing_countries_tenant", "tenant_id"),
    )


# ═══════════════════════════════════════════════════════════════════
# REGULATORY OBLIGATIONS
# ═══════════════════════════════════════════════════════════════════

class TicketingObligation(Base):
    """Regulatory obligation for ticketing platforms, by country and category."""
    __tablename__ = "ticketing_obligations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(String(64), nullable=True, index=True)  # None = global/shared
    country_code = Column(String(2), nullable=False, index=True)
    legal_area   = Column(SAEnum(TicketingObligationCategory), nullable=False)
    title        = Column(String(512), nullable=False)
    description  = Column(Text, nullable=False)
    legal_basis  = Column(String(512))
    owner_role   = Column(String(128))
    risk_level   = Column(SAEnum(TicketingRiskLevel), nullable=False)
    implementation_status = Column(SAEnum(TicketingImplementationStatus), default=TicketingImplementationStatus.NOT_STARTED)
    required_evidence  = Column(JSONB, default=list)
    controls           = Column(JSONB, default=list)
    deadline_frequency = Column(String(128))
    penalties_summary  = Column(Text)
    ai_explanation     = Column(Text)
    recommended_action = Column(Text)
    is_blocker         = Column(Boolean, default=False)
    created_at         = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ticketing_obligations_country", "country_code"),
        Index("ix_ticketing_obligations_category", "legal_area"),
    )


# ═══════════════════════════════════════════════════════════════════
# CONTROLS LIBRARY
# ═══════════════════════════════════════════════════════════════════

class TicketingControl(Base):
    """Ticketing-specific compliance controls library."""
    __tablename__ = "ticketing_controls"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(String(64), nullable=True, index=True)
    control_code = Column(String(64), nullable=False)
    name         = Column(String(512), nullable=False)
    description  = Column(Text)
    category     = Column(SAEnum(TicketingObligationCategory))
    risk_dimensions       = Column(JSONB, default=list)
    applies_to_countries  = Column(JSONB, default=list)
    implementation_guide  = Column(Text)
    evidence_required     = Column(JSONB, default=list)
    is_mandatory          = Column(Boolean, default=False)
    is_implemented        = Column(Boolean, default=False)
    created_at            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("control_code", name="uq_ticketing_control_code"),
        Index("ix_ticketing_controls_tenant", "tenant_id"),
    )


# ═══════════════════════════════════════════════════════════════════
# PROMOTERS & VENUES
# ═══════════════════════════════════════════════════════════════════

class TicketingPromoter(Base):
    """Event promoter / organizer records."""
    __tablename__ = "ticketing_promoters"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(String(64), nullable=False, index=True)
    name         = Column(String(512), nullable=False)
    legal_entity = Column(String(512))
    tax_id       = Column(String(128))
    country_code = Column(String(2))
    contact_email = Column(String(255))
    contact_phone = Column(String(64))
    agreement_signed = Column(Boolean, default=False)
    agreement_date   = Column(DateTime(timezone=True))
    kyc_verified     = Column(Boolean, default=False)
    risk_level       = Column(SAEnum(TicketingRiskLevel), default=TicketingRiskLevel.MEDIUM)
    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_ticketing_promoters_tenant", "tenant_id"),)


class TicketingVenue(Base):
    """Venue records."""
    __tablename__ = "ticketing_venues"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id    = Column(String(64), nullable=False, index=True)
    name         = Column(String(512), nullable=False)
    address      = Column(Text)
    city         = Column(String(128))
    country_code = Column(String(2))
    capacity     = Column(Integer)
    venue_type   = Column(String(128))
    authorization_obtained      = Column(Boolean, default=False)
    authorization_date          = Column(DateTime(timezone=True))
    authorization_document_url  = Column(String(1024))
    safety_permit_obtained      = Column(Boolean, default=False)
    safety_permit_number        = Column(String(128))
    notes      = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_ticketing_venues_tenant", "tenant_id"),)


# ═══════════════════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════════════════

class TicketingEvent(Base):
    """An event for which compliance must be assessed before launch."""
    __tablename__ = "ticketing_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(String(64), nullable=False, index=True)

    # Basic info
    name        = Column(String(512), nullable=False)
    description = Column(Text)
    country_code = Column(String(2), nullable=False)
    city         = Column(String(128))
    venue_id     = Column(UUID(as_uuid=True), ForeignKey("ticketing_venues.id"), nullable=True)
    promoter_id  = Column(UUID(as_uuid=True), ForeignKey("ticketing_promoters.id"), nullable=True)
    event_date   = Column(DateTime(timezone=True))
    end_date     = Column(DateTime(timezone=True))
    expected_attendance = Column(Integer)

    # Status
    status          = Column(SAEnum(TicketingEventStatus), default=TicketingEventStatus.DRAFT)
    launch_decision = Column(SAEnum(TicketingLaunchDecision), nullable=True)

    # Ticket configuration
    ticket_categories     = Column(JSONB, default=list)
    max_tickets_per_buyer = Column(Integer)
    service_fee_pct       = Column(Float, default=0.0)
    service_fee_fixed     = Column(Float, default=0.0)
    taxes_included        = Column(Boolean, default=True)

    # Compliance flags (BLOCKER checks)
    has_promoter_agreement  = Column(Boolean, default=False)
    has_refund_policy       = Column(Boolean, default=False)
    has_consumer_terms      = Column(Boolean, default=False)
    has_payment_processor   = Column(Boolean, default=False)
    has_privacy_policy      = Column(Boolean, default=False)
    has_withdrawal_button   = Column(Boolean, default=False)   # botón arrepentimiento
    has_cancellation_clause  = Column(Boolean, default=False)
    has_postponement_clause  = Column(Boolean, default=False)
    has_marketing_consent   = Column(Boolean, default=False)
    has_anti_bot_protection = Column(Boolean, default=False)
    has_electronic_invoice  = Column(Boolean, default=False)
    has_aaip_registration   = Column(Boolean, default=False)
    has_venue_authorization = Column(Boolean, default=False)
    has_event_permit        = Column(Boolean, default=False)
    has_chargeback_evidence = Column(Boolean, default=False)

    # High-risk features
    resale_enabled         = Column(Boolean, default=False)
    resale_type            = Column(String(64))   # disabled | controlled | marketplace
    has_resale_policy      = Column(Boolean, default=False)
    crypto_payments_enabled = Column(Boolean, default=False)
    has_aml_kyc_controls   = Column(Boolean, default=False)
    wallet_balance_enabled = Column(Boolean, default=False)

    # SLAs
    refund_sla_days    = Column(Integer, default=10)
    complaint_sla_days = Column(Integer, default=15)

    # Risk outputs
    risk_score_overall = Column(Integer, default=0)
    risk_breakdown     = Column(JSONB, default=dict)
    blocking_reasons   = Column(JSONB, default=list)
    compliance_gaps    = Column(JSONB, default=list)

    additional_countries = Column(JSONB, default=list)
    metadata_json        = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    venue    = relationship("TicketingVenue",    foreign_keys=[venue_id])
    promoter = relationship("TicketingPromoter", foreign_keys=[promoter_id])
    checklists   = relationship("TicketingEventChecklist", back_populates="event", cascade="all, delete-orphan")
    risk_scores  = relationship("TicketingRiskScore",      back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ticketing_events_tenant",  "tenant_id"),
        Index("ix_ticketing_events_country", "country_code"),
        Index("ix_ticketing_events_status",  "status"),
    )


# ═══════════════════════════════════════════════════════════════════
# EVENT CHECKLIST
# ═══════════════════════════════════════════════════════════════════

class TicketingEventChecklist(Base):
    """Per-event compliance checklist items generated from controls library."""
    __tablename__ = "ticketing_event_checklists"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id     = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=False)
    control_code = Column(String(64), nullable=False)
    category     = Column(SAEnum(TicketingObligationCategory))
    title        = Column(String(512), nullable=False)
    description  = Column(Text)
    is_required  = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completed_by = Column(String(128))
    completed_at = Column(DateTime(timezone=True))
    evidence_url = Column(String(1024))
    notes        = Column(Text)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    event = relationship("TicketingEvent", back_populates="checklists")

    __table_args__ = (Index("ix_ticketing_checklist_event", "event_id"),)


# ═══════════════════════════════════════════════════════════════════
# DOCUMENTS
# ═══════════════════════════════════════════════════════════════════

class TicketingDocument(Base):
    """Generated compliance documents (T&C, refund policies, notices, etc.)."""
    __tablename__ = "ticketing_documents"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(String(64), nullable=False, index=True)
    event_id      = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    document_type = Column(SAEnum(TicketingDocumentType), nullable=False)
    title         = Column(String(512), nullable=False)
    content       = Column(Text, nullable=False)
    country_code  = Column(String(2))
    language      = Column(String(8), default="es")
    version       = Column(Integer, default=1)
    generated_by_model = Column(String(128))
    is_approved   = Column(Boolean, default=False)
    approved_by   = Column(String(128))
    approved_at   = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ticketing_docs_tenant", "tenant_id"),
        Index("ix_ticketing_docs_event",  "event_id"),
    )


# ═══════════════════════════════════════════════════════════════════
# RISK SCORES
# ═══════════════════════════════════════════════════════════════════

class TicketingRiskScore(Base):
    """Risk assessment scores across 10 dimensions for a ticketing event."""
    __tablename__ = "ticketing_risk_scores"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id    = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=False)
    tenant_id   = Column(String(64), nullable=False, index=True)

    overall_score   = Column(Integer, nullable=False)
    launch_decision = Column(SAEnum(TicketingLaunchDecision), nullable=False)

    # Dimension scores 0-100
    consumer_risk           = Column(Integer, default=0)
    refund_risk             = Column(Integer, default=0)
    resale_risk             = Column(Integer, default=0)
    payment_risk            = Column(Integer, default=0)
    data_privacy_risk       = Column(Integer, default=0)
    tax_risk                = Column(Integer, default=0)
    contractual_risk        = Column(Integer, default=0)
    fraud_aml_risk          = Column(Integer, default=0)
    operational_risk        = Column(Integer, default=0)
    country_enforcement_risk = Column(Integer, default=0)

    blocking_reasons  = Column(JSONB, default=list)
    high_risk_triggers = Column(JSONB, default=list)
    missing_controls  = Column(JSONB, default=list)
    recommendations   = Column(JSONB, default=list)

    assessed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    event = relationship("TicketingEvent", back_populates="risk_scores")

    __table_args__ = (Index("ix_ticketing_risk_event", "event_id"),)


# ═══════════════════════════════════════════════════════════════════
# CLAIMS, REFUNDS, CHARGEBACKS
# ═══════════════════════════════════════════════════════════════════

class TicketingClaim(Base):
    """Consumer complaints and claims."""
    __tablename__ = "ticketing_claims"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id      = Column(String(64), nullable=False, index=True)
    event_id       = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    claim_type     = Column(String(64))   # refund | cancellation | fraud | other
    consumer_name  = Column(String(255))
    consumer_email = Column(String(255))
    description    = Column(Text)
    status         = Column(SAEnum(TicketingClaimStatus), default=TicketingClaimStatus.OPEN)
    priority       = Column(SAEnum(TicketingRiskLevel), default=TicketingRiskLevel.MEDIUM)
    sla_deadline   = Column(DateTime(timezone=True))
    resolved_at    = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ticketing_claims_tenant", "tenant_id"),
        Index("ix_ticketing_claims_event",  "event_id"),
    )


class TicketingRefundCase(Base):
    """Refund workflow tracking."""
    __tablename__ = "ticketing_refund_cases"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(String(64), nullable=False, index=True)
    event_id         = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    claim_id         = Column(UUID(as_uuid=True), ForeignKey("ticketing_claims.id"), nullable=True)
    consumer_name    = Column(String(255))
    ticket_reference = Column(String(128))
    amount_usd       = Column(Float)
    refund_type      = Column(String(64))   # withdrawal | cancellation | postponement | fraud
    status           = Column(SAEnum(TicketingRefundStatus), default=TicketingRefundStatus.PENDING)
    sla_deadline     = Column(DateTime(timezone=True))
    processed_at     = Column(DateTime(timezone=True))
    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_ticketing_refunds_tenant", "tenant_id"),)


class TicketingChargeback(Base):
    """Chargeback tracking."""
    __tablename__ = "ticketing_chargebacks"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id        = Column(String(64), nullable=False, index=True)
    event_id         = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    transaction_id   = Column(String(128))
    consumer_name    = Column(String(255))
    amount_usd       = Column(Float)
    reason_code      = Column(String(64))
    status           = Column(SAEnum(TicketingChargebackStatus), default=TicketingChargebackStatus.RECEIVED)
    evidence_submitted = Column(Boolean, default=False)
    evidence_deadline  = Column(DateTime(timezone=True))
    outcome          = Column(String(32))
    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_ticketing_chargebacks_tenant", "tenant_id"),)


# ═══════════════════════════════════════════════════════════════════
# EVIDENCE & AI ASSESSMENTS
# ═══════════════════════════════════════════════════════════════════

class TicketingEvidence(Base):
    """Evidence files for ticketing compliance (permits, agreements, policies)."""
    __tablename__ = "ticketing_evidence"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id     = Column(String(64), nullable=False, index=True)
    event_id      = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    evidence_type = Column(String(128))
    filename      = Column(String(512))
    file_url      = Column(String(1024))
    source_hash   = Column(String(64))
    custody_hash  = Column(String(64))
    uploaded_by   = Column(String(128))
    notes         = Column(Text)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ticketing_evidence_tenant", "tenant_id"),
        Index("ix_ticketing_evidence_event",  "event_id"),
    )


class TicketingAIAssessment(Base):
    """AI copilot assessments and structured responses for ticketing compliance."""
    __tablename__ = "ticketing_ai_assessments"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id   = Column(String(64), nullable=False, index=True)
    event_id    = Column(UUID(as_uuid=True), ForeignKey("ticketing_events.id"), nullable=True)
    question    = Column(Text, nullable=False)
    context     = Column(JSONB, default=dict)
    response    = Column(JSONB, nullable=False)
    model_used  = Column(String(128))
    latency_ms  = Column(Integer)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (Index("ix_ticketing_ai_tenant", "tenant_id"),)
