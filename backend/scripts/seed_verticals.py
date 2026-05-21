"""
ComplianceOS — Multi-Vertical Seed Data
=========================================
Populates vertical_regulators and vertical_obligation_types tables.
Run: docker compose exec backend python -m scripts.seed_verticals
"""
from __future__ import annotations

import asyncio
import uuid

from app.db.base import AsyncSessionLocal
from app.db.models import VerticalRegulator, VerticalObligationType


VERTICAL_REGULATORS_DATA = [
    # (vertical, country, code, name, url, schedule_hours)
    # FINTECH
    ("FINTECH",       "AR",   "BCRA",     "Banco Central de la República Argentina",              "https://bcra.gob.ar",                    6),
    ("FINTECH",       "AR",   "UIF",      "Unidad de Información Financiera",                     "https://uif.gob.ar",                     12),
    ("FINTECH",       "AR",   "CNV",      "Comisión Nacional de Valores",                         "https://cnv.gob.ar",                     12),
    ("FINTECH",       "BR",   "BACEN",    "Banco Central do Brasil",                              "https://bcb.gov.br",                      8),
    ("FINTECH",       "BR",   "COAF",     "Conselho de Controle de Atividades Financeiras",       "https://coaf.fazenda.gov.br",            12),
    ("FINTECH",       "MX",   "CNBV",     "Comisión Nacional Bancaria y de Valores",              "https://cnbv.gob.mx",                    12),
    ("FINTECH",       "CO",   "SFC",      "Superintendencia Financiera de Colombia",              "https://superfinanciera.gov.co",         12),
    ("FINTECH",       "CL",   "CMF",      "Comisión para el Mercado Financiero",                  "https://cmfchile.cl",                    12),
    ("FINTECH",       "PE",   "SBS",      "Superintendencia de Banca y Seguros",                  "https://sbs.gob.pe",                     12),
    # CRYPTO_VASP
    ("CRYPTO_VASP",   "AR",   "BCRA",     "BCRA — Registro VASP (Com. A 8094)",                  "https://bcra.gob.ar",                     6),
    ("CRYPTO_VASP",   "AR",   "UIF",      "UIF — Obligaciones VASP (Res. 300/2024)",             "https://uif.gob.ar",                     12),
    ("CRYPTO_VASP",   "INTL", "FATF",     "Financial Action Task Force",                          "https://fatf-gafi.org",                  24),
    ("CRYPTO_VASP",   "INTL", "OFAC",     "Office of Foreign Assets Control",                     "https://home.treasury.gov/policy-issues/office-of-foreign-assets-control-sanctions-programs-and-information", 24),
    # INSURANCE
    ("INSURANCE",     "AR",   "SSN",      "Superintendencia de Seguros de la Nación",             "https://ssn.gob.ar",                     24),
    ("INSURANCE",     "BR",   "SUSEP",    "Superintendência de Seguros Privados",                 "https://susep.gov.br",                   24),
    ("INSURANCE",     "MX",   "CNSF",     "Comisión Nacional de Seguros y Fianzas",               "https://cnsf.gob.mx",                    24),
    ("INSURANCE",     "CO",   "SFC",      "Superintendencia Financiera — Seguros",                "https://superfinanciera.gov.co",         24),
    ("INSURANCE",     "CL",   "CMF",      "CMF — Seguros",                                        "https://cmfchile.cl",                    24),
    # HEALTH_PHARMA
    ("HEALTH_PHARMA", "AR",   "ANMAT",    "Administración Nacional de Medicamentos",              "https://anmat.gob.ar",                   24),
    ("HEALTH_PHARMA", "BR",   "ANVISA",   "Agência Nacional de Vigilância Sanitária",             "https://anvisa.gov.br",                  24),
    ("HEALTH_PHARMA", "MX",   "COFEPRIS", "Comisión Federal para la Protección contra Riesgos Sanitarios", "https://cofepris.salud.gob.mx", 24),
    ("HEALTH_PHARMA", "CO",   "INVIMA",   "Instituto Nacional de Vigilancia de Medicamentos",     "https://invima.gov.co",                  24),
    ("HEALTH_PHARMA", "CL",   "ISP",      "Instituto de Salud Pública de Chile",                  "https://ispch.cl",                       24),
    # GAMING
    ("GAMING",        "AR",   "LOTBA",    "Lotería de la Ciudad de Buenos Aires",                 "https://lotba.gob.ar",                   12),
    ("GAMING",        "MX",   "SEGOB",    "Secretaría de Gobernación — Juegos y Sorteos",         "https://segob.gob.mx",                   24),
    ("GAMING",        "CO",   "COLJUEGOS","Empresa Industrial y Comercial Coljuegos",              "https://coljuegos.gov.co",               24),
    ("GAMING",        "INTL", "MGA",      "Malta Gaming Authority",                               "https://mga.org.mt",                     24),
    # CAPITAL_MARKETS
    ("CAPITAL_MARKETS","AR",  "CNV",      "Comisión Nacional de Valores",                         "https://cnv.gob.ar",                      6),
    ("CAPITAL_MARKETS","BR",  "CVM",      "Comissão de Valores Mobiliários",                      "https://cvm.gov.br",                     12),
    ("CAPITAL_MARKETS","CL",  "CMF",      "CMF — Valores",                                        "https://cmfchile.cl",                    12),
    ("CAPITAL_MARKETS","CO",  "SFC",      "SFC — Valores",                                        "https://superfinanciera.gov.co",         12),
    ("CAPITAL_MARKETS","MX",  "CNBV",     "CNBV — Valores",                                       "https://cnbv.gob.mx",                    12),
    # TELECOM
    ("TELECOM",       "AR",   "ENACOM",   "Ente Nacional de Comunicaciones",                      "https://enacom.gob.ar",                  24),
    ("TELECOM",       "BR",   "ANATEL",   "Agência Nacional de Telecomunicações",                 "https://anatel.gov.br",                  24),
    ("TELECOM",       "MX",   "IFT",      "Instituto Federal de Telecomunicaciones",              "https://ift.org.mx",                     24),
    ("TELECOM",       "CO",   "CRC",      "Comisión de Regulación de Comunicaciones",             "https://crcom.gov.co",                   24),
    ("TELECOM",       "CL",   "SUBTEL",   "Subsecretaría de Telecomunicaciones",                  "https://subtel.gob.cl",                  24),
]


VERTICAL_OBLIGATION_TYPES_DATA = [
    # (vertical, obligation_type, description, default_deadline_days, severity)
    ("FINTECH",         "KYC_EDD",              "Enhanced Due Diligence for high-risk customers",              30,  "high"),
    ("FINTECH",         "AML_REPORT",           "Suspicious Activity Report to FIU",                          150, "critical"),
    ("FINTECH",         "FUND_SEGREGATION",     "Client funds must be segregated from operational funds",        5, "critical"),
    ("FINTECH",         "REPORTING",            "Periodic regulatory reporting to supervisor",                  30, "high"),
    ("FINTECH",         "LICENSING",            "Maintain valid operating license",                           365, "critical"),
    ("CRYPTO_VASP",     "KYC_EDD",              "Travel Rule and EDD for crypto transactions > threshold",      30, "high"),
    ("CRYPTO_VASP",     "AML_REPORT",           "RoF to UIF for suspicious crypto operations",               150, "critical"),
    ("CRYPTO_VASP",     "VASP_REGISTRATION",    "Registration with BCRA as VASP (Com. A 8094)",              None, "critical"),
    ("CRYPTO_VASP",     "TRAVEL_RULE",          "FATF Rec. 16 Travel Rule information sharing",               None, "high"),
    ("CRYPTO_VASP",     "SANCTIONS",            "OFAC/UN sanctions screening on all transactions",            None, "critical"),
    ("INSURANCE",       "TECHNICAL_RESERVES",   "Calculate and maintain minimum technical reserves",            90, "critical"),
    ("INSURANCE",       "SOLVENCY_REPORT",      "Quarterly solvency margin report to SSN/SUSEP",               30, "high"),
    ("INSURANCE",       "ACTUARIAL_FILING",     "Annual actuarial report by certified actuary",               365, "high"),
    ("INSURANCE",       "REINSURANCE",          "Notify regulator of reinsurance arrangements",                30, "medium"),
    ("HEALTH_PHARMA",   "GMP_COMPLIANCE",       "Good Manufacturing Practice compliance and audit",           365, "critical"),
    ("HEALTH_PHARMA",   "PHARMACOVIGILANCE",    "Adverse event reporting within 15 days (serious events)",     15, "critical"),
    ("HEALTH_PHARMA",   "CLINICAL_TRIAL_REPORTING", "Clinical trial result reporting to ANMAT/ANVISA",        180, "high"),
    ("HEALTH_PHARMA",   "RECALL",               "Product recall notification to regulator within 24h",          1, "critical"),
    ("GAMING",          "AML_REPORT",           "Suspicious betting pattern report to FIU",                   150, "critical"),
    ("GAMING",          "AGE_VERIFICATION",     "Verify player age before account activation",                None, "critical"),
    ("GAMING",          "LICENSING",            "Annual gaming license renewal",                              365, "critical"),
    ("GAMING",          "RESPONSIBLE_GAMBLING", "Implement self-exclusion and betting limits mechanisms",     None, "high"),
    ("CAPITAL_MARKETS", "PROSPECTUS",           "File and publish prospectus before public offering",          30, "critical"),
    ("CAPITAL_MARKETS", "PERIODIC_REPORTING",   "Quarterly financial reporting to CNV/CVM",                   45, "high"),
    ("CAPITAL_MARKETS", "INSIDER_TRADING",      "Maintain insider trading prevention policy",                None, "critical"),
    ("CAPITAL_MARKETS", "CUSTODY",              "Comply with custody and settlement requirements",           None, "high"),
    ("TELECOM",         "DATA_BREACH_NOTIFICATION", "Notify regulator and users of data breach within 72h",    3, "critical"),
    ("TELECOM",         "QOS_REPORTING",        "Quarterly Quality of Service reporting to ENACOM/ANATEL",    90, "medium"),
    ("TELECOM",         "SPECTRUM_LICENSE",     "Annual spectrum license fee and renewal",                   365, "high"),
    ("TELECOM",         "CONSUMER_PROTECTION",  "Maintain consumer complaint registry and SLA",              None, "medium"),
]


async def seed_verticals() -> None:
    print("Seeding multi-vertical regulatory data...")

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Seed VerticalRegulator
        reg_count = 0
        for v, country, code, name, url, hours in VERTICAL_REGULATORS_DATA:
            existing = (await session.execute(
                select(VerticalRegulator).where(
                    VerticalRegulator.vertical == v,
                    VerticalRegulator.country == country,
                    VerticalRegulator.regulator_code == code,
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(VerticalRegulator(
                    id=uuid.uuid4(),
                    vertical=v,
                    country=country,
                    regulator_code=code,
                    regulator_name=name,
                    regulator_url=url,
                    schedule_hours=hours,
                ))
                reg_count += 1

        # Seed VerticalObligationType
        obl_count = 0
        for v, obl_type, desc, deadline, sev in VERTICAL_OBLIGATION_TYPES_DATA:
            existing = (await session.execute(
                select(VerticalObligationType).where(
                    VerticalObligationType.vertical == v,
                    VerticalObligationType.obligation_type == obl_type,
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(VerticalObligationType(
                    id=uuid.uuid4(),
                    vertical=v,
                    obligation_type=obl_type,
                    description=desc,
                    default_deadline_days=deadline,
                    severity=sev,
                ))
                obl_count += 1

        await session.commit()
        print(f"  {reg_count} regulators seeded")
        print(f"  {obl_count} obligation types seeded")
        print("Multi-vertical seed complete.")


if __name__ == "__main__":
    asyncio.run(seed_verticals())
