'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

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

const STATUS_COLORS: Record<string, string> = {
  draft:        'text-zinc-400',
  under_review: 'text-yellow-400',
  approved:     'text-green-400',
  approved_with_conditions: 'text-yellow-400',
  blocked:      'text-red-400',
  live:         'text-blue-400',
  completed:    'text-zinc-500',
  cancelled:    'text-zinc-600',
}

const MOCK_EVENTS = [
  {
    id: 'e1',
    name: 'Lollapalooza Argentina 2026',
    country_code: 'AR',
    city: 'Buenos Aires',
    event_date: '2026-03-20T18:00:00Z',
    status: 'blocked',
    launch_decision: 'BLOCKED',
    risk_score_overall: 72,
    blocking_reasons: ['Missing promoter agreement', 'Botón de arrepentimiento not implemented'],
    has_promoter_agreement: false,
    has_consumer_terms: true,
    has_refund_policy: true,
    has_payment_processor: true,
    has_withdrawal_button: false,
    created_at: '2026-05-01T10:00:00Z',
  },
  {
    id: 'e2',
    name: 'Buenos Aires Tech Summit',
    country_code: 'AR',
    city: 'Buenos Aires',
    event_date: '2026-06-15T09:00:00Z',
    status: 'approved',
    launch_decision: 'APPROVED',
    risk_score_overall: 18,
    blocking_reasons: [],
    has_promoter_agreement: true,
    has_consumer_terms: true,
    has_refund_policy: true,
    has_payment_processor: true,
    has_withdrawal_button: true,
    created_at: '2026-05-10T14:00:00Z',
  },
  {
    id: 'e3',
    name: 'Rock in Rio São Paulo',
    country_code: 'BR',
    city: 'São Paulo',
    event_date: '2026-09-05T18:00:00Z',
    status: 'under_review',
    launch_decision: 'APPROVED_WITH_CONDITIONS',
    risk_score_overall: 45,
    blocking_reasons: [],
    has_promoter_agreement: true,
    has_consumer_terms: true,
    has_refund_policy: true,
    has_payment_processor: true,
    has_withdrawal_button: false,
    created_at: '2026-05-15T09:00:00Z',
  },
  {
    id: 'e4',
    name: 'Mexico City Music Week',
    country_code: 'MX',
    city: 'Mexico City',
    event_date: '2026-07-20T20:00:00Z',
    status: 'draft',
    launch_decision: null,
    risk_score_overall: 55,
    blocking_reasons: ['No payment processor record'],
    has_promoter_agreement: true,
    has_consumer_terms: false,
    has_refund_policy: false,
    has_payment_processor: false,
    has_withdrawal_button: false,
    created_at: '2026-05-20T11:00:00Z',
  },
]

export default function EventsList() {
  const [events, setEvents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [countryFilter, setCountryFilter] = useState('')

  useEffect(() => {
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    if (countryFilter) params.set('country', countryFilter)
    fetch(`${API}/api/v1/ticketing/events?${params}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setEvents(d.events ?? []))
      .catch(() => setEvents(MOCK_EVENTS))
      .finally(() => setLoading(false))
  }, [statusFilter, countryFilter])

  const filtered = events.filter(e => {
    if (statusFilter && e.status !== statusFilter) return false
    if (countryFilter && e.country_code !== countryFilter) return false
    return true
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Events</h1>
          <p className="text-sm text-zinc-500 mt-1">Track compliance for each ticketing event</p>
        </div>
        <Link
          href="/ticketing/events/new"
          className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white"
        >
          + New Event
        </Link>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
        >
          {['', 'draft', 'under_review', 'approved', 'blocked', 'live', 'completed'].map(s => (
            <option key={s} value={s}>{s || 'All Statuses'}</option>
          ))}
        </select>
        <select
          value={countryFilter}
          onChange={e => setCountryFilter(e.target.value)}
          className="px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
        >
          {['', 'AR', 'BR', 'MX', 'CO', 'CL', 'PE', 'UY', 'PY'].map(c => (
            <option key={c} value={c}>{c || 'All Countries'}</option>
          ))}
        </select>
        <span className="px-3 py-2 text-sm text-zinc-500">{filtered.length} event(s)</span>
      </div>

      {/* Event cards */}
      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="border border-zinc-800 rounded-lg p-5 animate-pulse">
              <div className="h-4 bg-zinc-800 rounded w-1/3 mb-3" />
              <div className="h-3 bg-zinc-800 rounded w-1/2" />
            </div>
          ))
        ) : filtered.length === 0 ? (
          <div className="border border-zinc-800 rounded-lg p-8 text-center">
            <p className="text-zinc-500 text-sm">No events found.</p>
            <Link href="/ticketing/events/new" className="text-sm text-zinc-300 underline mt-2 inline-block">
              Create your first event
            </Link>
          </div>
        ) : (
          filtered.map(ev => {
            const complianceScore = Math.max(0, 100 - (ev.risk_score_overall ?? 0))
            const blockers = ev.blocking_reasons ?? []
            return (
              <div key={ev.id} className="border border-zinc-800 rounded-lg p-5 hover:border-zinc-600 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <Link
                        href={`/ticketing/events/${ev.id}`}
                        className="font-semibold text-zinc-100 hover:text-white"
                      >
                        {ev.name}
                      </Link>
                      <span className="font-mono text-xs text-zinc-500">{ev.country_code}</span>
                      {ev.city && <span className="text-xs text-zinc-500">{ev.city}</span>}
                      <span className={`text-xs ${STATUS_COLORS[ev.status] ?? 'text-zinc-500'}`}>
                        {ev.status?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    {ev.event_date && (
                      <div className="text-xs text-zinc-500 mt-1">
                        {new Date(ev.event_date).toLocaleDateString('en-GB', {
                          day: 'numeric', month: 'long', year: 'numeric',
                        })}
                      </div>
                    )}
                    {blockers.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {blockers.slice(0, 2).map((b: string, i: number) => (
                          <div key={i} className="text-xs text-red-400 flex items-start gap-1">
                            <span className="text-red-600 mt-0.5">•</span>{b}
                          </div>
                        ))}
                        {blockers.length > 2 && (
                          <div className="text-xs text-red-500">+{blockers.length - 2} more blockers</div>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                      <div className="text-lg font-bold">{complianceScore}<span className="text-zinc-500 text-sm">/100</span></div>
                      <div className="text-xs text-zinc-500">compliance</div>
                    </div>
                    {ev.launch_decision && (
                      <span className={`px-2.5 py-1 text-xs rounded border ${DECISION_COLORS[ev.launch_decision] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
                        {ev.launch_decision.replace(/_/g, ' ')}
                      </span>
                    )}
                    <div className="flex gap-2">
                      <Link
                        href={`/ticketing/events/${ev.id}`}
                        className="px-3 py-1.5 border border-zinc-800 rounded-md text-xs hover:bg-zinc-900"
                      >
                        View
                      </Link>
                      <Link
                        href={`/ticketing/events/${ev.id}/risk`}
                        className="px-3 py-1.5 border border-zinc-800 rounded-md text-xs hover:bg-zinc-900"
                      >
                        Risk
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
