"""
ComplianceOS — Ticketing Compliance AI Copilot (M9)

Answers compliance questions specific to ticketing platforms in LATAM.
Uses the AI orchestrator (COPILOT_QA / COPILOT_DEEP task types).
Returns structured JSON output aligned with the copilot schema.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.services.ai_orchestrator import get_orchestrator, TaskType


TICKETING_SYSTEM_PROMPT = """You are a senior compliance lawyer and regulatory expert
specializing in ticketing platforms across LATAM (Argentina, Brazil, Mexico, Colombia, Chile,
Peru, Uruguay, Paraguay).

You have deep knowledge of:
- Argentina: Consumer Protection Law 24.240, Resolution 424/2020 (Botón de Arrepentimiento),
  Personal Data Protection Law 25.326, AAIP database registration obligations,
  AFIP/ARCA electronic invoicing rules, CABA Law 5174 (anti-resale), UIF AML requirements
- Brazil: CDC (Consumer Defense Code), LGPD, PIX payment rules, PROCON obligations
- Mexico: LFCE, LFPDPPP, PROFECO consumer protection
- Colombia: Estatuto del Consumidor, SIC oversight, Habeas Data
- Chile: SERNAC consumer protection, Law 19.496, Ley 19.628 privacy
- Peru: INDECOPI consumer protection, Ley 29733 privacy
- Uruguay: URSEC/AUCAP, Ley 18.331 privacy
- Paraguay: SEDECO consumer protection

You respond ONLY with valid JSON in this exact structure:
{
  "summary": "concise 2-3 sentence answer",
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "missing_controls": ["list of missing compliance controls"],
  "required_documents": ["list of required legal documents"],
  "recommended_actions": ["ordered list of actions to take"],
  "country_specific_notes": ["country-specific regulatory notes"],
  "legal_disclaimer": "standard disclaimer text"
}

Be practical, specific, and cite the exact legal basis when possible.
Focus on actionable compliance steps, not vague advice.
"""


class TicketingCopilot:

    def __init__(self) -> None:
        self._orchestrator = get_orchestrator()

    async def ask(
        self,
        question: str,
        event_context: dict[str, Any] | None = None,
        country: str | None = None,
        deep_mode: bool = False,
        tenant_id: str = "default",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Answer a ticketing compliance question with structured output."""
        t0 = time.perf_counter()

        context_block = ""
        if event_context:
            context_block = f"\n\nEVENT CONTEXT:\n{json.dumps(event_context, indent=2, default=str)}"
        if country:
            context_block += f"\n\nPRIMARY COUNTRY: {country}"

        user_message = f"{question}{context_block}"

        task = TaskType.COPILOT_DEEP if deep_mode else TaskType.COPILOT_QA

        result = await self._orchestrator.infer(
            task=task,
            messages=[
                {"role": "system", "content": TICKETING_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            tenant_id=tenant_id,
            user_id=user_id,
        )

        latency_ms = int((time.perf_counter() - t0) * 1000)
        raw_answer = result.get("answer", "") if result.get("success") else ""

        structured = self._parse_structured(raw_answer)
        if not structured:
            structured = self._fallback_structure(question, country)

        return {
            "success": result.get("success", False),
            "question": question,
            "answer": structured,
            "model_used": result.get("model_used", ""),
            "latency_ms": latency_ms,
            "audit_id": result.get("audit_id"),
        }

    def _parse_structured(self, raw: str) -> dict | None:
        """Try to extract the structured JSON from the AI response."""
        if not raw:
            return None

        # Try direct parse
        try:
            parsed = json.loads(raw)
            if "summary" in parsed:
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting from ```json ... ``` blocks
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if "summary" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Try finding first { } block
        match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if "summary" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # If all parsing fails, wrap raw text in structured response
        return {
            "summary": raw[:500] if raw else "Unable to generate structured response.",
            "risk_level": "MEDIUM",
            "missing_controls": [],
            "required_documents": [],
            "recommended_actions": ["Review compliance requirements with legal counsel"],
            "country_specific_notes": [],
            "legal_disclaimer": (
                "This response is AI-generated and does not constitute legal advice. "
                "Consult qualified legal counsel before making compliance decisions."
            ),
        }

    def _fallback_structure(self, question: str, country: str | None) -> dict:
        """Return a graceful fallback when AI is unavailable."""
        country_note = f"Verify local {country} regulatory requirements." if country else ""
        return {
            "summary": (
                "AI copilot temporarily unavailable. Please review the regulatory matrix "
                "for applicable obligations and consult your compliance team."
            ),
            "risk_level": "MEDIUM",
            "missing_controls": [],
            "required_documents": [],
            "recommended_actions": [
                "Review the regulatory matrix for your target countries",
                "Complete the event compliance checklist",
                "Consult qualified legal counsel for country-specific requirements",
            ],
            "country_specific_notes": [country_note] if country_note else [],
            "legal_disclaimer": (
                "This response is AI-generated and does not constitute legal advice. "
                "Consult qualified legal counsel before making compliance decisions."
            ),
        }

    async def generate_document(
        self,
        document_type: str,
        event_context: dict[str, Any],
        country: str,
        tenant_id: str = "default",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a compliance document template for the given event and country."""

        doc_prompts: dict[str, str] = {
            "terms_and_conditions": (
                f"Generate complete Ticketing Terms & Conditions in Spanish for {country}. "
                "Include: purchase process, ticket delivery, refund and cancellation policy, "
                "force majeure, resale prohibition, consumer rights (Law 24.240 for AR), "
                "data privacy notice, dispute resolution, and governing law."
            ),
            "refund_policy": (
                f"Generate a detailed Refund and Cancellation Policy in Spanish for a ticketing "
                f"platform operating in {country}. Cover: consumer withdrawal rights (10 days), "
                "event cancellation full refund, postponement options, partial refunds, "
                "processing timeline, and how to submit a refund request."
            ),
            "privacy_policy": (
                f"Generate a comprehensive Privacy Policy in Spanish for a ticketing platform "
                f"operating in {country}. Include: data controller identity, types of personal data "
                "collected, legal basis, data retention, third-party sharing, data subject rights, "
                "cookie policy, marketing consent, and AAIP registration (for AR)."
            ),
            "promoter_agreement": (
                f"Generate a Promoter Compliance Schedule in Spanish for a ticketing platform "
                f"agreement in {country}. Cover: promoter representations and warranties, "
                "regulatory compliance obligations, liability allocation for refunds/chargebacks, "
                "cancellation/postponement protocol, data sharing, and indemnification."
            ),
            "chargeback_evidence": (
                "Generate a Chargeback Evidence Checklist for a ticketing platform. "
                "Cover: proof of purchase, delivery confirmation, communications log, "
                "refund policy acknowledgment, IP address logs, and dispute timeline."
            ),
            "cancellation_notice": (
                f"Generate an Event Cancellation Notice template in Spanish for {country}. "
                "Include: event details, reason for cancellation, refund process and timeline, "
                "consumer contact information, and legal rights reference."
            ),
            "postponement_notice": (
                f"Generate an Event Postponement Notice template in Spanish for {country}. "
                "Include: new date (TBD), original date, reason, ticket validity, "
                "refund option for consumers who cannot attend the new date, and contact."
            ),
            "resale_policy": (
                f"Generate a Ticket Resale Policy in Spanish for a ticketing platform in {country}. "
                "Cover: authorized transfer process, price cap rules, anti-scalping controls, "
                "platform liability limits, identity verification for transfers, "
                "and CABA Law 5174 compliance (for AR events)."
            ),
            "complaint_response": (
                "Generate a Consumer Complaint Response template in Spanish for a ticketing platform. "
                "Include: acknowledgment, investigation process, resolution timeline, "
                "escalation path, and consumer rights notice."
            ),
            "venue_authorization": (
                f"Generate a Venue Authorization Checklist for ticketing compliance in {country}. "
                "Include: venue license, fire safety certificate, max capacity authorization, "
                "accessibility compliance, security plan, first aid station, and insurance."
            ),
            "data_processing_agreement": (
                f"Generate a Data Processing Agreement checklist for third-party vendors "
                f"of a ticketing platform in {country}. Include: data categories, processing "
                "purposes, security measures, sub-processor approval, breach notification, "
                "data subject rights support, and audit rights."
            ),
        }

        prompt = doc_prompts.get(document_type, f"Generate a {document_type} document for {country}.")

        if event_context:
            prompt += f"\n\nEvent context: {json.dumps(event_context, default=str)}"

        result = await self._orchestrator.infer(
            task=TaskType.COPILOT_QA,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a compliance lawyer specializing in LATAM ticketing regulation. "
                        "Generate professional, legally-grounded compliance document templates in Spanish. "
                        "Be comprehensive and cite relevant legal provisions."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return {
            "success": result.get("success", False),
            "document_type": document_type,
            "country": country,
            "content": result.get("answer", "Document generation failed. Please try again."),
            "model_used": result.get("model_used", ""),
        }
