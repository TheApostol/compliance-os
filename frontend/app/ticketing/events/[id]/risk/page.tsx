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

const DECISION_STYLES: Record<string, { border: string; bg: string; text: string; label: string }> = {
  APPROVED: {
    border: 'border-green-800',
    bg:     'bg-green-950/20',
    text:   'text-green-300',
    label:  'APPROVED',
  },
  APPROVED_WITH_CONDITIONS: {
    border: 'border-yellow-800',
    bg:     'bg-yellow-950/20',
    text:   'text-yellow-300',
    label:  'APPROVED WITH CONDITIONS',
  },
  BLOCKED: {
    border: 'border-red-800',
    bg:     'bg-red-950/20',
    text:   'text-red-300',
    label:  'BLOCKED',
  },
}

const MOCK_ASSESSMENT = {
  overall_score: 72,
  launch_decision: 'BLOCKED',
  dimensions: {
    consumer_risk:            85,
    refund_risk:              40,
    resale_risk:              10,
    payment_risk:             30,
    data_privacy_risk:        70,
    tax_risk:                 60,
    contractual_risk:         100,
    fraud_aml_risk:           20,
    operational_risk:         45,
    country_enforcement_risk: 60,
  },
  blocking_reasons: [
    'Missing promoter agreement — contractual liability unallocated',
    'Botón de arrepentimiento not implemented — mandatory in Argentina (Res. 424/2020)',
  ],
  high_risk_triggers: [
    'Refund automation incomplete — chargeback and consumer risk elevated',
    'No AAIP registration — data protection violation risk',
  ],
  missing_controls: [
    'Promoter Compliance Agreement',
    'Botón de Arrepentimiento / Purchase Withdrawal',
    'AAIP database controller registration',
    'Anti-bot / bulk purchase protection',
    'Event/public safety permit',
  ],
  recommendations: [
    'URGENT: Resolve all blocking issues before proceeding with event launch',
    'Execute compliance schedule with promoter before event goes live',
    'Implement visible Botón de Arrepentimiento on homepage and post-purchase page',
    'Complete AAIP online registration at argentina.gob.ar/aaip',
    'Deploy CAPTCHA and purchase rate limiting',
  ],
}

function ScoreBar({ score, label, dim }: { score: number; label: string; dim: string }) {
  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f97316' : score >= 20 ? '#eab308' : '#22c55e'
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono font-medium" style={{ color }}>{score}</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full">
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

export default function EventRisk() {
  const params = useParams()
  const id = params.id as string
  const [assessment, setAssessment] = useState<any>(null)
  const [running, setRunning] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Try fetching report (which includes latest assessment)
    if (!id) return
    fetch(`${API}/api/v1/ticketing/reports/${id}`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => {
        if (d.risk_score !== undefined) {
          setAssessment({
            overall_score: d.risk_score,
            launch_decision: d.launch_decision,
            dimensions: d.risk_dimensions ?? {},
            blocking_reasons: d.blocking_reasons ?? [],
            high_risk_triggers: d.high_risk_triggers ?? [],
            missing_controls: d.missing_controls ?? [],
            recommendations: d.recommendations ?? [],
          })
        } else {
          setAssessment(MOCK_ASSESSMENT)
        }
      })
      .catch(() => setAssessment(MOCK_ASSESSMENT))
      .finally(() => setLoading(false))
  }, [id])

  async function runAssessment() {
    setRunning(true)
    try {
      const res = await fetch(`${API}/api/v1/ticketing/events/${id}/risk-assessment`, {
        method: 'POST',
        headers: authHeaders(),
      })
      const d = await res.json()
      if (d.assessment) setAssessment(d.assessment)
    } catch {}
    finally { setRunning(false) }
  }

  if (loading) return <div className="text-zinc-500 text-sm">Loading assessment…</div>

  const a = assessment ?? MOCK_ASSESSMENT
  const decision = a.launch_decision as string
  const style = DECISION_STYLES[decision] ?? DECISION_STYLES.BLOCKED
  const complianceScore = Math.max(0, 100 - a.overall_score)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Link href="/ticketing/events" className="hover:text-zinc-300">Events</Link>
            <span>/</span>
            <Link href={`/ticketing/events/${id}`} className="hover:text-zinc-300">Event</Link>
            <span>/</span>
            <span>Risk Assessment</span>
          </div>
          <h1 className="text-2xl font-bold">Risk Assessment</h1>
        </div>
        <button
          onClick={runAssessment}
          disabled={running}
          className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
        >
          {running ? 'Running…' : 'Re-run Assessment'}
        </button>
      </div>

      {/* Launch decision card */}
      <div className={`border ${style.border} ${style.bg} rounded-lg p-6`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-zinc-500 mb-1">Launch Decision</div>
            <div className={`text-2xl font-bold ${style.text}`}>{style.label}</div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold">{complianceScore}<span className="text-zinc-500 text-lg">/100</span></div>
            <div className="text-xs text-zinc-500">Compliance Score</div>
          </div>
        </div>
        {a.blocking_reasons?.length > 0 && (
          <div className="mt-4 space-y-1">
            {a.blocking_reasons.map((r: string, i: number) => (
              <div key={i} className="text-sm text-red-300 flex items-start gap-2">
                <span className="text-red-500 mt-0.5 shrink-0">✕</span>{r}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Dimension scores */}
      <div className="border border-zinc-800 rounded-lg p-6 space-y-5">
        <div className="text-sm font-semibold text-zinc-300">Risk Dimensions</div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-4">
          {Object.entries(DIMENSION_LABELS).map(([dim, label]) => (
            <ScoreBar key={dim} dim={dim} label={label} score={a.dimensions?.[dim] ?? 0} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* High-risk triggers */}
        {a.high_risk_triggers?.length > 0 && (
          <div className="border border-yellow-900 rounded-lg p-5">
            <div className="text-sm font-semibold text-yellow-400 mb-3">High-Risk Triggers</div>
            <ul className="space-y-2">
              {a.high_risk_triggers.map((t: string, i: number) => (
                <li key={i} className="text-sm text-yellow-200 flex items-start gap-2">
                  <span className="text-yellow-500 mt-0.5 shrink-0">⚠</span>{t}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Recommendations */}
        {a.recommendations?.length > 0 && (
          <div className="border border-zinc-800 rounded-lg p-5">
            <div className="text-sm font-semibold text-zinc-300 mb-3">Recommendations</div>
            <ol className="space-y-2">
              {a.recommendations.map((r: string, i: number) => (
                <li key={i} className="text-sm text-zinc-400 flex items-start gap-2">
                  <span className="text-zinc-600 mt-0.5 shrink-0">{i + 1}.</span>{r}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {/* Missing controls */}
      {a.missing_controls?.length > 0 && (
        <div className="border border-zinc-800 rounded-lg p-5">
          <div className="text-sm font-semibold text-zinc-300 mb-3">Missing Controls ({a.missing_controls.length})</div>
          <div className="flex flex-wrap gap-2">
            {a.missing_controls.map((c: string, i: number) => (
              <span key={i} className="px-2.5 py-1 bg-zinc-800 border border-zinc-700 rounded-full text-xs text-zinc-300">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <Link href={`/ticketing/events/${id}/checklist`} className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white">
          View Checklist →
        </Link>
        <Link href={`/ticketing/reports?event_id=${id}`} className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Generate Report
        </Link>
        <Link href="/ticketing/ai-copilot" className="px-4 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900">
          Ask AI Copilot
        </Link>
      </div>
    </div>
  )
}
