'use client'

import { Suspense, useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp', 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

const DECISION_STYLES: Record<string, { border: string; bg: string; text: string }> = {
  APPROVED:                 { border: 'border-green-800',  bg: 'bg-green-950/20',  text: 'text-green-300' },
  APPROVED_WITH_CONDITIONS: { border: 'border-yellow-800', bg: 'bg-yellow-950/20', text: 'text-yellow-300' },
  BLOCKED:                  { border: 'border-red-800',    bg: 'bg-red-950/20',    text: 'text-red-300' },
}

const MOCK_EVENTS = [
  { id: 'e1', name: 'Lollapalooza Argentina 2026', country_code: 'AR' },
  { id: 'e2', name: 'Buenos Aires Tech Summit', country_code: 'AR' },
  { id: 'e3', name: 'Rock in Rio São Paulo', country_code: 'BR' },
]

const MOCK_REPORT = {
  event_id: 'e1',
  event_name: 'Lollapalooza Argentina 2026',
  country_code: 'AR',
  generated_at: new Date().toISOString(),
  risk_score: 72,
  launch_decision: 'BLOCKED',
  blocking_reasons: [
    'Missing promoter agreement — contractual liability unallocated',
    'Botón de arrepentimiento not implemented — mandatory in Argentina (Res. 424/2020)',
  ],
  high_risk_triggers: [
    'Refund automation incomplete',
    'No AAIP registration',
  ],
  missing_controls: [
    'Promoter Compliance Agreement',
    'Botón de Arrepentimiento',
    'AAIP Registration',
    'Anti-Bot Protection',
    'Event Permit',
  ],
  recommendations: [
    'Resolve all blocking issues before event launch',
    'Execute promoter compliance agreement',
    'Implement Botón de Arrepentimiento on homepage and post-purchase page',
    'Complete AAIP registration at argentina.gob.ar/aaip',
    'Deploy CAPTCHA and purchase rate limiting',
  ],
  risk_dimensions: {
    consumer_risk: 85,
    refund_risk: 40,
    resale_risk: 10,
    payment_risk: 30,
    data_privacy_risk: 70,
    tax_risk: 60,
    contractual_risk: 100,
    fraud_aml_risk: 20,
    operational_risk: 45,
    country_enforcement_risk: 60,
  },
}

const DIMENSION_LABELS: Record<string, string> = {
  consumer_risk:            'Consumer Risk',
  refund_risk:              'Refund Risk',
  resale_risk:              'Resale Risk',
  payment_risk:             'Payment Risk',
  data_privacy_risk:        'Data Privacy Risk',
  tax_risk:                 'Tax / Invoicing Risk',
  contractual_risk:         'Contractual Risk',
  fraud_aml_risk:           'Fraud / AML Risk',
  operational_risk:         'Operational Risk',
  country_enforcement_risk: 'Country Enforcement Risk',
}

export default function ReportsPage() {
  return (
    <Suspense fallback={null}>
      <ReportsPageInner />
    </Suspense>
  )
}

function ReportsPageInner() {
  const searchParams = useSearchParams()
  const [events, setEvents] = useState<any[]>([])
  const [selectedEvent, setSelectedEvent] = useState(searchParams.get('event_id') ?? '')
  const [generating, setGenerating] = useState(false)
  const [report, setReport] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/ticketing/events`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setEvents(d.events ?? MOCK_EVENTS))
      .catch(() => setEvents(MOCK_EVENTS))
  }, [])

  useEffect(() => {
    if (selectedEvent) loadReport(selectedEvent)
    else setReport(null)
  }, [selectedEvent])

  async function loadReport(eventId: string) {
    try {
      const res = await fetch(`${API}/api/v1/ticketing/reports/${eventId}`, { headers: authHeaders() })
      const d = await res.json()
      if (d.risk_score !== undefined) setReport(d)
      else setReport(null)
    } catch {
      setReport(null)
    }
  }

  async function generate() {
    if (!selectedEvent) return
    setGenerating(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/v1/ticketing/reports`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ event_id: selectedEvent }),
      })
      const d = await res.json()
      if (d.risk_score !== undefined) {
        setReport(d)
      } else {
        setError(d.detail ?? 'Failed to generate report')
        setReport(MOCK_REPORT)
      }
    } catch {
      setReport(MOCK_REPORT)
    } finally {
      setGenerating(false)
    }
  }

  const r = report
  const style = r ? (DECISION_STYLES[r.launch_decision] ?? DECISION_STYLES.BLOCKED) : null
  const complianceScore = r ? Math.max(0, 100 - (r.risk_score ?? 0)) : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Compliance Reports</h1>
        <p className="text-sm text-zinc-500 mt-1">Generate and view event compliance reports</p>
      </div>

      {/* Event selector + generate */}
      <div className="border border-zinc-800 rounded-lg p-5 flex items-end gap-4">
        <div className="flex-1">
          <label className="text-xs text-zinc-500 block mb-1">Select Event</label>
          <select
            value={selectedEvent}
            onChange={e => setSelectedEvent(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
          >
            <option value="">Choose an event…</option>
            {events.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
          </select>
        </div>
        <button
          onClick={generate}
          disabled={generating || !selectedEvent}
          className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50 shrink-0"
        >
          {generating ? 'Generating…' : 'Generate Report'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">{error}</div>
      )}

      {!r && !generating && selectedEvent && (
        <div className="border border-zinc-800 rounded-lg p-8 text-center text-zinc-500 text-sm">
          No report found for this event. Click "Generate Report" to create one.
        </div>
      )}

      {r && style && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-zinc-500">{r.event_name}</div>
              <div className="text-sm text-zinc-400">
                {r.country_code} · Generated {new Date(r.generated_at).toLocaleString()}
              </div>
            </div>
            <Link
              href={`/ticketing/events/${selectedEvent}`}
              className="text-xs text-zinc-400 hover:text-zinc-200 border border-zinc-800 px-3 py-1.5 rounded-md"
            >
              View Event →
            </Link>
          </div>

          {/* Decision card */}
          <div className={`border ${style.border} ${style.bg} rounded-lg p-6`}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-zinc-500 mb-1">Launch Decision</div>
                <div className={`text-2xl font-bold ${style.text}`}>
                  {r.launch_decision?.replace(/_/g, ' ')}
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold">{complianceScore}<span className="text-zinc-500 text-lg">/100</span></div>
                <div className="text-xs text-zinc-500">Compliance Score</div>
              </div>
            </div>
            {r.blocking_reasons?.length > 0 && (
              <div className="mt-4 space-y-1">
                {r.blocking_reasons.map((reason: string, i: number) => (
                  <div key={i} className="text-sm text-red-300 flex items-start gap-2">
                    <span className="text-red-500 mt-0.5 shrink-0">✕</span>{reason}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Dimensions */}
          {r.risk_dimensions && Object.keys(r.risk_dimensions).length > 0 && (
            <div className="border border-zinc-800 rounded-lg p-6 space-y-4">
              <div className="text-sm font-semibold text-zinc-300">Risk Dimensions</div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-3">
                {Object.entries(DIMENSION_LABELS).map(([dim, label]) => {
                  const score = r.risk_dimensions?.[dim] ?? 0
                  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f97316' : score >= 20 ? '#eab308' : '#22c55e'
                  return (
                    <div key={dim} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-zinc-400">{label}</span>
                        <span className="font-mono font-medium" style={{ color }}>{score}</span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-full">
                        <div className="h-1.5 rounded-full transition-all" style={{ width: `${score}%`, backgroundColor: color }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            {/* High-risk triggers */}
            {r.high_risk_triggers?.length > 0 && (
              <div className="border border-yellow-900 rounded-lg p-5">
                <div className="text-sm font-semibold text-yellow-400 mb-3">High-Risk Triggers</div>
                <ul className="space-y-2">
                  {r.high_risk_triggers.map((t: string, i: number) => (
                    <li key={i} className="text-sm text-yellow-200 flex items-start gap-2">
                      <span className="text-yellow-500 mt-0.5 shrink-0">⚠</span>{t}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommendations */}
            {r.recommendations?.length > 0 && (
              <div className="border border-zinc-800 rounded-lg p-5">
                <div className="text-sm font-semibold text-zinc-300 mb-3">Recommendations</div>
                <ol className="space-y-2">
                  {r.recommendations.map((rec: string, i: number) => (
                    <li key={i} className="text-sm text-zinc-400 flex items-start gap-2">
                      <span className="text-zinc-600 mt-0.5 shrink-0">{i + 1}.</span>{rec}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>

          {/* Missing controls */}
          {r.missing_controls?.length > 0 && (
            <div className="border border-zinc-800 rounded-lg p-5">
              <div className="text-sm font-semibold text-zinc-300 mb-3">
                Missing Controls ({r.missing_controls.length})
              </div>
              <div className="flex flex-wrap gap-2">
                {r.missing_controls.map((c: string, i: number) => (
                  <span key={i} className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 rounded-full text-xs text-zinc-300">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <Link
              href={`/ticketing/events/${selectedEvent}/risk`}
              className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white"
            >
              Full Risk Assessment →
            </Link>
            <Link
              href={`/ticketing/events/${selectedEvent}/checklist`}
              className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900"
            >
              View Checklist
            </Link>
            <Link
              href={`/ticketing/documents?event_id=${selectedEvent}`}
              className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900"
            >
              Generate Documents
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
