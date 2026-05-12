"""
ComplianceOS — Demo Seed
=========================
Run: docker compose exec backend python -m scripts.seed_demo
"""

import asyncio
from datetime import datetime, timezone

from app.db.base import AsyncSessionLocal, engine, Base
from app.db.models import Tenant, Regulation


SAMPLE_REGULATIONS = [
    {
        "country": "AR",
        "regulator": "BCRA",
        "code": "Com. A 7825",
        "title": "Régimen de Proveedores de Servicios de Pago que ofrecen cuentas de pago",
        "text": """Los Proveedores de Servicios de Pago que ofrecen cuentas de pago (PSPCP)
deberán mantener el 100% de los fondos de los clientes en cuentas a la vista en pesos
en entidades financieras del país, sin posibilidad de invertirlos. Deberán informar
mensualmente al BCRA el detalle de saldos al último día hábil del mes anterior, dentro
de los primeros cinco días hábiles del mes siguiente. Deberán reportar dentro de las 24
horas cualquier evento que afecte la disponibilidad de fondos. El incumplimiento será
sancionado conforme al régimen de la Ley 21.526.""",
    },
    {
        "country": "AR",
        "regulator": "UIF",
        "code": "Res. 30/2017",
        "title": "Reporte de Operaciones Sospechosas",
        "text": """Los Sujetos Obligados deberán reportar a la UIF las operaciones sospechosas
de lavado de activos o financiación del terrorismo dentro de los 150 días corridos contados
desde la fecha de la operación o tentativa, a través del sistema en línea. Deberán mantener
registros de la operativa de sus clientes durante diez (10) años. La política de Conozca a su
Cliente (KYC) debe incluir identificación del beneficiario final, perfil transaccional, y monitoreo
continuo. Las operaciones de Personas Expuestas Políticamente (PEP) requieren Debida Diligencia
Reforzada y aprobación de la máxima autoridad del Sujeto Obligado.""",
    },
    {
        "country": "BR",
        "regulator": "BACEN",
        "code": "Circular 4015/2020",
        "title": "Política de Prevenção à Lavagem de Dinheiro",
        "text": """As instituições financeiras devem implementar políticas de prevenção à lavagem
de dinheiro proporcionais ao porte, natureza e complexidade dos seus negócios. As operações
em espécie iguais ou superiores a R$ 50.000,00 devem ser comunicadas ao COAF em até um dia útil.
A identificação do beneficiário final é obrigatória para todas as relações de negócio. O monitoramento
deve ser contínuo e baseado em análise de risco.""",
    },
]


async def seed():
    print("🌱 Seeding ComplianceOS demo data...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✓ Schema created")

    async with AsyncSessionLocal() as session:
        tenant = Tenant(
            slug="polkorp",
            name="Polkorp Global Ventures",
            sector="multi",
            jurisdictions=["AR", "BR", "MX", "CL", "CO", "UY", "PE"],
            data_residency_policy={
                "ai_providers_allowed": ["nvidia", "anthropic"],
                "pii_tokenization_required": True,
            },
        )
        session.add(tenant)
        await session.flush()
        print(f"  ✓ Tenant: {tenant.name}")

        for reg_data in SAMPLE_REGULATIONS:
            reg = Regulation(
                country=reg_data["country"],
                regulator=reg_data["regulator"],
                code=reg_data["code"],
                title=reg_data["title"],
                full_text=reg_data["text"],
                published_at=datetime.now(timezone.utc),
            )
            session.add(reg)
            print(f"  ✓ Regulation: {reg.country} / {reg.regulator} / {reg.code}")

        await session.commit()

    print("\n✓ Demo seed complete.")
    print("  Try: curl http://localhost:8000/api/v1/meta/models")


if __name__ == "__main__":
    asyncio.run(seed())
