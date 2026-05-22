'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp', 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

type CheckItem = {
  id: string
  control_code: string
  name: string
  description: string
  category: string
  is_blocker: boolean
  status: 'implemented' | 'partial' | 'missing' | 'not_applicable'
  evidence_url?: string
  notes?: string
  due_date?: string
}

const MOCK_CHECKLIST: CheckItem[] = [
  {
    id: '1', control_code: 'TCK-C01',
    name: 'Promoter Compliance Agreement',
    description: 'Signed agreement allocating liability between platform and promoter',
    category: 'contractual', is_blocker: true, status: 'missing',
  },
  {
    id: '2', control_code: 'TCK-C02',
    name: 'Refund & Cancellation Policy',
    description: 'Publicly posted policy covering cancellation, postponement, force majeure',
    category: 'consumer_protection', is_blocker: true, status: 'implemented',
    evidence_url: 'https://example.com/refund-policy',
  },
  {
    id: '3', control_code: 'TCK-C03',
    name: 'Consumer Terms & Conditions',
    description: 'Terms governing ticket purchase including transfer restrictions',
    category: 'consumer_protection', is_blocker: true, status: 'implemented',
  },
  {
    id: '4', control_code: 'TCK-C04',
    name: 'Payment Processor Record',
    description: 'Documented payment processor with PCI-DSS compliance evidence',
    category: 'payments', is_blocker: true, status: 'implemented',
  },
  {
    id: '5', control_code: 'TCK-C05',
    name: 'Privacy Policy',
    description: 'GDPR/LGPD-compatible privacy policy with data retention clauses',
    category: 'data_privacy', is_blocker: false, status: 'implemented',
  },
  {
    id: '6', control_code: 'TCK-C06',
    name: 'Botón de Arrepentimiento',
    description: 'Purchase withdrawal button (mandatory in Argentina, Res. 424/2020)',
    category: 'consumer_protection', is_blocker: true, status: 'missing',
  },
  {
    id: '7', control_code: 'TCK-C07',
    name: 'Cancellation Clause',
    description: 'Explicit cancellation rights and process for consumers',
    category: 'consumer_protection', is_blocker: false, status: 'implemented',
  },
  {
    id: '8', control_code: 'TCK-C08',
    name: 'Postponement Clause',
    description: 'Consumer rights on postponement, including refund trigger conditions',
    category: 'consumer_protection', is_blocker: false, status: 'partial',
  },
  {
    id: '9', control_code: 'TCK-C09',
    name: 'Marketing Consent',
    description: 'Explicit opt-in consent for marketing communications',
    category: 'data_privacy', is_blocker: false, status: 'implemented',
  },
  {
    id: '10', control_code: 'TCK-C10',
    name: 'Anti-Bot / Bulk Purchase Protection',
    description: 'CAPTCHA and purchase rate limiting to prevent scalping',
    category: 'resale', is_blocker: false, status: 'missing',
  },
  {
    id: '11', control_code: 'TCK-C11',
    name: 'Electronic Invoice Setup',
    description: 'AFIP-compliant electronic invoice generation per Res. 1415/2003',
    category: 'tax', is_blocker: false, status: 'implemented',
  },
  {
    id: '12', control_code: 'TCK-C12',
    name: 'AAIP Registration',
    description: 'Database controller registration with Argentina AAIP (PDPA)',
    category: 'data_privacy', is_blocker: false, status: 'missing',
  },
  {
    id: '13', control_code: 'TCK-C13',
    name: 'Venue Authorization',
    description: 'Written authorization from venue owner or operator',
    category: 'permits', is_blocker: false, status: 'implemented',
  },
  {
    id: '14', control_code: 'TCK-C14',
    name: 'Event / Public Safety Permit',
    description: 'Municipal event permit or public assembly approval',
    category: 'permits', is_blocker: false, status: 'missing',
  },
  {
    id: '15', control_code: 'TCK-C15',
    name: 'Chargeback Evidence Pack',
    description: 'Pre-packaged evidence for dispute resolution (T&C, delivery proof)',
    category: 'payments', is_blocker: false, status: 'implemented',
  },
]

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  implemented:    { label: 'Implemented',    color: 'text-green-400',  bg: 'bg-green-950/20',  border: 'border-green-800' },
  partial:        { label: 'Partial',        color: 'text-yellow-400', bg: 'bg-yellow-950/20', border: 'border-yellow-800' },
  missing:        { label: 'Missing',        color: 'text-red-400',    bg: 'bg-red-950/20',    border: 'border-red-900' },
  not_applicable: { label: 'N/A',            color: 'text-zinc-500',   bg: 'bg-zinc-900',      border: 'border-zinc-800' },
}

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

export default function EventChecklist() {
  const params = useParams()
  const id = params.id as string
  const [items, setItems] = useState<CheckItem[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => {
    if (!id) return
    fetch(`${API}/api/v1/ticketing/events/${id}/checklist`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setItems(d.items ?? MOCK_CHECKLIST))
      .catch(() => setItems(MOCK_CHECKLIST))
      .finally(() => setLoading(false))
  }, [id])

  async function updateStatus(itemId: string, status: string) {
    setUpdating(itemId)
    try {
      await fetch(`${API}/api/v1/ticketing/events/${id}/checklist/${itemId}`, {
        method: 'PATCH',
        headers: authHeaders(),
        body: JSON.stringify({ status }),
      })
      setItems(prev => prev.map(i => i.id === itemId ? { ...i, status: status as any } : i))
    } catch {}
    finally { setUpdating(null) }
  }

  const filtered = filterStatus ? items.filter(i => i.status === filterStatus) : items
  const implemented = items.filter(i => i.status === 'implemented').length
  const missing = items.filter(i => i.status === 'missing').length
  const blockersMissing = items.filter(i => i.is_blocker && i.status !== 'implemented').length

  const grouped = filtered.reduce<Record<string, CheckItem[]>>((acc, item) => {
    const cat = item.category
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(item)
    return acc
  }, {})

  if (loading) return <div className="text-zinc-500 text-sm">Loading checklist…</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Link href="/ticketing/events" className="hover:text-zinc-300">Events</Link>
            <span>/</span>
            <Link href={`/ticketing/events/${id}`} className="hover:text-zinc-300">Event</Link>
            <span>/</span>
            <span>Compliance Checklist</span>
          </div>
          <h1 className="text-2xl font-bold">Compliance Checklist</h1>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-400">{implemented}</div>
          <div className="text-xs text-zinc-500">Implemented</div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-yellow-400">
            {items.filter(i => i.status === 'partial').length}
          </div>
          <div className="text-xs text-zinc-500">Partial</div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-red-400">{missing}</div>
          <div className="text-xs text-zinc-500">Missing</div>
        </div>
        <div className={`border rounded-lg p-4 text-center ${blockersMissing > 0 ? 'border-red-900 bg-red-950/20' : 'border-green-800 bg-green-950/20'}`}>
          <div className={`text-2xl font-bold ${blockersMissing > 0 ? 'text-red-400' : 'text-green-400'}`}>{blockersMissing}</div>
          <div className="text-xs text-zinc-500">Blockers Missing</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-3">
        {['', 'missing', 'partial', 'implemented', 'not_applicable'].map(s => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
              filterStatus === s
                ? 'bg-zinc-700 border-zinc-600 text-zinc-100'
                : 'border-zinc-800 text-zinc-400 hover:border-zinc-700'
            }`}
          >
            {s ? STATUS_CONFIG[s]?.label : 'All'}
          </button>
        ))}
      </div>

      {/* Grouped items */}
      {Object.entries(grouped).map(([cat, catItems]) => (
        <div key={cat} className="border border-zinc-800 rounded-lg overflow-hidden">
          <div className="px-5 py-3 bg-zinc-900 border-b border-zinc-800">
            <span className="text-sm font-semibold text-zinc-300">
              {CATEGORY_LABELS[cat] ?? cat}
            </span>
            <span className="ml-2 text-xs text-zinc-500">({catItems.length})</span>
          </div>
          <div className="divide-y divide-zinc-800/60">
            {catItems.map(item => {
              const cfg = STATUS_CONFIG[item.status]
              return (
                <div key={item.id} className={`p-5 ${cfg.bg}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-xs text-zinc-500">{item.control_code}</span>
                        <span className="font-medium text-sm">{item.name}</span>
                        {item.is_blocker && (
                          <span className="px-1.5 py-0.5 bg-red-950 border border-red-900 text-red-400 text-xs rounded">
                            BLOCKER
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 mt-1">{item.description}</p>
                      {item.notes && (
                        <p className="text-xs text-zinc-400 mt-1 italic">{item.notes}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                      <select
                        value={item.status}
                        disabled={updating === item.id}
                        onChange={e => updateStatus(item.id, e.target.value)}
                        className="px-2 py-1 bg-zinc-900 border border-zinc-700 rounded text-xs focus:outline-none disabled:opacity-50"
                      >
                        <option value="implemented">Implemented</option>
                        <option value="partial">Partial</option>
                        <option value="missing">Missing</option>
                        <option value="not_applicable">N/A</option>
                      </select>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      <div className="flex gap-3">
        <Link href={`/ticketing/events/${id}/risk`} className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white">
          View Risk Assessment →
        </Link>
        <Link href={`/ticketing/documents?event_id=${id}`} className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Generate Documents
        </Link>
      </div>
    </div>
  )
}
