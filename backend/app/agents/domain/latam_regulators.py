"""
Domain Agents for LATAM Jurisdictions

Each domain agent owns regulatory intelligence for one country/regulator.
They track regulations, applicable sectors, deadline rules, and enforcement.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base import Agent, AgentResult, AgentType
from app.db.models import Regulation, Obligation

logger = logging.getLogger(__name__)


class LatamDomainAgent(Agent):
    """Base class for all LATAM regulatory domain agents."""

    def __init__(self, jurisdiction: str, regulators: list[str], country_name: str):
        self.jurisdiction = jurisdiction  # "AR", "BR", etc.
        self.country_name = country_name
        self.regulators = regulators  # ["BCB", "CVM"], etc.
        self.applicable_sectors = []

        super().__init__(
            agent_id=f"domain:{jurisdiction.lower()}",
            agent_type=AgentType.DOMAIN,
            tenant_id="system",
        )

    @property
    def capabilities(self) -> list[str]:
        return [
            f"regulations:fetch:{self.jurisdiction}",
            f"obligations:track:{self.jurisdiction}",
            f"deadlines:enforce:{self.jurisdiction}",
            f"sector-mapping:{self.jurisdiction}",
        ]

    async def execute(self, context: dict[str, Any], db_session: AsyncSession) -> AgentResult:
        """Route to task handler."""
        task = context.get("task", "assess_entity")

        if task == "assess_entity":
            return await self._assess_entity_for_jurisdiction(context, db_session)
        elif task == "fetch_regulations":
            return await self._fetch_regulations(context, db_session)
        elif task == "check_applicable_obligations":
            return await self._check_applicable_obligations(context, db_session)
        else:
            return AgentResult(success=False, error=f"Unknown task: {task}")

    async def _assess_entity_for_jurisdiction(
        self, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """
        Assess entity compliance w.r.t. this jurisdiction's regulations.

        Returns:
        - applicable regulations
        - applicable obligations
        - key deadlines
        - enforcement risk
        """
        try:
            tenant_id = context.get("tenant_id")
            entity_id = context.get("entity_id")
            entity_sectors = context.get("sectors", [])

            # Get regulations for this jurisdiction applicable to entity's sectors
            regs = (
                await db_session.execute(
                    select(Regulation).where(
                        Regulation.country == self.jurisdiction,
                        (Regulation.sector.in_(entity_sectors) | (Regulation.sector.is_(None)))
                        if entity_sectors
                        else True,
                    )
                )
            ).scalars().all()

            # Get obligations from those regulations
            obligations = (
                await db_session.execute(
                    select(Obligation).where(
                        Obligation.regulation_id.in_([r.id for r in regs])
                    )
                )
            ).scalars().all()

            return AgentResult(
                success=True,
                data={
                    "jurisdiction": self.jurisdiction,
                    "country": self.country_name,
                    "applicable_regulations": len(regs),
                    "applicable_obligations": len(obligations),
                    "key_regulators": self.regulators,
                    "enforcement_risk": self._assess_enforcement_risk(obligations),
                    "summary": f"Entity subject to {len(regs)} regulations in {self.country_name}",
                },
                agent_id=self.agent_id,
            )

        except Exception as e:
            logger.error(f"Error assessing entity for {self.jurisdiction}: {e}")
            return AgentResult(success=False, error=str(e), agent_id=self.agent_id)

    async def _fetch_regulations(
        self, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """
        Fetch and index latest regulations for this jurisdiction.

        In production, this would call regulatory crawlers.
        """
        logger.info(f"Fetching regulations for {self.country_name}")

        # Placeholder: real implementation calls crawler
        return AgentResult(
            success=True,
            data={
                "jurisdiction": self.jurisdiction,
                "regulations_fetched": 0,
                "new_regulations": 0,
                "updated_regulations": 0,
                "last_fetch": None,
            },
            agent_id=self.agent_id,
        )

    async def _check_applicable_obligations(
        self, context: dict[str, Any], db_session: AsyncSession
    ) -> AgentResult:
        """
        Check which obligations apply to entity based on sectors + entity_type.
        """
        try:
            entity_sectors = context.get("sectors", [])
            entity_type = context.get("entity_type", "company")

            # Filter obligations by sector + entity_type
            # (placeholder; real implementation has complex logic)
            applicable = []

            return AgentResult(
                success=True,
                data={
                    "jurisdiction": self.jurisdiction,
                    "applicable_obligations": applicable,
                    "filtered_by": {"sectors": entity_sectors, "entity_type": entity_type},
                },
                agent_id=self.agent_id,
            )

        except Exception as e:
            return AgentResult(success=False, error=str(e), agent_id=self.agent_id)

    def _assess_enforcement_risk(self, obligations: list) -> str:
        """
        Estimate enforcement risk based on obligation count + severity.
        """
        if not obligations:
            return "low"

        critical_count = sum(
            1 for o in obligations
            if hasattr(o, "severity") and o.severity and "CRITICAL" in str(o.severity).upper()
        )

        if critical_count >= 3:
            return "critical"
        elif critical_count >= 1 or len(obligations) >= 10:
            return "high"
        elif len(obligations) >= 5:
            return "medium"
        else:
            return "low"


# Concrete domain agents for each LATAM jurisdiction


class ArgentinaAgent(LatamDomainAgent):
    """Central Bank of Argentina (BCRA) + Tax Authority (AFIP)."""

    def __init__(self):
        super().__init__(
            jurisdiction="AR",
            regulators=["BCRA", "AFIP", "CNV"],
            country_name="Argentina",
        )
        self.applicable_sectors = [
            "banking",
            "fintech",
            "insurance",
            "securities",
            "crypto",
        ]

    @property
    def role(self) -> str:
        return "Argentina Regulatory Specialist (BCRA/AFIP)"


class BrazilAgent(LatamDomainAgent):
    """Central Bank of Brazil (BCB) + Securities Commission (CVM)."""

    def __init__(self):
        super().__init__(
            jurisdiction="BR",
            regulators=["BCB", "CVM", "COAF"],
            country_name="Brazil",
        )
        self.applicable_sectors = [
            "banking",
            "fintech",
            "insurance",
            "securities",
            "crypto",
            "pix",
        ]

    @property
    def role(self) -> str:
        return "Brazil Regulatory Specialist (BCB/CVM)"


class ColombiaAgent(LatamDomainAgent):
    """Superintendence of Finance (SuperFinanciera)."""

    def __init__(self):
        super().__init__(
            jurisdiction="CO",
            regulators=["SuperFinanciera", "DIAN"],
            country_name="Colombia",
        )
        self.applicable_sectors = ["banking", "fintech", "insurance", "securities"]

    @property
    def role(self) -> str:
        return "Colombia Regulatory Specialist (SuperFinanciera)"


class ChileAgent(LatamDomainAgent):
    """Financial Market Commission (CMF) + SBIF."""

    def __init__(self):
        super().__init__(
            jurisdiction="CL",
            regulators=["CMF", "SBIF"],
            country_name="Chile",
        )
        self.applicable_sectors = ["banking", "fintech", "insurance", "securities", "pension"]

    @property
    def role(self) -> str:
        return "Chile Regulatory Specialist (CMF/SBIF)"


class MexicoAgent(LatamDomainAgent):
    """National Banking and Securities Commission (CNBV) + SHCP."""

    def __init__(self):
        super().__init__(
            jurisdiction="MX",
            regulators=["CNBV", "SAT", "SHCP"],
            country_name="Mexico",
        )
        self.applicable_sectors = [
            "banking",
            "fintech",
            "insurance",
            "securities",
            "pension",
        ]

    @property
    def role(self) -> str:
        return "Mexico Regulatory Specialist (CNBV)"


class AndeanAgent(LatamDomainAgent):
    """Multi-country Andean Community (CAN) regulator (CONASIF)."""

    def __init__(self):
        super().__init__(
            jurisdiction="ANDEAN",
            regulators=["CONASIF"],
            country_name="Andean Community (Multinational)",
        )
        self.applicable_sectors = [
            "banking",
            "fintech",
            "insurance",
            "securities",
        ]

    @property
    def role(self) -> str:
        return "Andean Community Regulatory Specialist (CONASIF)"
