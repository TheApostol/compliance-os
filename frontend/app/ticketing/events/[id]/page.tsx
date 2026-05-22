'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

const DECISION_COLORS: Record<string, string> = {
  APPROVED:                 'bg-green-950 text-green-300 border-green-900',
  APPROVED_WITH_CONDITIONS: 'bg-yellow-950 text-yellow-300 border-yellow-900',
  BLOCKED:                  'bg-red-950 text-red-300 border-red-900',
}

const COMPLIANCE_FLAGS = [
  { key: 'has_promoter_agreement',  label: 'Promoter Agreement' },
  { key: 'has_refund_policy',       label: 'Refund Policy' },
  { key: 'has_consumer_terms',      label: 'Consumer T&C' },
  { key: 'has_payment_processor',   label: 'Payment Processor' },
  { key: 'has_privacy_policy',      label: 'Privacy Policy' },
  { key: 'has_withdrawal_button',   label: 'Botón Arrepentimiento' },
  { key: 'has_cancellation_clause', label: 'Cancellation Clause' },
  { key: 'has_postponement_clause', label: 'Postponement Clause' },
  { key: 'has_marketing_consent',   label: 'Marketing Consent' },
  { key: 'has_anti_bot_protection', label: 'Anti-Bot Protection' },
  { key: 'has_electronic_invoice',  label: 'E-Invoice Setup' },
  { key: 'has_aaip_registration',   label: 'AAIP Registration' },
  { key: 'has_venue_authorization', label: 'Venue Authorization' },
  { key: 'has_event_permit',        label: 'Event Permit' },
  { key: 'has_chargeback_evidence', label: 'Chargeback Evidence' },
]

const MOCK_EVENT = {
  id: 'e1',
  name: 'Lollapalooza Argentina 2026',
  country_code: 'AR',
  city: 'Buenos Aires',
  event_date: '2026-03-20T18:00:00Z',
  status: 'blocked',
  launch_decision: 'BLOCKED',
  risk_score_overall: 72,
  blocking_reasons: [
    'Missing promoter agreement — contractual liability unallocated',
    'Botón de arrepentimiento not implemented — mandatory in Argentina (Res. 424/2020)',
  ],
  compliance_gaps: ['Promoter Compliance Agreement', 'Botón de Arrepentimiento / Purchase Withdrawal', 'AAIP database controller registration'],
  has_promoter_agreement: false,
  has_refund_policy: true,
  has_consumer_terms: true,
  has_payment_processor: true,
  has_privacy_policy: true,
  has_withdrawal_button: false,
  has_cancellation_clause: true,
  has_postponement_clause: false,
  has_marketing_consent: true,
  has_anti_bot_protection: false,
  has_electronic_invoice: true,
  has_aaip_registration: false,
  has_venue_authorization: true,
  has_event_permit: false,
  has_chargeback_evidence: true,
  resale_enabled: false,
  crypto_payments_enabled: false,
  wallet_balance_enabled: false,
  service_fee_pct: 12,
  expected_attendance: 50000,
  refund_sla_days: 10,
  complaint_sla_days: 15,
}

export default function EventDetail() {
  const params = useParams()
  const id = params.id as string
  const [event, setEvent] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    fetch(`${API}/api/v1/ticketing/events/${id}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setEvent(d))
      .catch(() => setEvent(MOCK_EVENT))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-zinc-800 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (!event) return <div className="text-zinc-500">Event not found</div>

  const ev = event
  const complianceScore = Math.max(0, 100 - (ev.risk_score_overall ?? 0))
  const blockers = ev.blocking_reasons ?? []
  const gaps = ev.compliance_gaps ?? []

  const implemented = COMPLIANCE_FLAGS.filter(f => ev[f.key]).length
  const total = COMPLIANCE_FLAGS.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 text-xs text-zinc-500 mb-2">
          <Link href="/ticketing/events" className="hover:text-zinc-300">Events</Link>
          <span>/</span>
          <span>{ev.name}</span>
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">{ev.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-mono text-sm text-zinc-400">{ev.country_code}</span>
              {ev.city && <span className="text-sm text-zinc-500">{ev.city}</span>}
              {ev.event_date && (
                <span className="text-sm text-zinc-500">
                  {new Date(ev.event_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {ev.launch_decision && (
              <span className={`px-3 py-1.5 text-sm font-medium rounded border ${DECISION_COLORS[ev.launch_decision] ?? ''}`}>
                {ev.launch_decision.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold">{complianceScore}</div>
          <div className="text-xs text-zinc-500">Compliance Score</div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-orange-400">{ev.risk_score_overall}</div>
          <div className="text-xs text-zinc-500">Risk Score</div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-red-400">{blockers.length}</div>
          <div className="text-xs text-zinc-500">Blockers</div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold">{implemented}/{total}</div>
          <div className="text-xs text-zinc-500">Controls Implemented</div>
        </div>
      </div>

      {/* Action links */}
      <div className="flex gap-3 flex-wrap">
        <Link href={`/ticketing/events/${id}/risk`} className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Risk Assessment →
        </Link>
        <Link href={`/ticketing/events/${id}/checklist`} className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Compliance Checklist →
        </Link>
        <Link href={`/ticketing/reports?event_id=${id}`} className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Generate Report →
        </Link>
      </div>

      {/* Blockers */}
      {blockers.length > 0 && (
        <div className="border border-red-900 bg-red-950/20 rounded-lg p-5">
          <div className="text-sm font-semibold text-red-400 mb-3">Launch Blockers</div>
          <ul className="space-y-2">
            {blockers.map((b: string, i: number) => (
              <li key={i} className="text-sm text-red-200 flex items-start gap-2">
                <span className="text-red-500 mt-0.5 shrink-0">✕</span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Compliance controls grid */}
      <div>
        <h2 className="text-base font-semibold mb-4">Compliance Controls</h2>
        <div className="grid grid-cols-3 gap-2">
          {COMPLIANCE_FLAGS.map(flag => {
            const ok = !!ev[flag.key]
            return (
              <div
                key={flag.key}
                className={`p-3 rounded-md border flex items-center gap-2 ${
                  ok ? 'border-green-800 bg-green-950/20' : 'border-red-900 bg-red-950/10'
                }`}
              >
                <span className={`text-sm ${ok ? 'text-green-400' : 'text-red-400'}`}>
                  {ok ? '✓' : '✕'}
                </span>
                <span className="text-xs">{flag.label}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Missing controls */}
      {gaps.length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold mb-3 text-zinc-300">Missing Controls</h2>
          <ul className="space-y-1">
            {gaps.map((g: string, i: number) => (
              <li key={i} className="text-sm text-zinc-400 flex items-start gap-2">
                <span className="text-yellow-600 mt-0.5">•</span>{g}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
