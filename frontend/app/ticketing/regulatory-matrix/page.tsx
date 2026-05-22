'use client'

import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

const CATEGORIES = [
  { value: '',                      label: 'All Categories' },
  { value: 'consumer_protection',   label: 'Consumer Protection' },
  { value: 'ecommerce',             label: 'E-commerce Disclosures' },
  { value: 'refunds_cancellations', label: 'Refunds & Cancellations' },
  { value: 'ticket_resale',         label: 'Ticket Resale' },
  { value: 'data_privacy',          label: 'Data Privacy' },
  { value: 'payments_psp',          label: 'Payments / PSP' },
  { value: 'tax_invoicing',         label: 'Tax & E-invoicing' },
  { value: 'marketing_comms',       label: 'Marketing' },
  { value: 'public_events_permits', label: 'Permits' },
  { value: 'terms_conditions',      label: 'Terms & Conditions' },
  { value: 'complaint_handling',    label: 'Complaint Handling' },
  { value: 'evidence_retention',    label: 'Evidence Retention' },
]

const COUNTRIES = ['', 'AR', 'BR', 'MX', 'CO', 'CL', 'PE', 'UY', 'PY']
const RISK_LEVELS = ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

const RISK_COLORS: Record<string, string> = {
  LOW:      'bg-green-950 text-green-300 border-green-900',
  MEDIUM:   'bg-yellow-950 text-yellow-300 border-yellow-900',
  HIGH:     'bg-orange-950 text-orange-300 border-orange-900',
  CRITICAL: 'bg-red-950 text-red-300 border-red-900',
}

const STATUS_COLORS: Record<string, string> = {
  not_started: 'text-red-400',
  in_progress: 'text-yellow-400',
  implemented: 'text-green-400',
  verified:    'text-blue-400',
  not_applicable: 'text-zinc-500',
}

// Mock data for when backend is unavailable
const MOCK_OBLIGATIONS = [
  {
    id: '1',
    country_code: 'AR',
    legal_area: 'consumer_protection',
    title: 'Botón de Arrepentimiento / Derecho de Retracto Online',
    description: 'All e-commerce platforms must display a visible Botón de Arrepentimiento. Consumers have 10 days to revoke a purchase without penalty.',
    legal_basis: 'Ley 24.240 Art. 34; Resolución 424/2020',
    owner_role: 'Legal / Product',
    risk_level: 'CRITICAL',
    implementation_status: 'not_started',
    required_evidence: ['Screenshot of botón visible on homepage', 'Refund processing workflow'],
    controls: ['has_withdrawal_button', 'has_refund_policy'],
    deadline_frequency: 'Continuous',
    penalties_summary: 'Fines up to ARS 5,000,000 per violation.',
    recommended_action: 'Add visible Botón de Arrepentimiento to homepage header and post-purchase confirmation.',
    is_blocker: true,
  },
  {
    id: '2',
    country_code: 'AR',
    legal_area: 'refunds_cancellations',
    title: 'Política de Reembolso y Cancelación de Evento',
    description: 'Ticketing platforms must maintain a clear refund and cancellation policy accessible before purchase.',
    legal_basis: 'Ley 24.240 Arts. 10, 19, 34',
    owner_role: 'Legal / Operations',
    risk_level: 'HIGH',
    implementation_status: 'in_progress',
    required_evidence: ['Refund policy document', 'Consumer communication templates'],
    controls: ['has_refund_policy'],
    deadline_frequency: 'Continuous',
    penalties_summary: 'Fines up to ARS 1,000,000.',
    recommended_action: 'Display refund policy on event page, checkout, and confirmation email.',
    is_blocker: true,
  },
  {
    id: '3',
    country_code: 'AR',
    legal_area: 'data_privacy',
    title: 'Registro de Base de Datos ante AAIP',
    description: 'All organizations maintaining personal data databases in Argentina must register with AAIP.',
    legal_basis: 'Ley 25.326 Art. 21; Disposición AAIP 1/2018',
    owner_role: 'Legal / DPO',
    risk_level: 'HIGH',
    implementation_status: 'not_started',
    required_evidence: ['AAIP registration certificate', 'Database inventory'],
    controls: ['has_aaip_registration'],
    deadline_frequency: 'Annual renewal',
    penalties_summary: 'Fines up to ARS 3,000,000.',
    recommended_action: 'Register databases at argentina.gob.ar/aaip.',
    is_blocker: false,
  },
  {
    id: '4',
    country_code: 'AR',
    legal_area: 'tax_invoicing',
    title: 'Facturación Electrónica (AFIP/ARCA)',
    description: 'All ticket sales must generate an electronic fiscal document via AFIP/ARCA at time of purchase.',
    legal_basis: 'RG AFIP 2485/2008 y modificatorias',
    owner_role: 'Finance / Tax',
    risk_level: 'HIGH',
    implementation_status: 'not_started',
    required_evidence: ['AFIP enrollment certificate', 'Sample electronic invoices'],
    controls: ['has_electronic_invoice'],
    deadline_frequency: 'Per transaction',
    penalties_summary: 'Fines up to 50% of undocumented transactions.',
    recommended_action: 'Enroll in AFIP electronic billing and configure automatic invoice generation.',
    is_blocker: true,
  },
  {
    id: '5',
    country_code: 'AR',
    legal_area: 'ticket_resale',
    title: 'Política de Reventa y Control de Scalping',
    description: 'CABA Law 5174 prohibits commercial resale above face value. Platforms must cap at face value +20%.',
    legal_basis: 'CABA Ley 5174 (2014)',
    owner_role: 'Legal / Product',
    risk_level: 'HIGH',
    implementation_status: 'not_started',
    required_evidence: ['Resale policy document', 'Price cap documentation'],
    controls: ['has_resale_policy'],
    deadline_frequency: 'Continuous',
    penalties_summary: 'Platform liability as facilitator.',
    recommended_action: 'Implement identity-linked transfers with price caps.',
    is_blocker: false,
  },
  {
    id: '6',
    country_code: 'BR',
    legal_area: 'consumer_protection',
    title: 'Direito de Arrependimento (CDC Art. 49)',
    description: 'Brazilian Consumer Defense Code grants 7 days for remote purchase cancellation with full refund.',
    legal_basis: 'CDC Art. 49; Lei 8.078/90',
    owner_role: 'Legal / Operations',
    risk_level: 'HIGH',
    implementation_status: 'not_started',
    required_evidence: ['Cancellation mechanism documentation', 'Refund SLA policy'],
    controls: ['has_refund_policy', 'has_cancellation_clause'],
    deadline_frequency: 'Continuous',
    penalties_summary: 'PROCON fines. Mandatory full refund.',
    recommended_action: 'Implement 7-day cancellation flow with automatic refund.',
    is_blocker: true,
  },
  {
    id: '7',
    country_code: 'MX',
    legal_area: 'tax_invoicing',
    title: 'Comprobante Fiscal Digital por Internet (CFDI)',
    description: 'All commercial transactions require CFDI electronic invoice issued via SAT.',
    legal_basis: 'CFF Art. 29; LFDE; SAT RMF',
    owner_role: 'Finance / Tax',
    risk_level: 'HIGH',
    implementation_status: 'not_started',
    required_evidence: ['SAT enrollment', 'CFDI sample'],
    controls: ['has_electronic_invoice'],
    deadline_frequency: 'Per transaction',
    penalties_summary: 'SAT fines up to MXN 87,000 per unissued invoice.',
    recommended_action: 'Integrate SAT-authorized PAC for CFDI generation.',
    is_blocker: true,
  },
]

export default function RegulatoryMatrix() {
  const [obligations, setObligations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [country, setCountry] = useState('')
  const [category, setCategory] = useState('')
  const [riskLevel, setRiskLevel] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams()
    if (country) params.set('country', country)
    if (category) params.set('category', category)
    if (riskLevel) params.set('risk_level', riskLevel)

    setLoading(true)
    fetch(`${API}/api/v1/ticketing/obligations?${params}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setObligations(d.obligations ?? []))
      .catch(() => setObligations(MOCK_OBLIGATIONS))
      .finally(() => setLoading(false))
  }, [country, category, riskLevel])

  const filtered = obligations.filter(o => {
    if (country && o.country_code !== country) return false
    if (category && o.legal_area !== category) return false
    if (riskLevel && o.risk_level !== riskLevel) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Regulatory Matrix</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Ticketing compliance obligations by country and category
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={country}
          onChange={e => setCountry(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
        >
          {COUNTRIES.map(c => (
            <option key={c} value={c}>{c || 'All Countries'}</option>
          ))}
        </select>
        <select
          value={category}
          onChange={e => setCategory(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
        >
          {CATEGORIES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <select
          value={riskLevel}
          onChange={e => setRiskLevel(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
        >
          {RISK_LEVELS.map(r => (
            <option key={r} value={r}>{r || 'All Risk Levels'}</option>
          ))}
        </select>
        <div className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm text-zinc-400">
          {loading ? 'Loading…' : `${filtered.length} obligations`}
        </div>
      </div>

      {/* Table */}
      <div className="border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900">
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500 w-12">Country</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Obligation</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Category</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Risk</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Status</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-zinc-500">Blocker</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-zinc-800">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-3 bg-zinc-800 rounded animate-pulse" style={{ width: `${60 + j * 10}%` }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-zinc-500 text-sm">
                  No obligations found. Use{' '}
                  <code className="font-mono text-xs bg-zinc-800 px-1 rounded">POST /api/v1/ticketing/seed</code>
                  {' '}to load seed data.
                </td>
              </tr>
            ) : (
              filtered.map(ob => (
                <>
                  <tr
                    key={ob.id}
                    className="border-b border-zinc-800 hover:bg-zinc-900 cursor-pointer"
                    onClick={() => setExpanded(expanded === ob.id ? null : ob.id)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-zinc-300">{ob.country_code}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-zinc-100">{ob.title}</div>
                      <div className="text-xs text-zinc-500 mt-0.5">{ob.legal_basis}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-400">
                      {ob.legal_area?.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded border ${RISK_COLORS[ob.risk_level] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
                        {ob.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs ${STATUS_COLORS[ob.implementation_status] ?? 'text-zinc-500'}`}>
                        {ob.implementation_status?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {ob.is_blocker ? (
                        <span className="px-1.5 py-0.5 text-xs bg-red-950 text-red-400 border border-red-900 rounded">BLOCKER</span>
                      ) : (
                        <span className="text-xs text-zinc-600">—</span>
                      )}
                    </td>
                  </tr>
                  {expanded === ob.id && (
                    <tr key={`${ob.id}-detail`} className="border-b border-zinc-800 bg-zinc-950">
                      <td colSpan={6} className="px-6 py-5">
                        <div className="grid grid-cols-2 gap-6">
                          <div className="space-y-3">
                            <div>
                              <div className="text-xs text-zinc-500 mb-1">Description</div>
                              <p className="text-sm text-zinc-300">{ob.description}</p>
                            </div>
                            {ob.recommended_action && (
                              <div>
                                <div className="text-xs text-zinc-500 mb-1">Recommended Action</div>
                                <p className="text-sm text-zinc-300">{ob.recommended_action}</p>
                              </div>
                            )}
                            {ob.penalties_summary && (
                              <div>
                                <div className="text-xs text-zinc-500 mb-1">Penalties</div>
                                <p className="text-sm text-red-300">{ob.penalties_summary}</p>
                              </div>
                            )}
                          </div>
                          <div className="space-y-3">
                            <div>
                              <div className="text-xs text-zinc-500 mb-1">Owner</div>
                              <p className="text-sm text-zinc-300">{ob.owner_role || '—'}</p>
                            </div>
                            <div>
                              <div className="text-xs text-zinc-500 mb-1">Frequency</div>
                              <p className="text-sm text-zinc-300">{ob.deadline_frequency || '—'}</p>
                            </div>
                            {ob.required_evidence?.length > 0 && (
                              <div>
                                <div className="text-xs text-zinc-500 mb-1">Required Evidence</div>
                                <ul className="space-y-1">
                                  {ob.required_evidence.map((e: string, i: number) => (
                                    <li key={i} className="text-xs text-zinc-400 flex items-start gap-1">
                                      <span className="text-zinc-600 mt-0.5">•</span>{e}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
