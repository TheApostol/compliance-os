# ComplianceOS — Prompt maestro para diseño UI/UX en Figma

Prompt listo para pegar en Figma (First Draft / Figma AI) o para entregar a un diseñador/agencia. Cubre **web app** y **app instalable (PWA)** para los 10 módulos + arquitectura transversal (auth, multi-tenant, admin) relevados directamente del código de `compliance-os` (`backend/app/db/models.py`, `api/v1/router.py`, `core/auth.py`, `frontend/app/dashboard/*`).

Está escrito para copiarse tal cual. Las secciones entre `[ ]` son variables que podés ajustar (branding, idioma default, etc.).

---

## PROMPT

Diseñá el sistema de UI/UX completo de **ComplianceOS**, un sistema operativo de compliance regulatorio AI-native para industrias reguladas de LATAM (banca, PSPs, fintech, cripto). No es un dashboard de reportes: es infraestructura regulatoria — convierte regulación en obligaciones estructuradas y orquesta agentes de IA que monitorean, auditan y actúan de forma continua sobre 9 reguladores (BCRA/UIF Argentina, BACEN Brasil, SBS Perú, SFC Colombia, CMF Chile, CNBV México, BCU Uruguay, SBS Ecuador).

Generá dos entregables dentro del mismo archivo de Figma: **Web App** (desktop-first, densidad de datos alta, uso interno de compliance officers) y **App Instalable / PWA** (mobile-first, para revisión y aprobación en movimiento, notificaciones push de vencimientos).

### 1. Personalidad de marca y dirección visual

- Tono: "torre de control regulatoria" — serio, confiable, denso en datos, cero infantilismo. Referencias: Linear, Vercel Dashboard, Stripe Radar, Chainalysis Reactor.
- Modo por defecto: **dark mode** (uso 24/7 tipo SOC/NOC), con light mode disponible como toggle.
- Paleta semántica de severidad consistente en TODO el sistema (se reutiliza en riesgo KYC, alertas de vencimiento, severidad de obligación, premortem):
  - `LOW` verde, `MEDIUM` ámbar, `HIGH` naranja, `CRITICAL` rojo.
  - Un segundo eje de estado (no de severidad) para: `pending / in_review / approved / rejected / escalated`.
- Tipografía: sans-serif de alta legibilidad para tablas densas + una monoespaciada para hashes, IDs, JWT, hashes de auditoría (custody_hash, source_hash).
- Localización: ES / PT-BR / EN nativo (selector de idioma en header). Formateo de moneda y fecha por país/tenant.
- Data viz: score rings (0-100), sparklines de tendencia, heatmaps de riesgo por país/regulador, grafo interactivo (regulación → obligación → entidad → control).

### 2. Arquitectura de información / navegación global

Sidebar principal (colapsable) con estos grupos, en este orden:

1. **Overview** — cockpit ejecutivo (KPIs, feed en vivo, alertas críticas)
2. **M1 · Inteligencia Regulatoria** — regulaciones, obligaciones, crawler de 9 reguladores
3. **M2 · Compliance Copilot** — chat AI con preguntas enlatadas y expansión de recomendaciones
4. **M3 · KYC/AML** — cola de casos, screening, sanciones, generación de RoF (Report of Findings)
5. **M4 · Monitoreo Continuo** — drift detection, alertas de vencimiento, deadline checker
6. **M10 · Monitoreo Transaccional (AML)** — screening de transacciones, reglas configurables
7. **M5 · Gobernanza de IA** — registro de modelos, auditoría de decisiones AI, chequeo de prompt injection
8. **M6 · Evidencia Automatizada** — carga de documentos, extracción estructurada, cadena de custodia
9. **M7 · Predictivo** — riesgo por jurisdicción, simulación de entrada a mercado
10. **M8 · Workflows / Remediación** — DAG de aprobaciones, escalamiento, remediación
11. **M9 · Tickets** — mesa de ayuda de compliance
12. **Grafo de Compliance** — visualización regulación↔obligación↔entidad↔control
13. **Compliance Score** — score por entidad + histórico + gap analysis
14. **Auditoría** — log inmutable (hash chain), tamper-evident
15. **Entidades** — empresas/individuos/sectores regulados
16. **Premortem** — inventario de failure modes + roadmap de mitigación (ya existe una versión, usarla de referencia)
17. **Configuración** (sección aparte, abajo del sidebar):
    - Tenant / Organización (política de residencia de datos, timezone IANA)
    - Usuarios y roles
    - API Keys
    - Webhooks
    - Exportaciones (CSV obligaciones, PDF reporte de compliance, CSV evidencia)
    - Modelos de IA validados (banco de modelos NVIDIA/Anthropic/OpenRouter, con estado deprecated/approved)

Un topbar global con: selector de tenant (multi-tenant switcher), badge de rol activo (`admin | analyst | viewer`), búsqueda global (`/search`), centro de notificaciones en tiempo real (server-sent events: crawler completo, alerta de vencimiento, regulación parseada), selector de idioma, avatar/menu de usuario.

### 3. Autenticación y control de acceso (diseñar como flujo completo, no solo una pantalla)

- **Login** con email + password (JWT local HS256), con soporte visual para modo enterprise SSO (Auth0 / Clerk) — mostrar botón "Continuar con SSO de tu organización" como variante.
- **Registro** de usuario nuevo dentro de un tenant existente.
- **Recuperación de sesión**: manejo de expiración de access token (sesiones de 8h) con refresh token silencioso (7 días) — diseñar el estado de "sesión expirando" y el modal de re-login sin perder contexto.
- **Selector de tenant** post-login si el usuario pertenece a más de una organización.
- **Onboarding de tenant nuevo** (solo rol admin): crear organización, elegir política de residencia de datos (`global | latam | ar | br`), timezone.
- **Gestión de roles** con 3 niveles visualmente distintos en toda la UI (no solo en una tabla de settings): `admin` (acceso total), `analyst` (operación diaria, sin config de tenant), `viewer` (solo lectura) — cada pantalla debe tener un estado de "vista de solo lectura" cuando el rol es viewer.
- **API Keys**: pantalla de creación con scopes (`read`, `write`, `crawl`), key mostrada una sola vez, lista con prefijo visible + último uso + expiración.
- Pantalla de error 401/403 con mensaje claro de "no autenticado" vs "sin permisos para esta acción".

### 4. Pantallas por módulo (contenido mínimo que cada una debe tener)

**M1 — Inteligencia Regulatoria**
- Feed de regulaciones (país, regulador, código, título, fecha de vigencia, estado de embedding)
- Detalle de regulación → lista de obligaciones extraídas (severidad, frecuencia, deadline_rule, sectores aplicables, evidencia requerida, penalidad USD, verificado por humano sí/no)
- Estado del crawler por regulador (9 países) con última corrida, éxito/fallo, botón "correr ahora"
- Vista de mapeo obligación → entidad/sector

**M2 — Compliance Copilot**
- Interfaz de chat con streaming de respuesta, preguntas enlatadas sugeridas, citas a regulaciones fuente (RAG), botón "expandir con recomendaciones accionables"

**M3 — KYC/AML**
- Cola de casos con filtros por risk_level y status (`OPEN, UNDER_REVIEW, ESCALATED, CLOSED_NO_ACTION, REPORTED, REJECTED`)
- Detalle de caso: score de riesgo AI (ring 0-100), red flags, obligaciones disparadas, botón de screening de sanciones, generación de Report of Findings, asignación a analista, toggle "requiere revisión humana"

**M4 — Monitoreo Continuo**
- Dashboard de drift detection de modelos AI
- Centro de alertas de vencimiento (deadline) con días restantes, severidad, botón de reconocimiento (acknowledge)

**M10 — Monitoreo Transaccional**
- Tabla de transacciones (monto, moneda, canal, país, contraparte) con status `pending/cleared/flagged/blocked/reported`
- Detalle con reglas disparadas (rule_flags), análisis AI de tipología, vínculo a caso KYC
- Editor de reglas configurables (threshold, velocity, geography, structuring)

**M5 — Gobernanza de IA**
- Registro de modelos (provider, versión, casos de uso, benchmark scores, aprobado para producción sí/no, deprecated)
- Auditoría de decisiones AI + chequeo de prompt injection con resultado pass/fail

**M6 — Evidencia Automatizada**
- Zona de carga de documentos (PDF) con progreso de extracción
- Resultado estructurado + obligaciones cruzadas + confidence score
- Cadena de custodia: hash de origen, hash de custodia, timestamp — presentado como línea de tiempo verificable

**M7 — Predictivo**
- Mapa de riesgo por jurisdicción (heatmap LATAM)
- Simulador "entrada a mercado" con inputs de país/sector y output de riesgo proyectado

**M8 — Workflows / Remediación**
- Vista tipo DAG/kanban de pasos de aprobación, con estado por paso, escalamiento visual si excede el timeout

**M9 — Tickets**
- Lista + detalle con prioridad y status, similar a un helpdesk liviano

**Grafo de Compliance**
- Grafo interactivo navegable (zoom, filtro por tipo de vértice: regulation/obligation/entity/control/regulator; por tipo de arista: REQUIRES/APPLIES_TO/SATISFIES/ISSUED_BY/CROSS_REFERENCES)

**Compliance Score**
- Score por entidad con histórico (gráfico de línea temporal) y gap analysis accionable

**Auditoría**
- Log inmutable, filtrable por tipo de evento, con indicador visual de integridad de la cadena de hashes (verificado/roto)

**Entidades**
- CRUD de compañías/individuos/sectores con propiedades JSON y sectores aplicables

### 5. Estados que hay que diseñar para CADA pantalla con datos

- Loading (skeleton, no spinner genérico)
- Empty state con call-to-action
- Error (con distinción clara entre error de red, timeout de IA >180s, y error de permisos)
- Datos en vivo actualizándose (indicador sutil de "actualizado hace Xs" para las pantallas alimentadas por SSE)

### 6. Web app — requisitos responsive

- Desktop ≥1440px: sidebar expandido + tablas densas multi-columna
- Laptop 1024–1439px: sidebar colapsable a íconos
- Tablet 768–1023px: tablas → cards, sidebar en drawer

### 7. App instalable (PWA) — diseñar como app nativa, no "web achicada"

- Ícono de app, splash screen, prompt de instalación ("Agregar a inicio")
- Navegación inferior (bottom tab bar) con los 4-5 módulos de mayor uso diario: Overview, KYC, Alertas, Copilot, Perfil — el resto accesible por menú "Más"
- Modo offline: qué se cachea (alertas ya cargadas, casos asignados) vs qué requiere conexión, con banner de "sin conexión, mostrando datos cacheados"
- Notificaciones push nativas para: vencimiento de obligación crítico, caso KYC asignado, escalamiento de workflow, resultado de crawler
- Bloqueo de sesión con PIN/biométrico opcional al reabrir la app (dato sensible de compliance)
- Gestos táctiles: swipe para aprobar/rechazar en colas de aprobación (workflows, casos KYC)

### 8. Sistema de componentes a construir (Figma components + variants, no pantallas sueltas)

Botones (primary/secondary/destructive/ghost), inputs, selects con búsqueda, date/time pickers con timezone, badges de severidad y de status (variants por los 4 niveles + los 6 estados de caso), score ring, sparkline, tabla de datos con ordenamiento/filtro/paginación, tarjeta de alerta, chat bubble, timeline de custodia, grafo de nodos, tabs, modal, toast/notificación, empty state, skeleton loader, sidebar item (con badge de contador), topbar, bottom tab bar (mobile).

### 9. Entregables esperados

- Un archivo de Figma con páginas separadas: `Design Tokens`, `Components`, `Web App`, `Mobile/PWA`, `Flows` (prototipo clickeable del flujo login → overview → un caso KYC → aprobación).
- Auto-layout en todos los frames, componentes con variants (no duplicar por copy-paste).
- Prototipo interactivo mínimo: Login → selección de tenant → Overview → M3 detalle de caso → aprobación → vuelta a cola.

---

**Nota de scope**: si el generador de Figma AI trunca por tamaño, dividir el prompt en 3 pasadas: (1) Design tokens + componentes + Login/Auth + Overview, (2) Módulos M1-M6, (3) Módulos M7-M10 + Grafo + Auditoría + Configuración + versión PWA.
