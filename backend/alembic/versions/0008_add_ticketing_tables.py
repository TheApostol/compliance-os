"""Add M9 ticketing compliance tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-22

Idempotent: uses inspector to check existing tables before creating.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "ticketing_countries" not in existing:
        op.create_table(
            "ticketing_countries",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("country_code", sa.String(2), nullable=False),
            sa.Column("country_name", sa.String(128), nullable=False),
            sa.Column("risk_level", sa.String(16), nullable=False, server_default="MEDIUM"),
            sa.Column("risk_score", sa.Integer, default=50),
            sa.Column("requires_boton_arrepentimiento", sa.Boolean, default=False),
            sa.Column("requires_aaip_registration", sa.Boolean, default=False),
            sa.Column("requires_electronic_invoice", sa.Boolean, default=False),
            sa.Column("requires_anti_resale_controls", sa.Boolean, default=False),
            sa.Column("requires_promoter_permit", sa.Boolean, default=False),
            sa.Column("withdrawal_period_days", sa.Integer, default=10),
            sa.Column("currency", sa.String(8), default="USD"),
            sa.Column("regulator_consumer", sa.String(128)),
            sa.Column("regulator_data_privacy", sa.String(128)),
            sa.Column("regulator_payments", sa.String(128)),
            sa.Column("regulator_tax", sa.String(128)),
            sa.Column("notes", sa.Text),
            sa.Column("regulatory_summary", JSONB, default=dict),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("tenant_id", "country_code", name="uq_ticketing_country_tenant"),
        )
        op.create_index("ix_ticketing_countries_tenant", "ticketing_countries", ["tenant_id"])

    if "ticketing_obligations" not in existing:
        op.create_table(
            "ticketing_obligations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=True),
            sa.Column("country_code", sa.String(2), nullable=False),
            sa.Column("legal_area", sa.String(64), nullable=False),
            sa.Column("title", sa.String(512), nullable=False),
            sa.Column("description", sa.Text, nullable=False),
            sa.Column("legal_basis", sa.String(512)),
            sa.Column("owner_role", sa.String(128)),
            sa.Column("risk_level", sa.String(16), nullable=False),
            sa.Column("implementation_status", sa.String(32), default="not_started"),
            sa.Column("required_evidence", JSONB, default=list),
            sa.Column("controls", JSONB, default=list),
            sa.Column("deadline_frequency", sa.String(128)),
            sa.Column("penalties_summary", sa.Text),
            sa.Column("ai_explanation", sa.Text),
            sa.Column("recommended_action", sa.Text),
            sa.Column("is_blocker", sa.Boolean, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_obligations_country", "ticketing_obligations", ["country_code"])
        op.create_index("ix_ticketing_obligations_category", "ticketing_obligations", ["legal_area"])

    if "ticketing_controls" not in existing:
        op.create_table(
            "ticketing_controls",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=True),
            sa.Column("control_code", sa.String(64), nullable=False),
            sa.Column("name", sa.String(512), nullable=False),
            sa.Column("description", sa.Text),
            sa.Column("category", sa.String(64)),
            sa.Column("risk_dimensions", JSONB, default=list),
            sa.Column("applies_to_countries", JSONB, default=list),
            sa.Column("implementation_guide", sa.Text),
            sa.Column("evidence_required", JSONB, default=list),
            sa.Column("is_mandatory", sa.Boolean, default=False),
            sa.Column("is_implemented", sa.Boolean, default=False),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("control_code", name="uq_ticketing_control_code"),
        )
        op.create_index("ix_ticketing_controls_tenant", "ticketing_controls", ["tenant_id"])

    if "ticketing_promoters" not in existing:
        op.create_table(
            "ticketing_promoters",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(512), nullable=False),
            sa.Column("legal_entity", sa.String(512)),
            sa.Column("tax_id", sa.String(128)),
            sa.Column("country_code", sa.String(2)),
            sa.Column("contact_email", sa.String(255)),
            sa.Column("contact_phone", sa.String(64)),
            sa.Column("agreement_signed", sa.Boolean, default=False),
            sa.Column("agreement_date", sa.DateTime(timezone=True)),
            sa.Column("kyc_verified", sa.Boolean, default=False),
            sa.Column("risk_level", sa.String(16), default="MEDIUM"),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_promoters_tenant", "ticketing_promoters", ["tenant_id"])

    if "ticketing_venues" not in existing:
        op.create_table(
            "ticketing_venues",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(512), nullable=False),
            sa.Column("address", sa.Text),
            sa.Column("city", sa.String(128)),
            sa.Column("country_code", sa.String(2)),
            sa.Column("capacity", sa.Integer),
            sa.Column("venue_type", sa.String(128)),
            sa.Column("authorization_obtained", sa.Boolean, default=False),
            sa.Column("authorization_date", sa.DateTime(timezone=True)),
            sa.Column("authorization_document_url", sa.String(1024)),
            sa.Column("safety_permit_obtained", sa.Boolean, default=False),
            sa.Column("safety_permit_number", sa.String(128)),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_venues_tenant", "ticketing_venues", ["tenant_id"])

    if "ticketing_events" not in existing:
        op.create_table(
            "ticketing_events",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("name", sa.String(512), nullable=False),
            sa.Column("description", sa.Text),
            sa.Column("country_code", sa.String(2), nullable=False),
            sa.Column("city", sa.String(128)),
            sa.Column("venue_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_venues.id")),
            sa.Column("promoter_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_promoters.id")),
            sa.Column("event_date", sa.DateTime(timezone=True)),
            sa.Column("end_date", sa.DateTime(timezone=True)),
            sa.Column("expected_attendance", sa.Integer),
            sa.Column("status", sa.String(32), default="draft"),
            sa.Column("launch_decision", sa.String(32)),
            sa.Column("ticket_categories", JSONB, default=list),
            sa.Column("max_tickets_per_buyer", sa.Integer),
            sa.Column("service_fee_pct", sa.Float, default=0.0),
            sa.Column("service_fee_fixed", sa.Float, default=0.0),
            sa.Column("taxes_included", sa.Boolean, default=True),
            sa.Column("has_promoter_agreement", sa.Boolean, default=False),
            sa.Column("has_refund_policy", sa.Boolean, default=False),
            sa.Column("has_consumer_terms", sa.Boolean, default=False),
            sa.Column("has_payment_processor", sa.Boolean, default=False),
            sa.Column("has_privacy_policy", sa.Boolean, default=False),
            sa.Column("has_withdrawal_button", sa.Boolean, default=False),
            sa.Column("has_cancellation_clause", sa.Boolean, default=False),
            sa.Column("has_postponement_clause", sa.Boolean, default=False),
            sa.Column("has_marketing_consent", sa.Boolean, default=False),
            sa.Column("has_anti_bot_protection", sa.Boolean, default=False),
            sa.Column("has_electronic_invoice", sa.Boolean, default=False),
            sa.Column("has_aaip_registration", sa.Boolean, default=False),
            sa.Column("has_venue_authorization", sa.Boolean, default=False),
            sa.Column("has_event_permit", sa.Boolean, default=False),
            sa.Column("has_chargeback_evidence", sa.Boolean, default=False),
            sa.Column("resale_enabled", sa.Boolean, default=False),
            sa.Column("resale_type", sa.String(64)),
            sa.Column("has_resale_policy", sa.Boolean, default=False),
            sa.Column("crypto_payments_enabled", sa.Boolean, default=False),
            sa.Column("has_aml_kyc_controls", sa.Boolean, default=False),
            sa.Column("wallet_balance_enabled", sa.Boolean, default=False),
            sa.Column("refund_sla_days", sa.Integer, default=10),
            sa.Column("complaint_sla_days", sa.Integer, default=15),
            sa.Column("risk_score_overall", sa.Integer, default=0),
            sa.Column("risk_breakdown", JSONB, default=dict),
            sa.Column("blocking_reasons", JSONB, default=list),
            sa.Column("compliance_gaps", JSONB, default=list),
            sa.Column("additional_countries", JSONB, default=list),
            sa.Column("metadata", JSONB, default=dict),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_events_tenant",  "ticketing_events", ["tenant_id"])
        op.create_index("ix_ticketing_events_country", "ticketing_events", ["country_code"])
        op.create_index("ix_ticketing_events_status",  "ticketing_events", ["status"])

    if "ticketing_event_checklists" not in existing:
        op.create_table(
            "ticketing_event_checklists",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id"), nullable=False),
            sa.Column("control_code", sa.String(64), nullable=False),
            sa.Column("category", sa.String(64)),
            sa.Column("title", sa.String(512), nullable=False),
            sa.Column("description", sa.Text),
            sa.Column("is_required", sa.Boolean, default=True),
            sa.Column("is_completed", sa.Boolean, default=False),
            sa.Column("completed_by", sa.String(128)),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("evidence_url", sa.String(1024)),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_checklist_event", "ticketing_event_checklists", ["event_id"])

    if "ticketing_documents" not in existing:
        op.create_table(
            "ticketing_documents",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("document_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(512), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("country_code", sa.String(2)),
            sa.Column("language", sa.String(8), default="es"),
            sa.Column("version", sa.Integer, default=1),
            sa.Column("generated_by_model", sa.String(128)),
            sa.Column("is_approved", sa.Boolean, default=False),
            sa.Column("approved_by", sa.String(128)),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_docs_tenant", "ticketing_documents", ["tenant_id"])
        op.create_index("ix_ticketing_docs_event",  "ticketing_documents", ["event_id"])

    if "ticketing_risk_scores" not in existing:
        op.create_table(
            "ticketing_risk_scores",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id"), nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("overall_score", sa.Integer, nullable=False),
            sa.Column("launch_decision", sa.String(32), nullable=False),
            sa.Column("consumer_risk", sa.Integer, default=0),
            sa.Column("refund_risk", sa.Integer, default=0),
            sa.Column("resale_risk", sa.Integer, default=0),
            sa.Column("payment_risk", sa.Integer, default=0),
            sa.Column("data_privacy_risk", sa.Integer, default=0),
            sa.Column("tax_risk", sa.Integer, default=0),
            sa.Column("contractual_risk", sa.Integer, default=0),
            sa.Column("fraud_aml_risk", sa.Integer, default=0),
            sa.Column("operational_risk", sa.Integer, default=0),
            sa.Column("country_enforcement_risk", sa.Integer, default=0),
            sa.Column("blocking_reasons", JSONB, default=list),
            sa.Column("high_risk_triggers", JSONB, default=list),
            sa.Column("missing_controls", JSONB, default=list),
            sa.Column("recommendations", JSONB, default=list),
            sa.Column("assessed_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_risk_event", "ticketing_risk_scores", ["event_id"])

    if "ticketing_claims" not in existing:
        op.create_table(
            "ticketing_claims",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("claim_type", sa.String(64)),
            sa.Column("consumer_name", sa.String(255)),
            sa.Column("consumer_email", sa.String(255)),
            sa.Column("description", sa.Text),
            sa.Column("status", sa.String(32), default="open"),
            sa.Column("priority", sa.String(16), default="MEDIUM"),
            sa.Column("sla_deadline", sa.DateTime(timezone=True)),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
            sa.Column("resolution_notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_claims_tenant", "ticketing_claims", ["tenant_id"])
        op.create_index("ix_ticketing_claims_event",  "ticketing_claims", ["event_id"])

    if "ticketing_refund_cases" not in existing:
        op.create_table(
            "ticketing_refund_cases",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_claims.id")),
            sa.Column("consumer_name", sa.String(255)),
            sa.Column("ticket_reference", sa.String(128)),
            sa.Column("amount_usd", sa.Float),
            sa.Column("refund_type", sa.String(64)),
            sa.Column("status", sa.String(32), default="pending"),
            sa.Column("sla_deadline", sa.DateTime(timezone=True)),
            sa.Column("processed_at", sa.DateTime(timezone=True)),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_refunds_tenant", "ticketing_refund_cases", ["tenant_id"])

    if "ticketing_chargebacks" not in existing:
        op.create_table(
            "ticketing_chargebacks",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("transaction_id", sa.String(128)),
            sa.Column("consumer_name", sa.String(255)),
            sa.Column("amount_usd", sa.Float),
            sa.Column("reason_code", sa.String(64)),
            sa.Column("status", sa.String(32), default="received"),
            sa.Column("evidence_submitted", sa.Boolean, default=False),
            sa.Column("evidence_deadline", sa.DateTime(timezone=True)),
            sa.Column("outcome", sa.String(32)),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_chargebacks_tenant", "ticketing_chargebacks", ["tenant_id"])

    if "ticketing_evidence" not in existing:
        op.create_table(
            "ticketing_evidence",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("evidence_type", sa.String(128)),
            sa.Column("filename", sa.String(512)),
            sa.Column("file_url", sa.String(1024)),
            sa.Column("source_hash", sa.String(64)),
            sa.Column("custody_hash", sa.String(64)),
            sa.Column("uploaded_by", sa.String(128)),
            sa.Column("notes", sa.Text),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_evidence_tenant", "ticketing_evidence", ["tenant_id"])
        op.create_index("ix_ticketing_evidence_event",  "ticketing_evidence", ["event_id"])

    if "ticketing_ai_assessments" not in existing:
        op.create_table(
            "ticketing_ai_assessments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("ticketing_events.id")),
            sa.Column("question", sa.Text, nullable=False),
            sa.Column("context", JSONB, default=dict),
            sa.Column("response", JSONB, nullable=False),
            sa.Column("model_used", sa.String(128)),
            sa.Column("latency_ms", sa.Integer),
            sa.Column("created_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_ticketing_ai_tenant", "ticketing_ai_assessments", ["tenant_id"])


def downgrade() -> None:
    tables = [
        "ticketing_ai_assessments",
        "ticketing_evidence",
        "ticketing_chargebacks",
        "ticketing_refund_cases",
        "ticketing_claims",
        "ticketing_risk_scores",
        "ticketing_documents",
        "ticketing_event_checklists",
        "ticketing_events",
        "ticketing_venues",
        "ticketing_promoters",
        "ticketing_controls",
        "ticketing_obligations",
        "ticketing_countries",
    ]
    existing = _existing_tables()
    for t in tables:
        if t in existing:
            op.drop_table(t)
