"""
ComplianceOS — Ticketing Module Seed Data

Argentina obligations and LATAM country profiles for initial seeding.
All data is based on current regulations as of 2026.
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════
# COUNTRY PROFILES
# ═══════════════════════════════════════════════════════════════════

COUNTRY_PROFILES: list[dict[str, Any]] = [
    {
        "country_code": "AR",
        "country_name": "Argentina",
        "risk_level": "HIGH",
        "risk_score": 75,
        "requires_boton_arrepentimiento": True,
        "requires_aaip_registration": True,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": True,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 10,
        "currency": "ARS",
        "regulator_consumer": "Secretaría de Comercio Interior / COPREC",
        "regulator_data_privacy": "AAIP (Agencia de Acceso a la Información Pública)",
        "regulator_payments": "BCRA / Coelsa",
        "regulator_tax": "AFIP / ARCA",
        "notes": "High enforcement risk. AFIP, AAIP, and BCRA actively audit digital commerce.",
    },
    {
        "country_code": "BR",
        "country_name": "Brazil",
        "risk_level": "HIGH",
        "risk_score": 65,
        "requires_boton_arrepentimiento": True,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 7,
        "currency": "BRL",
        "regulator_consumer": "PROCON / Senacon / SINDEC",
        "regulator_data_privacy": "ANPD (Autoridade Nacional de Proteção de Dados)",
        "regulator_payments": "Banco Central do Brasil",
        "regulator_tax": "Receita Federal",
        "notes": "CDC Art. 49 grants 7-day cooling-off period. LGPD applies to all data processing.",
    },
    {
        "country_code": "MX",
        "country_name": "Mexico",
        "risk_level": "MEDIUM",
        "risk_score": 55,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 5,
        "currency": "MXN",
        "regulator_consumer": "PROFECO (Procuraduría Federal del Consumidor)",
        "regulator_data_privacy": "INAI (Instituto Nacional de Transparencia)",
        "regulator_payments": "CNBV / Banxico",
        "regulator_tax": "SAT",
        "notes": "LFCE and PROFECO regulate consumer protection. CFDI required for all sales.",
    },
    {
        "country_code": "CO",
        "country_name": "Colombia",
        "risk_level": "MEDIUM",
        "risk_score": 50,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 5,
        "currency": "COP",
        "regulator_consumer": "SIC (Superintendencia de Industria y Comercio)",
        "regulator_data_privacy": "SIC — División de Habeas Data",
        "regulator_payments": "Superfinanciera",
        "regulator_tax": "DIAN",
        "notes": "Estatuto del Consumidor (Ley 1480) governs e-commerce and reversals.",
    },
    {
        "country_code": "CL",
        "country_name": "Chile",
        "risk_level": "MEDIUM",
        "risk_score": 45,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 10,
        "currency": "CLP",
        "regulator_consumer": "SERNAC (Servicio Nacional del Consumidor)",
        "regulator_data_privacy": "Consejo para la Transparencia",
        "regulator_payments": "CMF (Comisión para el Mercado Financiero)",
        "regulator_tax": "SII",
        "notes": "Law 19.496 grants 10-day right of retraction for distance purchases.",
    },
    {
        "country_code": "PE",
        "country_name": "Peru",
        "risk_level": "MEDIUM",
        "risk_score": 60,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 0,
        "currency": "PEN",
        "regulator_consumer": "INDECOPI",
        "regulator_data_privacy": "Autoridad Nacional de Protección de Datos Personales",
        "regulator_payments": "SBS (Superintendencia de Banca y Seguros)",
        "regulator_tax": "SUNAT",
        "notes": "INDECOPI actively enforces consumer rights. Electronic billing mandatory for most sectors.",
    },
    {
        "country_code": "UY",
        "country_name": "Uruguay",
        "risk_level": "LOW",
        "risk_score": 40,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 5,
        "currency": "UYU",
        "regulator_consumer": "AUCAP (Área de Defensa del Consumidor)",
        "regulator_data_privacy": "URCDP (Unidad Reguladora de Control de Datos Personales)",
        "regulator_payments": "BCU (Banco Central del Uruguay)",
        "regulator_tax": "DGI",
        "notes": "Ley 17.250 consumer protection. Ley 18.331 personal data protection.",
    },
    {
        "country_code": "PY",
        "country_name": "Paraguay",
        "risk_level": "LOW",
        "risk_score": 35,
        "requires_boton_arrepentimiento": False,
        "requires_aaip_registration": False,
        "requires_electronic_invoice": True,
        "requires_anti_resale_controls": False,
        "requires_promoter_permit": True,
        "withdrawal_period_days": 0,
        "currency": "PYG",
        "regulator_consumer": "SEDECO (Secretaría de Defensa del Consumidor y el Usuario)",
        "regulator_data_privacy": "SEDECO / MITIC",
        "regulator_payments": "BCP (Banco Central del Paraguay)",
        "regulator_tax": "SET (Subsecretaría de Estado de Tributación)",
        "notes": "Ley 1334/98 consumer protection. E-invoicing progressively required.",
    },
]


# ═══════════════════════════════════════════════════════════════════
# ARGENTINA OBLIGATIONS (initial seed — full set)
# ═══════════════════════════════════════════════════════════════════

ARGENTINA_OBLIGATIONS: list[dict[str, Any]] = [
    {
        "country_code": "AR",
        "legal_area": "consumer_protection",
        "title": "Botón de Arrepentimiento / Derecho de Retracto Online",
        "description": (
            "All e-commerce platforms must display a visible 'Botón de Arrepentimiento' on their homepage "
            "and post-purchase confirmation pages. Consumers have 10 days to revoke a purchase without "
            "penalty. Refund must be processed within 10 business days of the revocation request."
        ),
        "legal_basis": "Ley 24.240 Art. 34; Resolución 424/2020 (Secretaría de Comercio)",
        "owner_role": "Legal / Product",
        "risk_level": "CRITICAL",
        "required_evidence": [
            "Screenshot of botón visible on homepage",
            "Screenshot of post-purchase confirmation with button",
            "Revocation request form/flow documentation",
            "Refund processing workflow documentation",
        ],
        "controls": ["has_withdrawal_button", "has_refund_policy"],
        "deadline_frequency": "Continuous — per platform operation",
        "penalties_summary": "Fines up to ARS 5,000,000 per violation. Platform suspension possible. COPREC complaints.",
        "ai_explanation": (
            "The Botón de Arrepentimiento is one of Argentina's most enforced e-commerce obligations. "
            "Resolution 424/2020 requires it to be prominently visible — not buried in T&C. "
            "Ticketing platforms are explicitly covered under Law 24.240 as distance commerce operators."
        ),
        "recommended_action": (
            "Add a clearly labeled 'Arrepentimiento de compra' button to homepage header, "
            "post-purchase email, and account dashboard. Link to a self-service revocation form "
            "that auto-triggers the refund workflow."
        ),
        "is_blocker": True,
    },
    {
        "country_code": "AR",
        "legal_area": "refunds_cancellations",
        "title": "Política de Reembolso y Cancelación de Evento",
        "description": (
            "Ticketing platforms must maintain a clear refund and cancellation policy accessible "
            "before purchase. For consumer-initiated refunds within 10 days, full refund is mandatory. "
            "For event cancellation by organizer, full refund including service fees is required. "
            "For postponement, consumer must have option to attend new date or receive full refund."
        ),
        "legal_basis": "Ley 24.240 Arts. 10, 19, 34; Res. 424/2020",
        "owner_role": "Legal / Operations",
        "risk_level": "HIGH",
        "required_evidence": [
            "Refund policy document",
            "Refund processing records",
            "Consumer communication templates",
        ],
        "controls": ["has_refund_policy", "has_cancellation_clause", "has_postponement_clause"],
        "deadline_frequency": "Continuous — displayed before purchase",
        "penalties_summary": "Fines up to ARS 1,000,000. Mandatory refund plus interest for delays.",
        "ai_explanation": (
            "Argentina's consumer law requires refund policies to be visible BEFORE the purchase, "
            "not just in T&C. For ticketing, cancellation policies must cover force majeure events "
            "and organizer-initiated cancellations separately from consumer retraction."
        ),
        "recommended_action": (
            "Display refund policy summary on event page, checkout flow, and confirmation email. "
            "Implement automated refund trigger for event cancellations within 24 hours of organizer notification."
        ),
        "is_blocker": True,
    },
    {
        "country_code": "AR",
        "legal_area": "ecommerce",
        "title": "Términos y Condiciones Visibles Antes del Checkout",
        "description": (
            "Consumers must be presented with and must accept the platform's Terms & Conditions "
            "before completing a purchase. The T&C must be in Spanish, clearly legible, and must "
            "include: product/service description, total price breakdown (including service fees and taxes), "
            "refund policy, withdrawal rights, complaint channel, and governing law."
        ),
        "legal_basis": "Ley 24.240 Art. 10; Decreto 1798/94; Res. 139/2020 (Comercio Interior)",
        "owner_role": "Legal / Product",
        "risk_level": "HIGH",
        "required_evidence": [
            "T&C document (Spanish)",
            "Checkout screenshot showing T&C acceptance checkbox",
            "Version history of T&C changes",
        ],
        "controls": ["has_consumer_terms"],
        "deadline_frequency": "Continuous — per purchase flow",
        "penalties_summary": "Fines up to ARS 5,000,000 per violation. Unenforceable contracts risk.",
        "ai_explanation": (
            "Without visible T&C before purchase, the contract may be unenforceable and the platform "
            "loses the ability to rely on its own terms in chargeback disputes. COPREC accepts complaints "
            "when T&C are not visible before checkout."
        ),
        "recommended_action": (
            "Add a mandatory checkbox at checkout: 'Acepto los Términos y Condiciones y la Política de Privacidad.' "
            "Link both documents. Store acceptance with timestamp and IP for audit."
        ),
        "is_blocker": True,
    },
    {
        "country_code": "AR",
        "legal_area": "ecommerce",
        "title": "Transparencia de Precio y Cargos de Servicio",
        "description": (
            "All service fees, taxes, and charges must be disclosed before the final checkout step. "
            "The total price (including all fees) must be the primary price displayed. "
            "Dynamic pricing (surge pricing) must comply with Secretaría de Comercio guidelines."
        ),
        "legal_basis": "Ley 24.240 Art. 10; Ley 24.240 Art. 7 (oferta); Res. 14/2020",
        "owner_role": "Product / Finance",
        "risk_level": "HIGH",
        "required_evidence": [
            "Price breakdown screenshots",
            "Fee disclosure documentation",
            "Checkout flow walkthrough",
        ],
        "controls": ["has_consumer_terms"],
        "deadline_frequency": "Continuous — per purchase",
        "penalties_summary": "Fines up to ARS 2,000,000. Binding offer at advertised price if not disclosed.",
        "ai_explanation": (
            "Argentina's consumer law treats advertised prices as binding offers. If service fees are "
            "only shown at the final checkout step, the consumer can claim the original price as binding. "
            "All fees must be shown from the first price display."
        ),
        "recommended_action": (
            "Show total price (base + service fee + taxes) from event listing page. "
            "Add a fee breakdown tooltip on the checkout summary."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "data_privacy",
        "title": "Aviso de Privacidad y Política de Datos Personales",
        "description": (
            "Ticketing platforms must maintain a compliant Privacy Policy accessible from the homepage. "
            "The policy must describe: data controller identity, types of personal data collected, "
            "purposes of processing, data retention periods, third-party sharing, consumer rights "
            "(access, rectification, deletion, objection), and how to exercise those rights."
        ),
        "legal_basis": "Ley 25.326 (LPDP); Disposición AAIP 1/2018",
        "owner_role": "Legal / DPO",
        "risk_level": "HIGH",
        "required_evidence": [
            "Privacy policy document",
            "Homepage link to privacy policy",
            "AAIP registration certificate",
        ],
        "controls": ["has_privacy_policy", "has_aaip_registration"],
        "deadline_frequency": "Continuous — updated when processing changes",
        "penalties_summary": "Fines up to ARS 3,000,000. AAIP can order data processing suspension.",
        "ai_explanation": (
            "Law 25.326 requires a privacy notice before data collection. For ticketing platforms, "
            "personal data includes name, email, payment data, purchase history, and behavioral data. "
            "Each category requires separate disclosure."
        ),
        "recommended_action": (
            "Publish Spanish-language privacy policy on homepage footer. "
            "Register as data controller with AAIP at www.argentina.gob.ar/aaip. "
            "Add privacy policy link to checkout acceptance checkbox."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "data_privacy",
        "title": "Registro de Base de Datos ante AAIP",
        "description": (
            "Any person or organization that maintains a personal data database in Argentina must "
            "register the database with the AAIP (Agencia de Acceso a la Información Pública). "
            "Ticketing platforms maintain at minimum: customer database, purchase history database, "
            "and marketing contact database — each requires separate registration."
        ),
        "legal_basis": "Ley 25.326 Art. 21; Disposición AAIP 1/2018",
        "owner_role": "Legal / DPO",
        "risk_level": "HIGH",
        "required_evidence": [
            "AAIP database registration certificate(s)",
            "Database inventory listing each registered database",
        ],
        "controls": ["has_aaip_registration"],
        "deadline_frequency": "Annual renewal — prior to processing",
        "penalties_summary": "Operating unregistered databases is a regulatory violation. Fines up to ARS 3,000,000.",
        "ai_explanation": (
            "AAIP database registration is mandatory and frequently overlooked by digital platforms. "
            "The registration must describe the database name, purpose, data categories, retention period, "
            "and security measures. Failure to register does not stop operations but creates enforcement liability."
        ),
        "recommended_action": (
            "Complete AAIP online registration at www.argentina.gob.ar/aaip/registro-de-bases-de-datos. "
            "Register at minimum: 'Base de Clientes', 'Historial de Compras', 'Contactos de Marketing'. "
            "Set calendar reminder for annual renewal."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "marketing_comms",
        "title": "Consentimiento de Marketing Separado",
        "description": (
            "Marketing communications consent must be collected separately from the purchase T&C acceptance. "
            "A pre-checked checkbox for marketing consent is not valid. "
            "Consumers must be able to unsubscribe from marketing at any time. "
            "Consent must be documented with timestamp and mechanism."
        ),
        "legal_basis": "Ley 25.326 Art. 27 (spam); Ley 26.951 (No Llame); Res. AAIP",
        "owner_role": "Marketing / Legal",
        "risk_level": "MEDIUM",
        "required_evidence": [
            "Consent collection mechanism screenshot",
            "Unsubscribe mechanism documentation",
            "Consent database with timestamps",
        ],
        "controls": ["has_marketing_consent"],
        "deadline_frequency": "Continuous — per subscriber",
        "penalties_summary": "Fines up to ARS 500,000 per unsolicited message. AAIP complaints.",
        "ai_explanation": (
            "Argentina's spam law prohibits unsolicited commercial communications to consumers "
            "who have not explicitly opted in. The 'No Llame' registry and AAIP guidelines both "
            "require opt-in (not opt-out) for marketing. A bundled T&C checkbox is insufficient."
        ),
        "recommended_action": (
            "Add a separate unchecked marketing consent checkbox at registration and checkout. "
            "Label clearly: 'Deseo recibir ofertas y novedades por email.' "
            "Store consent with timestamp, IP, and mechanism for AAIP audit readiness."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "tax_invoicing",
        "title": "Facturación Electrónica (AFIP/ARCA)",
        "description": (
            "All ticket sales must generate an electronic fiscal document (factura electrónica) "
            "via AFIP/ARCA. The invoice must be issued at the time of purchase and sent to the consumer. "
            "Service fees must be separately itemized. The ticketing platform must be enrolled as "
            "a billing agent if acting as payment intermediary between consumer and promoter."
        ),
        "legal_basis": "RG AFIP 2485/2008 y modificatorias; RG AFIP 4290/2018",
        "owner_role": "Finance / Tax",
        "risk_level": "HIGH",
        "required_evidence": [
            "AFIP enrollment certificate",
            "Sample electronic invoices",
            "Invoice issuance workflow documentation",
        ],
        "controls": ["has_electronic_invoice"],
        "deadline_frequency": "Per transaction — immediate",
        "penalties_summary": "Fines up to 50% of undocumented transactions. AFIP can order closure.",
        "ai_explanation": (
            "AFIP requires electronic invoices for all commercial transactions above a minimum threshold. "
            "For ticketing platforms, the question of who is the 'seller' (platform vs. promoter) "
            "determines the invoicing structure. If the platform collects payment and remits to promoter, "
            "it may need to issue invoices as a commission agent."
        ),
        "recommended_action": (
            "Enroll in AFIP's electronic billing system. Configure automatic factura electrónica "
            "generation on purchase confirmation. Clarify fiscal structure with tax advisor "
            "(platform as agent vs. reseller)."
        ),
        "is_blocker": True,
    },
    {
        "country_code": "AR",
        "legal_area": "terms_conditions",
        "title": "Acuerdo de Cumplimiento con Promotores",
        "description": (
            "Ticketing platforms must have a formal compliance schedule in their promoter agreements "
            "that allocates regulatory obligations between the platform and the promoter. "
            "At minimum, the agreement must cover: refund obligations, cancellation protocols, "
            "permit requirements, tax responsibilities, data sharing rules, and liability allocation."
        ),
        "legal_basis": "Ley 24.240 Art. 40 (solidary liability); Código Civil y Comercial Art. 1092",
        "owner_role": "Legal / Commercial",
        "risk_level": "HIGH",
        "required_evidence": [
            "Signed promoter agreement with compliance schedule",
            "KYC verification of promoter entity",
        ],
        "controls": ["has_promoter_agreement"],
        "deadline_frequency": "Per event — before going live",
        "penalties_summary": (
            "Under Art. 40, platform and promoter are jointly liable to consumers. "
            "Without agreement, platform bears full liability."
        ),
        "ai_explanation": (
            "Argentina's consumer law establishes joint and several liability between the ticketing "
            "platform and the event promoter. Without a compliance schedule in the promoter agreement, "
            "the platform cannot allocate specific obligations (e.g., permits, refunds) to the promoter "
            "and retains full liability for all consumer claims."
        ),
        "recommended_action": (
            "Add a Compliance Schedule as an exhibit to all promoter agreements. "
            "Include: who handles refund processing, cancellation protocol timeline, "
            "permit responsibility, and indemnification for consumer claims."
        ),
        "is_blocker": True,
    },
    {
        "country_code": "AR",
        "legal_area": "public_events_permits",
        "title": "Protocolo de Cancelación y Postergación de Evento",
        "description": (
            "Ticketing platforms must have a documented cancellation and postponement protocol. "
            "For CABA events, Ley 5174 and the Ministerio de Espacio Público require advance notice. "
            "Consumers must be notified within 24 hours of cancellation. "
            "Refund processing must begin within 24 hours of cancellation announcement."
        ),
        "legal_basis": "Ley 24.240; CABA Ley 5174; Decreto GCBA 1182/2018",
        "owner_role": "Operations / Legal",
        "risk_level": "MEDIUM",
        "required_evidence": [
            "Cancellation protocol document",
            "Postponement notification template",
            "Consumer notification proof (email/SMS)",
        ],
        "controls": ["has_cancellation_clause", "has_postponement_clause"],
        "deadline_frequency": "Event-driven — within 24h of cancellation",
        "penalties_summary": "COPREC complaints. Mandatory full refund plus interest for delays.",
        "ai_explanation": (
            "COVID-19 generated significant litigation over event cancellations in Argentina. "
            "Platforms without a clear protocol faced COPREC complaints and mandatory refunds. "
            "A documented protocol protects the platform and provides a consumer-facing process."
        ),
        "recommended_action": (
            "Create a cancellation/postponement SOP with: trigger criteria, consumer notification template, "
            "refund automation, and promoter notification chain. Test the flow before first live event."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "payments_psp",
        "title": "Documentación de Contracargos (Chargebacks)",
        "description": (
            "Ticketing platforms must maintain a chargeback evidence package for each transaction. "
            "Evidence must include: purchase confirmation, delivery confirmation, T&C acceptance, "
            "IP address and device fingerprint, consumer communications, and refund policy acknowledgment. "
            "Evidence must be retained for 5 years (AFIP requirement)."
        ),
        "legal_basis": "BCRA Com. A 7283; Ley 25.065 (Tarjetas); AFIP retention requirements",
        "owner_role": "Finance / Operations",
        "risk_level": "HIGH",
        "required_evidence": [
            "Chargeback evidence pack template",
            "Transaction log with IP and device data",
            "Consumer communications archive",
        ],
        "controls": ["has_chargeback_evidence"],
        "deadline_frequency": "Per transaction — retained 5 years",
        "penalties_summary": "Lost chargebacks = full transaction amount + fees. High chargeback rates trigger PSP review.",
        "ai_explanation": (
            "Ticketing is one of the highest chargeback rate sectors in digital commerce. "
            "Event cancellations, consumer regret, and fraud all generate disputes. "
            "A pre-assembled evidence pack dramatically improves dispute win rates."
        ),
        "recommended_action": (
            "Automate evidence package assembly at purchase: save T&C acceptance log, "
            "IP address, device fingerprint, purchase timestamp, ticket delivery confirmation, "
            "and all consumer communications. Implement 90-day alert for unresolved chargebacks."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "ticket_resale",
        "title": "Política de Reventa y Control de Scalping",
        "description": (
            "CABA Law 5174 prohibits the commercial resale of tickets to mass events at prices "
            "above face value. Ticketing platforms enabling secondary market sales must: "
            "cap resale prices at face value + 20%, verify seller identity, "
            "and maintain transaction logs for 2 years. Open resale marketplaces are high-risk."
        ),
        "legal_basis": "CABA Ley 5174 (2014); Ley 24.240 (unfair commercial practices)",
        "owner_role": "Legal / Product",
        "risk_level": "HIGH",
        "required_evidence": [
            "Resale policy document",
            "Price cap mechanism documentation",
            "Seller identity verification records",
        ],
        "controls": ["has_resale_policy", "has_anti_bot_protection"],
        "deadline_frequency": "Continuous — per resale transaction",
        "penalties_summary": (
            "CABA Ley 5174: fines for buyers and sellers. Platform liability as facilitator. "
            "Consumer protection complaints."
        ),
        "ai_explanation": (
            "CABA Law 5174 was enacted specifically to address ticket scalping at large events. "
            "While enforcement has been inconsistent, the risk is reputational and financial. "
            "Platforms offering open resale marketplaces are exposed as facilitators. "
            "Controlled transfer (identity-linked, price-capped) is the compliant approach."
        ),
        "recommended_action": (
            "Choose between: (a) disabled resale (safest), (b) controlled transfer with identity verification "
            "and price cap, or (c) authorized exchange with platform oversight. "
            "Document the policy and enforce it technically."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "ecommerce",
        "title": "Protección Anti-Bot y Límites de Compra",
        "description": (
            "To prevent bulk automated purchases (bots) and artificial ticket scarcity, "
            "platforms should implement: CAPTCHA on checkout, purchase quantity limits per user, "
            "rate limiting, device fingerprinting, and velocity rules. "
            "These controls also protect against account takeover fraud."
        ),
        "legal_basis": "Ley 24.240 (unfair commercial practices); CABA Ley 5174",
        "owner_role": "Engineering / Security",
        "risk_level": "MEDIUM",
        "required_evidence": [
            "Anti-bot technical controls documentation",
            "Purchase limit configuration",
            "Bot incident logs (if any)",
        ],
        "controls": ["has_anti_bot_protection"],
        "deadline_frequency": "Continuous — technical control",
        "penalties_summary": "Regulatory risk from enabling unfair commercial practices. PSP fraud flags.",
        "ai_explanation": (
            "Bot-driven ticket purchases create artificial scarcity and effectively enable price gouging. "
            "Argentine consumer law prohibits unfair commercial practices that harm consumer interests. "
            "Anti-bot controls are both a compliance requirement and a commercial necessity."
        ),
        "recommended_action": (
            "Implement CAPTCHA (reCAPTCHA v3 or hCaptcha), set max 6 tickets per purchase, "
            "add rate limiting at 3 purchase attempts per 10 minutes, "
            "and monitor for velocity anomalies."
        ),
        "is_blocker": False,
    },
    {
        "country_code": "AR",
        "legal_area": "complaint_handling",
        "title": "Canal de Reclamos y Atención al Consumidor",
        "description": (
            "Ticketing platforms must provide a consumer complaint channel that is visible and accessible. "
            "The channel must be able to receive and respond to complaints within 15 business days. "
            "Platforms must log all complaints and their resolution. "
            "COPREC (online consumer protection platform) complaints require response within 10 days."
        ),
        "legal_basis": "Ley 24.240 Art. 45; Ley 26.993 (COPREC); Res. SCI 14/2020",
        "owner_role": "Customer Service / Legal",
        "risk_level": "MEDIUM",
        "required_evidence": [
            "Complaint channel URL/form",
            "Response SLA policy",
            "Complaint log with resolution records",
        ],
        "controls": ["has_consumer_terms"],
        "deadline_frequency": "Continuous — 15 days per complaint",
        "penalties_summary": "COPREC unresolved complaints escalate to SICE. Fines up to ARS 1,000,000.",
        "ai_explanation": (
            "COPREC (consumidor.gob.ar) is Argentina's national consumer complaint platform. "
            "All registered businesses must respond to COPREC complaints within 10 business days. "
            "Unresponded complaints are automatically escalated to SICE (enforcement). "
            "A dedicated customer service channel reduces formal complaint rates."
        ),
        "recommended_action": (
            "Create a dedicated complaint/support form. Register on consumidor.gob.ar. "
            "Assign a dedicated agent to COPREC complaint monitoring with 48h escalation SLA."
        ),
        "is_blocker": False,
    },
]


# ═══════════════════════════════════════════════════════════════════
# CONTROLS LIBRARY
# ═══════════════════════════════════════════════════════════════════

CONTROLS_LIBRARY: list[dict[str, Any]] = [
    {
        "control_code": "TCK-C01",
        "name": "Price Transparency Before Checkout",
        "description": "Display total price including all fees and taxes from the first price display.",
        "category": "ecommerce",
        "risk_dimensions": ["consumer_risk", "tax_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Show base price + service fee + taxes on event listing page. Add fee breakdown tooltip on checkout.",
        "evidence_required": ["Price breakdown screenshot", "Checkout flow documentation"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C02",
        "name": "Service Fee Disclosure",
        "description": "Clearly disclose service fees before the final checkout step.",
        "category": "ecommerce",
        "risk_dimensions": ["consumer_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Add 'Service fee: X%' line item to checkout summary page.",
        "evidence_required": ["Checkout screenshot", "Fee disclosure policy"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C03",
        "name": "Taxes Shown Separately",
        "description": "Show applicable taxes (VAT/IVA) as a separate line item in checkout.",
        "category": "tax_invoicing",
        "risk_dimensions": ["tax_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Separate line for IVA/VAT in checkout summary. Match tax rate to event country.",
        "evidence_required": ["Tax breakdown in checkout", "Tax configuration documentation"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C04",
        "name": "Refund Policy Visible Before Purchase",
        "description": "Display refund policy summary on event page and checkout, with full policy linked.",
        "category": "refunds_cancellations",
        "risk_dimensions": ["consumer_risk", "refund_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Add collapsible 'Política de Reembolso' section to event page and checkout.",
        "evidence_required": ["Refund policy document", "Checkout screenshot showing policy link"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C05",
        "name": "Event Cancellation Workflow",
        "description": "Documented process for handling event cancellations with consumer notifications and refunds.",
        "category": "refunds_cancellations",
        "risk_dimensions": ["refund_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Create SOP: trigger → notify consumers within 24h → initiate refunds → update event status.",
        "evidence_required": ["Cancellation SOP document", "Consumer notification template"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C06",
        "name": "Event Postponement Workflow",
        "description": "Process for postponements including consumer option to retain ticket or request refund.",
        "category": "refunds_cancellations",
        "risk_dimensions": ["refund_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Create SOP: notify consumers with new date + opt-out refund option within 72h.",
        "evidence_required": ["Postponement SOP", "Consumer communication template"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C07",
        "name": "Botón de Arrepentimiento / Purchase Withdrawal",
        "description": "Visible purchase withdrawal button on homepage and post-purchase confirmation.",
        "category": "consumer_protection",
        "risk_dimensions": ["consumer_risk"],
        "applies_to_countries": ["AR"],
        "implementation_guide": (
            "Add visible 'Arrepentimiento de Compra' button to: homepage header, "
            "post-purchase email, and account purchases page. "
            "Link to self-service revocation form. Process refund within 10 business days."
        ),
        "evidence_required": [
            "Homepage screenshot with button visible",
            "Revocation form/flow documentation",
            "Refund processing workflow",
        ],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C08",
        "name": "Complaint Handling Workflow",
        "description": "Dedicated consumer complaint channel with documented SLA and escalation path.",
        "category": "complaint_handling",
        "risk_dimensions": ["consumer_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Create complaint form, assign SLA (15 business days), monitor COPREC (AR).",
        "evidence_required": ["Complaint channel URL", "SLA policy", "Complaint log"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C09",
        "name": "Chargeback Evidence Pack",
        "description": "Pre-assembled transaction evidence package for chargeback disputes.",
        "category": "payments_psp",
        "risk_dimensions": ["payment_risk", "fraud_aml_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Automatically capture: T&C acceptance log, IP, device, purchase timestamp, delivery confirmation.",
        "evidence_required": ["Evidence pack template", "Transaction log sample"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C10",
        "name": "Promoter Settlement Reconciliation",
        "description": "Documented settlement process between platform and promoter with compliance schedule.",
        "category": "terms_conditions",
        "risk_dimensions": ["contractual_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Include compliance schedule in all promoter agreements. Document settlement timeline.",
        "evidence_required": ["Signed promoter agreement", "Settlement process documentation"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C11",
        "name": "Anti-Bot and Bulk Purchase Controls",
        "description": "Technical controls to prevent automated bulk purchases and ticket scalping.",
        "category": "ecommerce",
        "risk_dimensions": ["fraud_aml_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Implement CAPTCHA, max 6 tickets/purchase, rate limiting, velocity rules.",
        "evidence_required": ["Anti-bot configuration documentation", "Rate limit settings"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C12",
        "name": "Controlled Ticket Transfer",
        "description": "Identity-linked ticket transfer with audit trail. No open anonymous resale.",
        "category": "ticket_resale",
        "risk_dimensions": ["resale_risk", "fraud_aml_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Allow transfer only to verified identities. Log all transfers. Limit to 1 transfer per ticket.",
        "evidence_required": ["Transfer policy", "Identity verification records"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C13",
        "name": "Resale Disabled / Capped / Authorized Only",
        "description": "Resale policy selection: disabled, capped at face value, or authorized exchange only.",
        "category": "ticket_resale",
        "risk_dimensions": ["resale_risk"],
        "applies_to_countries": ["AR"],
        "implementation_guide": "Select resale policy and enforce technically. Document policy in T&C.",
        "evidence_required": ["Resale policy document", "Technical enforcement documentation"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C14",
        "name": "KYC Trigger for High-Value Resale",
        "description": "Trigger KYC verification for resale above threshold or suspicious transfer patterns.",
        "category": "ticket_resale",
        "risk_dimensions": ["fraud_aml_risk", "resale_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Set KYC trigger at USD 1,000 resale value or 5+ tickets transferred to single buyer.",
        "evidence_required": ["KYC trigger configuration", "Verification records"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C15",
        "name": "Marketing Opt-In Separated from Purchase Consent",
        "description": "Marketing consent collected via separate unchecked checkbox, not bundled with T&C.",
        "category": "marketing_comms",
        "risk_dimensions": ["data_privacy_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Add separate marketing checkbox at registration and checkout. Store consent with timestamp.",
        "evidence_required": ["Consent mechanism screenshot", "Consent database sample"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C16",
        "name": "Privacy Policy by Country",
        "description": "Privacy policy published in Spanish covering LPDP (AR) / LGPD (BR) requirements.",
        "category": "data_privacy",
        "risk_dimensions": ["data_privacy_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Publish country-specific privacy policies. Link from homepage footer and checkout.",
        "evidence_required": ["Privacy policy document", "Homepage link screenshot"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C17",
        "name": "Data Subject Rights Workflow",
        "description": "Process for handling data subject requests (access, rectification, deletion).",
        "category": "data_privacy",
        "risk_dimensions": ["data_privacy_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Create DSR form with 30-day SLA. Document verification and response process.",
        "evidence_required": ["DSR form/process", "Response templates"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C18",
        "name": "Vendor DPA Tracking",
        "description": "Data Processing Agreements with all third-party vendors who process consumer data.",
        "category": "data_privacy",
        "risk_dimensions": ["data_privacy_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Inventory all vendors processing personal data. Execute DPAs. Review annually.",
        "evidence_required": ["Vendor DPA inventory", "Signed DPAs"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C19",
        "name": "PCI/Payment Processor Documentation",
        "description": "Maintain PSP agreement, PCI-DSS scope documentation, and payment security controls.",
        "category": "payments_psp",
        "risk_dimensions": ["payment_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Execute PSP agreement. Complete PCI-DSS SAQ (if applicable). Document scope.",
        "evidence_required": ["PSP agreement", "PCI-DSS SAQ or attestation"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C20",
        "name": "Electronic Invoice / Receipt Issuance",
        "description": "Generate and deliver electronic fiscal document for all ticket sales.",
        "category": "tax_invoicing",
        "risk_dimensions": ["tax_risk"],
        "applies_to_countries": ["AR", "BR", "MX", "CO", "CL", "PE", "UY"],
        "implementation_guide": "Integrate with AFIP (AR), Receita Federal (BR), or SAT (MX) e-invoicing API.",
        "evidence_required": ["E-invoice integration documentation", "Sample invoice"],
        "is_mandatory": True,
    },
    {
        "control_code": "TCK-C21",
        "name": "Promoter Permit Checklist",
        "description": "Verify promoter has obtained all required event permits before ticket sales open.",
        "category": "public_events_permits",
        "risk_dimensions": ["contractual_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Create pre-launch checklist: municipal permit, venue authorization, fire safety, security plan.",
        "evidence_required": ["Permit checklist", "Copies of permits"],
        "is_mandatory": False,
    },
    {
        "control_code": "TCK-C22",
        "name": "Venue Authorization Checklist",
        "description": "Verify venue has all required authorizations: capacity, safety, accessibility.",
        "category": "public_events_permits",
        "risk_dimensions": ["contractual_risk", "operational_risk"],
        "applies_to_countries": [],
        "implementation_guide": "Checklist: capacity certificate, fire safety, emergency exits, accessibility, insurance.",
        "evidence_required": ["Venue authorization documents", "Safety certificate"],
        "is_mandatory": False,
    },
]
