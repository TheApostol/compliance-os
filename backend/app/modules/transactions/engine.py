"""
M10 — Transaction Monitoring (AML)
====================================
Real-time AML transaction scoring: deterministic rule engine (threshold,
velocity/structuring, geography) combined with AI typology analysis via
the orchestrator. Every screening decision is audit-logged (hash chain).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func

from app.core.audit import append_audit
from app.db.base import AsyncSessionLocal
from app.db.models import RiskLevel, Transaction, TransactionRule, TransactionStatus
from app.services.ai_orchestrator import (
    AIOrchestrator, InferenceRequest, TaskType, get_orchestrator
)

VELOCITY_WINDOW_HOURS = 24
VELOCITY_MAX_COUNT = 5
VELOCITY_MAX_SUM = Decimal("15000")
CTR_THRESHOLD = Decimal("10000")
STRUCTURING_BAND = Decimal("2000")  # flags amounts just under the CTR threshold
DEFAULT_HIGH_RISK_COUNTRIES = {"IR", "KP", "SY", "MM", "AF"}

ANOMALY_SYSTEM = """You are an AML transaction monitoring analyst for ComplianceOS, expert in LATAM and
global AML typologies (smurfing, layering, structuring, trade-based ML, mule accounts). You will be
given a transaction, the deterministic rules it already triggered, and recent transaction history for
the same subject. Use these as evidence, don't invent figures. Output ONLY valid JSON."""

ANOMALY_SCHEMA = """{
  "risk_score": 1-100,
  "typologies_detected": ["specific AML typology names, [] if none"],
  "rof_sar_required": bool,
  "recommended_action": "ACCEPT|FLAG|BLOCK|ESCALATE",
  "rationale": "1-3 sentences citing the rules/history that drove the score"
}"""


def _risk_level_for_score(score: int) -> RiskLevel:
    if score >= 80:
        return RiskLevel.CRITICAL
    if score >= 60:
        return RiskLevel.HIGH
    if score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class TransactionMonitoringEngine:
    def __init__(self, orchestrator: AIOrchestrator | None = None):
        self.orch = orchestrator or get_orchestrator()

    async def score_transaction(
        self,
        tenant_id: str,
        txn_data: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            txn = Transaction(
                tenant_id=tenant_id,
                external_ref=txn_data.get("external_ref"),
                subject_identifier=txn_data["subject_identifier"],
                counterparty_identifier=txn_data.get("counterparty_identifier"),
                counterparty_country=txn_data.get("counterparty_country"),
                amount=Decimal(str(txn_data["amount"])),
                currency=txn_data["currency"],
                channel=txn_data["channel"],
                country=txn_data["country"],
                occurred_at=txn_data.get("occurred_at") or datetime.now(timezone.utc),
            )
            session.add(txn)
            await session.flush()

            recent = await self._recent_transactions(session, tenant_id, txn.subject_identifier, txn.id)
            rule_flags, rule_score = await self._evaluate_rules(session, tenant_id, txn, recent)

            prompt = (
                f"Transaction: amount={txn.amount} {txn.currency}, channel={txn.channel}, "
                f"country={txn.country}, counterparty_country={txn.counterparty_country or 'n/a'}\n"
                f"Deterministic rules triggered: {rule_flags or 'none'}\n"
                f"Recent transactions for this subject (last {VELOCITY_WINDOW_HOURS}h): "
                f"{len(recent)} totaling {sum((r.amount for r in recent), Decimal('0'))}\n\n"
                f"Assess AML risk.\n\nReturn JSON:\n{ANOMALY_SCHEMA}"
            )
            ai_result = await self.orch.infer(InferenceRequest(
                task=TaskType.ANOMALY_DETECTION,
                system=ANOMALY_SYSTEM,
                user_prompt=prompt,
                tenant_id=tenant_id,
                user_id=user_id,
                temperature=0.1,
                max_tokens=1024,
            ))
            ai_analysis = ai_result.parsed_json or {}
            ai_score = ai_analysis.get("risk_score")

            final_score = (
                round(0.4 * rule_score + 0.6 * ai_score) if isinstance(ai_score, (int, float))
                else rule_score
            )
            risk_level = _risk_level_for_score(final_score)
            recommended_action = ai_analysis.get("recommended_action", "ACCEPT" if final_score < 35 else "FLAG")

            if recommended_action == "BLOCK":
                status = TransactionStatus.BLOCKED
            elif final_score >= 35 or rule_flags:
                status = TransactionStatus.FLAGGED
            else:
                status = TransactionStatus.CLEARED

            txn.risk_score = final_score
            txn.risk_level = risk_level
            txn.rule_flags = rule_flags
            txn.ai_analysis = ai_analysis
            txn.status = status
            txn.scored_at = datetime.now(timezone.utc)

            await append_audit(
                session=session,
                tenant_id=tenant_id,
                event_type="transaction_screening",
                payload={
                    "transaction_id": str(txn.id),
                    "subject_identifier": txn.subject_identifier,
                    "amount": str(txn.amount),
                    "currency": txn.currency,
                    "rule_flags": rule_flags,
                    "risk_score": final_score,
                    "risk_level": risk_level.value,
                    "status": status.value,
                    "recommended_action": recommended_action,
                    "ai_audit_id": ai_result.audit_id,
                },
                user_id=user_id,
            )

            await session.commit()
            await session.refresh(txn)
            return self._to_dict(txn) | {
                "model_used": ai_result.model_used,
                "ai_success": ai_result.success,
            }

    async def _recent_transactions(
        self, session, tenant_id: str, subject_identifier: str, exclude_id: uuid.UUID
    ) -> list[Transaction]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=VELOCITY_WINDOW_HOURS)
        stmt = select(Transaction).where(
            Transaction.tenant_id == tenant_id,
            Transaction.subject_identifier == subject_identifier,
            Transaction.occurred_at >= cutoff,
            Transaction.id != exclude_id,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _evaluate_rules(
        self, session, tenant_id: str, txn: Transaction, recent: list[Transaction]
    ) -> tuple[list[str], int]:
        flags: list[str] = []
        score = 0

        if txn.amount >= CTR_THRESHOLD:
            flags.append("ctr_threshold")
            score += 20
        elif CTR_THRESHOLD - STRUCTURING_BAND <= txn.amount < CTR_THRESHOLD:
            flags.append("structuring_suspected")
            score += 35

        window_sum = sum((r.amount for r in recent), Decimal("0")) + txn.amount
        window_count = len(recent) + 1
        if window_count >= VELOCITY_MAX_COUNT or window_sum >= VELOCITY_MAX_SUM:
            flags.append("velocity_24h")
            score += 30

        if txn.counterparty_country and txn.counterparty_country in DEFAULT_HIGH_RISK_COUNTRIES:
            flags.append("high_risk_geography")
            score += 25

        custom = await self._tenant_rules(session, tenant_id)
        for rule in custom:
            if self._custom_rule_triggers(rule, txn, recent):
                flags.append(rule.rule_code)
                score += 20

        return flags, min(score, 100)

    @staticmethod
    async def _tenant_rules(session, tenant_id: str) -> list[TransactionRule]:
        stmt = select(TransactionRule).where(
            TransactionRule.tenant_id == tenant_id,
            TransactionRule.is_active.is_(True),
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _custom_rule_triggers(rule: TransactionRule, txn: Transaction, recent: list[Transaction]) -> bool:
        cfg = rule.config or {}
        if rule.rule_type == "amount_threshold":
            max_amount = cfg.get("max_amount")
            currency = cfg.get("currency")
            if max_amount is None:
                return False
            if currency and currency != txn.currency:
                return False
            return txn.amount >= Decimal(str(max_amount))

        if rule.rule_type == "geography":
            countries = set(cfg.get("high_risk_countries", []))
            return bool(txn.counterparty_country and txn.counterparty_country in countries)

        if rule.rule_type == "velocity":
            window_hours = cfg.get("window_hours", VELOCITY_WINDOW_HOURS)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            in_window = [r for r in recent if r.occurred_at >= cutoff]
            total = sum((r.amount for r in in_window), Decimal("0")) + txn.amount
            count = len(in_window) + 1
            return count >= cfg.get("max_count", 9999) or total >= Decimal(str(cfg.get("max_sum", "9e18")))

        if rule.rule_type == "structuring":
            threshold = Decimal(str(cfg.get("threshold", CTR_THRESHOLD)))
            band = Decimal(str(cfg.get("band", STRUCTURING_BAND)))
            return threshold - band <= txn.amount < threshold

        return False

    async def list_transactions(
        self,
        tenant_id: str,
        status: str | None = None,
        risk_level: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Transaction).where(Transaction.tenant_id == tenant_id)
            if status:
                stmt = stmt.where(Transaction.status == TransactionStatus(status))
            if risk_level:
                stmt = stmt.where(Transaction.risk_level == RiskLevel(risk_level))
            stmt = stmt.order_by(Transaction.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return [self._to_dict(t) for t in result.scalars().all()]

    async def get_transaction(self, tenant_id: str, transaction_id: str) -> dict[str, Any] | None:
        async with AsyncSessionLocal() as session:
            stmt = select(Transaction).where(
                Transaction.id == transaction_id, Transaction.tenant_id == tenant_id
            )
            result = await session.execute(stmt)
            txn = result.scalar_one_or_none()
            return self._to_dict(txn) if txn else None

    async def summary(self, tenant_id: str) -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Transaction.status, func.count(Transaction.id))
                .where(Transaction.tenant_id == tenant_id)
                .group_by(Transaction.status)
            )
            result = await session.execute(stmt)
            status_counts = {s.value: c for s, c in result.all()}

            stmt2 = (
                select(Transaction.risk_level, func.count(Transaction.id))
                .where(Transaction.tenant_id == tenant_id, Transaction.risk_level.isnot(None))
                .group_by(Transaction.risk_level)
            )
            result2 = await session.execute(stmt2)
            risk_counts = {r.value: c for r, c in result2.all()}

        return {"by_status": status_counts, "by_risk_level": risk_counts}

    @staticmethod
    def _to_dict(txn: Transaction) -> dict[str, Any]:
        return {
            "transaction_id": str(txn.id),
            "external_ref": txn.external_ref,
            "subject_identifier": txn.subject_identifier,
            "counterparty_identifier": txn.counterparty_identifier,
            "counterparty_country": txn.counterparty_country,
            "amount": str(txn.amount),
            "currency": txn.currency,
            "channel": txn.channel,
            "country": txn.country,
            "occurred_at": txn.occurred_at.isoformat() if txn.occurred_at else None,
            "status": txn.status.value if txn.status else None,
            "risk_score": txn.risk_score,
            "risk_level": txn.risk_level.value if txn.risk_level else None,
            "rule_flags": txn.rule_flags or [],
            "ai_analysis": txn.ai_analysis or {},
            "created_at": txn.created_at.isoformat() if txn.created_at else None,
            "scored_at": txn.scored_at.isoformat() if txn.scored_at else None,
        }


_engine = TransactionMonitoringEngine()


def get_transaction_engine() -> TransactionMonitoringEngine:
    return _engine
