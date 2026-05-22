'use client'

import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

type Control = {
  id: string
  code: string
  name: string
  description: string
  category: string
  is_hard_blocker: boolean
  applies_to_countries: string[] | null
  implementation_notes: string
  evidence_required: string[]
  estimated_effort: string
}

const MOCK_CONTROLS: Control[] = [
  {
    id: '1', code: 'TCK-C01', name: 'Promoter Compliance Agreement',
    description: 'Signed legal agreement allocating compliance liability between the ticketing platform and the event promoter.',
    category: 'contractual', is_hard_blocker: true, applies_to_countries: null,
    implementation_notes: 'Must be signed before event goes live. Template available in Documents section.',
    evidence_required: ['Signed PDF', 'DocuSign audit trail'],
    estimated_effort: '1-2 days',
  },
  {
    id: '2', code: 'TCK-C02', name: 'Refund & Cancellation Policy',
    description: 'Publicly posted policy covering cancellation, postponement, and force majeure refund obligations.',
    category: 'consumer_protection', is_hard_blocker: true, applies_to_countries: null,
    implementation_notes: 'Must be visible at checkout and in confirmation email. Min 10-day SLA for Argentina.',
    evidence_required: ['URL of live policy page', 'Screenshot of checkout display'],
    estimated_effort: '2-3 hours',
  },
  {
    id: '3', code: 'TCK-C03', name: 'Consumer Terms & Conditions',
    description: 'Terms governing ticket purchase, including transfer restrictions and liability cap.',
    category: 'consumer_protection', is_hard_blocker: true, applies_to_countries: null,
    implementation_notes: 'Require explicit checkbox consent at checkout.',
    evidence_required: ['URL of T&C page', 'Consent flow screenshot'],
    estimated_effort: '1 day',
  },
  {
    id: '4', code: 'TCK-C04', name: 'Payment Processor Record',
    description: 'Documented payment processor with PCI-DSS compliance evidence.',
    category: 'payments', is_hard_blocker: true, applies_to_countries: null,
    implementation_notes: 'Maintain processor agreement and PCI-DSS certificate on file.',
    evidence_required: ['Processor agreement', 'PCI-DSS certificate'],
    estimated_effort: '1 week',
  },
  {
    id: '5', code: 'TCK-C05', name: 'Privacy Policy',
    description: 'LGPD/PDPA-compatible privacy policy with data retention clauses and third-party sharing disclosure.',
    category: 'data_privacy', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Update annually or when data practices change.',
    evidence_required: ['URL of live privacy page'],
    estimated_effort: '2-3 hours',
  },
  {
    id: '6', code: 'TCK-C06', name: 'Botón de Arrepentimiento',
    description: 'Purchase withdrawal button mandatory in Argentina under Res. 424/2020 (10-day withdrawal right).',
    category: 'consumer_protection', is_hard_blocker: true, applies_to_countries: ['AR'],
    implementation_notes: 'Must be visible on homepage AND post-purchase confirmation page. Must process refund within 10 days.',
    evidence_required: ['Screenshot of button on site', 'Refund workflow documentation'],
    estimated_effort: '2-3 days',
  },
  {
    id: '7', code: 'TCK-C07', name: 'Cancellation Clause',
    description: 'Explicit cancellation rights for consumers including refund timeline.',
    category: 'consumer_protection', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Include in T&C and refund policy.',
    evidence_required: ['Section in T&C document'],
    estimated_effort: '1 hour',
  },
  {
    id: '8', code: 'TCK-C08', name: 'Postponement Clause',
    description: 'Consumer rights on event postponement, including refund trigger conditions.',
    category: 'consumer_protection', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Specify maximum postponement period before automatic refund triggers.',
    evidence_required: ['Section in T&C or refund policy'],
    estimated_effort: '1 hour',
  },
  {
    id: '9', code: 'TCK-C09', name: 'Marketing Consent',
    description: 'Explicit double opt-in consent for marketing communications. Separate from T&C consent.',
    category: 'data_privacy', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Use separate checkbox from T&C acceptance.',
    evidence_required: ['Consent mechanism screenshot', 'Consent database schema'],
    estimated_effort: '4 hours',
  },
  {
    id: '10', code: 'TCK-C10', name: 'Anti-Bot / Bulk Purchase Protection',
    description: 'CAPTCHA and purchase rate limiting to prevent scalping bots.',
    category: 'resale', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Limit to 4-6 tickets per transaction. Implement CAPTCHA on checkout.',
    evidence_required: ['Technical spec or vendor contract'],
    estimated_effort: '1-2 weeks',
  },
  {
    id: '11', code: 'TCK-C11', name: 'Electronic Invoice Setup',
    description: 'AFIP-compliant electronic invoice (factura electrónica) per Res. 1415/2003.',
    category: 'tax', is_hard_blocker: false, applies_to_countries: ['AR'],
    implementation_notes: 'Each ticket sale must trigger an electronic invoice. CUIT required.',
    evidence_required: ['AFIP certificate', 'Sample invoice'],
    estimated_effort: '3-5 days',
  },
  {
    id: '12', code: 'TCK-C12', name: 'AAIP Database Registration',
    description: 'Registration as data controller with Argentina AAIP (Agencia de Acceso a la Información Pública).',
    category: 'data_privacy', is_hard_blocker: false, applies_to_countries: ['AR'],
    implementation_notes: 'Register at argentina.gob.ar/aaip. Free registration, takes 1-2 weeks.',
    evidence_required: ['AAIP registration certificate'],
    estimated_effort: '2 hours + 1-2 week processing',
  },
  {
    id: '13', code: 'TCK-C13', name: 'Venue Authorization',
    description: 'Written authorization from venue owner or operator for the event.',
    category: 'permits', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Must be in place before ticket sales open.',
    evidence_required: ['Signed venue contract or letter of authorization'],
    estimated_effort: 'Varies',
  },
  {
    id: '14', code: 'TCK-C14', name: 'Event / Public Safety Permit',
    description: 'Municipal event permit or public assembly approval from local authority.',
    category: 'permits', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Requirements vary by municipality. File 30-60 days in advance.',
    evidence_required: ['Permit document from municipality'],
    estimated_effort: '2-6 weeks processing',
  },
  {
    id: '15', code: 'TCK-C15', name: 'Chargeback Evidence Pack',
    description: 'Pre-packaged evidence for dispute resolution: T&C acceptance, delivery proof, communication history.',
    category: 'payments', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Automate evidence collection at time of purchase. Store for 24 months.',
    evidence_required: ['Evidence pack template', 'Sample dispute response'],
    estimated_effort: '3-5 days',
  },
  {
    id: '16', code: 'TCK-C16', name: 'Resale Policy & Price Cap',
    description: 'Defined resale policy with maximum resale price cap (e.g., 130% of face value).',
    category: 'resale', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Required if resale marketplace is enabled.',
    evidence_required: ['Published resale policy', 'Technical price cap implementation'],
    estimated_effort: '1 week',
  },
  {
    id: '17', code: 'TCK-C17', name: 'AML/KYC Controls for Crypto',
    description: 'Know Your Customer and Anti-Money Laundering controls for cryptocurrency payment acceptance.',
    category: 'payments', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Required if crypto payments are enabled. UIF reporting for AR.',
    evidence_required: ['KYC provider contract', 'AML policy document'],
    estimated_effort: '2-4 weeks',
  },
  {
    id: '18', code: 'TCK-C18', name: 'Complaint Handling SLA',
    description: 'Documented complaint handling process with response SLA (e.g., 15 business days).',
    category: 'consumer_protection', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Argentina requires max 15 business day response per Ley 24.240.',
    evidence_required: ['Complaint procedure document', 'Helpdesk ticket system evidence'],
    estimated_effort: '2-3 days',
  },
  {
    id: '19', code: 'TCK-C19', name: 'Price Transparency & Fee Disclosure',
    description: 'Upfront disclosure of all fees (service charges, booking fees) before checkout.',
    category: 'consumer_protection', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Display total price including all fees on event listing page.',
    evidence_required: ['Screenshot of pricing display', 'Fee breakdown in T&C'],
    estimated_effort: '1 day',
  },
  {
    id: '20', code: 'TCK-C20', name: 'Brazil LGPD Data Mapping',
    description: 'Data processing activities mapped and documented per Brazilian LGPD requirements.',
    category: 'data_privacy', is_hard_blocker: false, applies_to_countries: ['BR'],
    implementation_notes: 'Appoint DPO. Maintain ROPA (Record of Processing Activities).',
    evidence_required: ['ROPA document', 'DPO appointment letter'],
    estimated_effort: '1-2 weeks',
  },
  {
    id: '21', code: 'TCK-C21', name: 'Force Majeure Clause',
    description: 'Force majeure clause covering epidemics, natural disasters, and government restrictions.',
    category: 'contractual', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Include in both consumer T&C and promoter agreement.',
    evidence_required: ['Clause in T&C', 'Clause in promoter agreement'],
    estimated_effort: '2 hours',
  },
  {
    id: '22', code: 'TCK-C22', name: 'Wallet / Stored Funds Safeguards',
    description: 'Consumer fund protection for wallet/stored balance products (segregation, insurance).',
    category: 'payments', is_hard_blocker: false, applies_to_countries: null,
    implementation_notes: 'Required if wallet balance feature is enabled.',
    evidence_required: ['Fund segregation policy', 'Banking arrangement documentation'],
    estimated_effort: '2-4 weeks',
  },
]

const CATEGORY_LABELS: Record<string, string> = {
  consumer_protection: 'Consumer Protection',
  data_privacy: 'Data Privacy',
  payments: 'Payments',
  tax: 'Tax & Invoicing',
  contractual: 'Contractual',
  resale: 'Resale Controls',
  permits: 'Permits & Safety',
  evidence: 'Evidence',
}

export default function ControlsLibrary() {
  const [controls, setControls] = useState<Control[]>([])
  const [loading, setLoading] = useState(true)
  const [filterCat, setFilterCat] = useState('')
  const [filterCountry, setFilterCountry] = useState('')
  const [filterBlocker, setFilterBlocker] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/ticketing/controls`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setControls(d.controls ?? MOCK_CONTROLS))
      .catch(() => setControls(MOCK_CONTROLS))
      .finally(() => setLoading(false))
  }, [])

  const filtered = controls.filter(c => {
    if (filterCat && c.category !== filterCat) return false
    if (filterCountry && c.applies_to_countries && !c.applies_to_countries.includes(filterCountry)) return false
    if (filterBlocker && !c.is_hard_blocker) return false
    return true
  })

  const categories = [...new Set(controls.map(c => c.category))]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Controls Library</h1>
        <p className="text-sm text-zinc-500 mt-1">22 compliance controls for ticketing operations across LATAM</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filterCat}
          onChange={e => setFilterCat(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
        >
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{CATEGORY_LABELS[c] ?? c}</option>)}
        </select>
        <select
          value={filterCountry}
          onChange={e => setFilterCountry(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
        >
          <option value="">All Countries</option>
          {['AR', 'BR', 'MX', 'CO', 'CL', 'PE', 'UY', 'PY'].map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="flex items-center gap-2 px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm cursor-pointer">
          <input type="checkbox" checked={filterBlocker} onChange={e => setFilterBlocker(e.target.checked)} />
          Blockers only
        </label>
        <span className="px-3 py-2 text-sm text-zinc-500">{filtered.length} control(s)</span>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-16 bg-zinc-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(ctrl => (
            <div key={ctrl.id} className="border border-zinc-800 rounded-lg overflow-hidden">
              <button
                onClick={() => setExpanded(expanded === ctrl.id ? null : ctrl.id)}
                className="w-full p-5 flex items-start justify-between gap-4 text-left hover:bg-zinc-900/50 transition-colors"
              >
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="font-mono text-xs text-zinc-500 shrink-0">{ctrl.code}</span>
                  <span className="font-medium text-sm">{ctrl.name}</span>
                  {ctrl.is_hard_blocker && (
                    <span className="px-1.5 py-0.5 bg-red-950 border border-red-900 text-red-400 text-xs rounded">
                      BLOCKER
                    </span>
                  )}
                  <span className="px-1.5 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded">
                    {CATEGORY_LABELS[ctrl.category] ?? ctrl.category}
                  </span>
                  {ctrl.applies_to_countries && (
                    <span className="text-xs text-yellow-600">
                      {ctrl.applies_to_countries.join(', ')} only
                    </span>
                  )}
                </div>
                <span className="text-zinc-600 shrink-0">{expanded === ctrl.id ? '▲' : '▼'}</span>
              </button>

              {expanded === ctrl.id && (
                <div className="border-t border-zinc-800 p-5 space-y-4 bg-zinc-900/30">
                  <p className="text-sm text-zinc-400">{ctrl.description}</p>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs font-semibold text-zinc-500 mb-1">Implementation Notes</div>
                      <p className="text-sm text-zinc-300">{ctrl.implementation_notes}</p>
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-zinc-500 mb-1">Estimated Effort</div>
                      <p className="text-sm text-zinc-300">{ctrl.estimated_effort}</p>
                    </div>
                  </div>

                  {ctrl.evidence_required.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-zinc-500 mb-2">Evidence Required</div>
                      <div className="flex flex-wrap gap-2">
                        {ctrl.evidence_required.map((e, i) => (
                          <span key={i} className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 rounded text-xs text-zinc-300">
                            {e}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
