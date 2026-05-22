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

const MOCK_DASHBOARD = {
  compliance_score: 62,
  risk_score: 38,
  total_events: 4,
  active_events: 1,
  blocked_events: 1,
  open_claims: 3,
  open_chargebacks: 2,
  chargeback_exposure_usd: 1840,
  refund_sla_ok: true,
  critical_alerts: [
    "1 event BLOCKED — missing required compliance controls",
    "2 open chargebacks — USD 1,840 exposure",
    "Event 'Lollapalooza AR 2026': Missing promoter agreement",
  ],
  events_by_status: {
    draft: 1, under_review: 1, approved: 1, blocked: 1, live: 0, completed: 0, cancelled: 0,
  },
}

function ScoreCircle({ score, label, color }: { score: number; label: string; color: string }) {
  const pct = Math.max(0, Math.min(100, score))
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#27272a" strokeWidth="3" />
          <circle
            cx="18" cy="18" r="15.9" fill="none"
            stroke={color} strokeWidth="3"
            strokeDasharray={`${pct} ${100 - pct}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-lg font-bold">
          {pct}
        </span>
      </div>
      <span className="text-xs text-zinc-500 text-center">{label}</span>
    </div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    LOW:      'bg-green-950 text-green-300 border-green-900',
    MEDIUM:   'bg-yellow-950 text-yellow-300 border-yellow-900',
    HIGH:     'bg-orange-950 text-orange-300 border-orange-900',
    CRITICAL: 'bg-red-950 text-red-300 border-red-900',
    BLOCKED:  'bg-red-950 text-red-300 border-red-900',
    APPROVED: 'bg-green-950 text-green-300 border-green-900',
    APPROVED_WITH_CONDITIONS: 'bg-yellow-950 text-yellow-300 border-yellow-900',
  }
  return (
    <span className={`px-2 py-0.5 text-xs rounded border ${colors[level] ?? 'bg-zinc-800 text-zinc-400 border-zinc-700'}`}>
      {level.replace(/_/g, ' ')}
    </span>
  )
}

const COUNTRY_RISKS = [
  { code: 'AR', name: 'Argentina',  risk: 75, level: 'HIGH' },
  { code: 'BR', name: 'Brazil',     risk: 65, level: 'HIGH' },
  { code: 'MX', name: 'Mexico',     risk: 55, level: 'MEDIUM' },
  { code: 'CO', name: 'Colombia',   risk: 50, level: 'MEDIUM' },
  { code: 'CL', name: 'Chile',      risk: 45, level: 'MEDIUM' },
  { code: 'PE', name: 'Peru',       risk: 60, level: 'MEDIUM' },
  { code: 'UY', name: 'Uruguay',    risk: 40, level: 'LOW' },
  { code: 'PY', name: 'Paraguay',   risk: 35, level: 'LOW' },
]

export default function TicketingDashboard() {
  const [data, setData] = useState<typeof MOCK_DASHBOARD | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/api/v1/ticketing/dashboard`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(MOCK_DASHBOARD))
      .finally(() => setLoading(false))
  }, [])

  const d = data ?? MOCK_DASHBOARD

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Ticketing Compliance Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Real-time compliance posture for your ticketing platform across LATAM
        </p>
      </div>

      {/* Score cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="border border-zinc-800 rounded-lg p-5 flex flex-col items-center gap-3">
          <ScoreCircle score={d.compliance_score} label="Compliance Score" color="#22c55e" />
        </div>
        <div className="border border-zinc-800 rounded-lg p-5 flex flex-col items-center gap-3">
          <ScoreCircle score={d.risk_score} label="Risk Score" color="#f97316" />
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
          <div>
            <div className="text-2xl font-bold">{d.total_events}</div>
            <div className="text-xs text-zinc-500">Total Events</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-400">{d.active_events}</div>
            <div className="text-xs text-zinc-500">Live</div>
          </div>
        </div>
        <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
          <div>
            <div className="text-2xl font-bold text-red-400">{d.blocked_events}</div>
            <div className="text-xs text-zinc-500">Blocked</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-400">{d.open_claims}</div>
            <div className="text-xs text-zinc-500">Open Claims</div>
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Open Chargebacks', value: d.open_chargebacks, color: 'text-red-400' },
          { label: 'Chargeback Exposure', value: `USD ${d.chargeback_exposure_usd?.toLocaleString()}`, color: 'text-red-400' },
          { label: 'Refund SLA', value: d.refund_sla_ok ? 'OK' : 'BREACH', color: d.refund_sla_ok ? 'text-green-400' : 'text-red-400' },
          { label: 'Events by Status', value: `${d.events_by_status?.live ?? 0} live`, color: 'text-zinc-100' },
        ].map(m => (
          <div key={m.label} className="border border-zinc-800 rounded-lg p-4">
            <div className={`text-xl font-bold ${m.color}`}>{m.value}</div>
            <div className="text-xs text-zinc-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Critical alerts */}
      {d.critical_alerts?.length > 0 && (
        <div className="border border-red-900 bg-red-950/20 rounded-lg p-5">
          <div className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            Critical Alerts
          </div>
          <ul className="space-y-2">
            {d.critical_alerts.map((alert, i) => (
              <li key={i} className="text-sm text-red-200 flex items-start gap-2">
                <span className="text-red-500 mt-1">•</span>
                {alert}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Country risk matrix */}
      <div>
        <h2 className="text-base font-semibold mb-4">Country Risk Scores</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {COUNTRY_RISKS.map(c => (
            <div key={c.code} className="border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-sm font-bold">{c.code}</span>
                <RiskBadge level={c.level} />
              </div>
              <div className="text-xs text-zinc-500 mb-1">{c.name}</div>
              <div className="h-1.5 bg-zinc-800 rounded-full">
                <div
                  className={`h-1.5 rounded-full ${
                    c.risk >= 70 ? 'bg-red-500' : c.risk >= 50 ? 'bg-orange-500' : c.risk >= 35 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${c.risk}%` }}
                />
              </div>
              <div className="text-xs text-zinc-400 mt-1">{c.risk}/100</div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-3 gap-4">
        <Link href="/ticketing/events/new" className="border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors">
          <div className="text-sm font-medium">Create Event</div>
          <div className="text-xs text-zinc-500 mt-1">Run pre-launch compliance check</div>
        </Link>
        <Link href="/ticketing/regulatory-matrix" className="border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors">
          <div className="text-sm font-medium">View Obligations</div>
          <div className="text-xs text-zinc-500 mt-1">Browse regulatory matrix by country</div>
        </Link>
        <Link href="/ticketing/ai-copilot" className="border border-zinc-800 rounded-lg p-4 hover:border-zinc-600 transition-colors">
          <div className="text-sm font-medium">Ask AI Copilot</div>
          <div className="text-xs text-zinc-500 mt-1">Get compliance guidance instantly</div>
        </Link>
      </div>
    </div>
  )
}
