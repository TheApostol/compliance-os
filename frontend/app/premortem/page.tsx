'use client'

import { useState, useEffect } from 'react'
import { Badge, Card, StatusPill, variantForLevel } from '../components/ui'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const CATEGORIES = ['all', 'ai_reliability', 'data_isolation', 'crawler', 'audit'] as const
type Category = typeof CATEGORIES[number]

interface FailureMode {
  id: string
  scenario: string
  description: string
  impact: string
  likelihood: string
  severity: string
  category: string
  affected_modules: string[]
  status: string
  created_at: string
  updated_at: string
}

interface Finding {
  id: string
  title: string
  description: string
  finding_type: string
  priority: string
  related_failure_modes: string[]
  status: string
  created_at: string
}

interface Summary {
  total_failure_modes: number
  severity_distribution: Record<'critical' | 'high' | 'medium' | 'low', number>
  status_distribution: Record<'identified' | 'mitigated' | 'resolved' | 'monitoring', number>
  total_findings: number
  findings_by_priority: Record<'critical' | 'high' | 'medium' | 'low', number>
}

function authHeaders(token: string | null): HeadersInit {
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

export default function PremortemPage() {
  const [token, setToken] = useState<string | null>(null)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [modes, setModes] = useState<FailureMode[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [category, setCategory] = useState<Category>('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedMode, setSelectedMode] = useState<FailureMode | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem('cos_token')
    if (stored) setToken(stored)
  }, [])

  useEffect(() => {
    if (token === null) return
    load()
  }, [token, category])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const headers = authHeaders(token)
      const modesUrl = category === 'all'
        ? `${API_URL}/api/v1/premortem/failure-modes`
        : `${API_URL}/api/v1/premortem/failure-modes?category=${category}`

      const [summaryRes, modesRes, findingsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/premortem/summary`, { headers }),
        fetch(modesUrl, { headers }),
        fetch(`${API_URL}/api/v1/premortem/findings`, { headers }),
      ])

      if (!summaryRes.ok || !modesRes.ok || !findingsRes.ok) {
        throw new Error(`HTTP ${summaryRes.status}/${modesRes.status}/${findingsRes.status}`)
      }

      const [summaryData, modesData, findingsData] = await Promise.all([
        summaryRes.json(), modesRes.json(), findingsRes.json(),
      ])

      setSummary(summaryData)
      setModes(modesData.failure_modes || [])
      setFindings(findingsData.findings || [])
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const statusVariant = (status: string) =>
    status === 'resolved' ? 'success' : status === 'mitigated' ? 'low' : status === 'monitoring' ? 'medium' : 'neutral'

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-4 md:p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <button onClick={() => { window.location.href = '/' }} className="text-xs text-zinc-500 hover:text-zinc-300 underline mb-2">
            ← Back to Console
          </button>
          <h1 className="text-xl font-bold">Premortem Analysis</h1>
          <p className="text-sm text-zinc-500">Failure-mode tracking and mitigation status</p>
        </div>
        <StatusPill active={!error && !loading} activeLabel="Live" inactiveLabel={loading ? 'Loading...' : 'Error'} />
      </div>

      {error && (
        <Card className="border-red-900 bg-red-950/30 text-sm text-red-300 mb-6">
          Failed to load premortem data: {error}
        </Card>
      )}

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8">
          <Card>
            <div className="text-2xl md:text-3xl font-mono font-bold mb-1">{summary.total_failure_modes}</div>
            <div className="text-xs text-zinc-500">Total Failure Modes</div>
          </Card>
          <Card>
            <div className="text-2xl md:text-3xl font-mono font-bold mb-1 text-red-400">{summary.severity_distribution.critical}</div>
            <div className="text-xs text-zinc-500">Critical</div>
          </Card>
          <Card>
            <div className="text-2xl md:text-3xl font-mono font-bold mb-1 text-green-400">{summary.status_distribution.resolved}</div>
            <div className="text-xs text-zinc-500">Resolved</div>
          </Card>
          <Card>
            <div className="text-2xl md:text-3xl font-mono font-bold mb-1 text-zinc-300">{summary.total_findings}</div>
            <div className="text-xs text-zinc-500">Findings</div>
          </Card>
        </div>
      )}

      {summary && (
        <Card className="mb-8">
          <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Severity Distribution</div>
          <div className="flex h-3 rounded overflow-hidden bg-zinc-900">
            {(['critical', 'high', 'medium', 'low'] as const).map(level => {
              const count = summary.severity_distribution[level]
              const pct = summary.total_failure_modes > 0 ? (count / summary.total_failure_modes) * 100 : 0
              const bar = {
                critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-yellow-500', low: 'bg-green-500',
              }[level]
              return pct > 0 ? <div key={level} className={bar} style={{ width: `${pct}%` }} title={`${level}: ${count}`} /> : null
            })}
          </div>
          <div className="flex gap-4 mt-3 text-xs text-zinc-500">
            {(['critical', 'high', 'medium', 'low'] as const).map(level => (
              <div key={level} className="flex items-center gap-1.5">
                <Badge variant={variantForLevel(level)} size="sm">{level}</Badge>
                <span>{summary.severity_distribution[level]}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="flex gap-2 mb-4 flex-wrap">
        {CATEGORIES.map(c => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`text-xs px-3 py-1.5 rounded border ${
              category === c
                ? 'border-zinc-500 bg-zinc-800 text-zinc-100'
                : 'border-zinc-800 text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {c.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <Card className="mb-8 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-zinc-500 border-b border-zinc-800">
              <th className="py-2 pr-4">Scenario</th>
              <th className="py-2 pr-4">Category</th>
              <th className="py-2 pr-4">Severity</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {modes.length === 0 && !loading && (
              <tr><td colSpan={5} className="py-6 text-center text-zinc-600">No failure modes recorded.</td></tr>
            )}
            {modes.map(m => (
              <tr key={m.id} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                <td className="py-2 pr-4 max-w-xs truncate">{m.scenario}</td>
                <td className="py-2 pr-4 text-zinc-500">{m.category}</td>
                <td className="py-2 pr-4"><Badge variant={variantForLevel(m.severity)} size="sm">{m.severity}</Badge></td>
                <td className="py-2 pr-4"><Badge variant={statusVariant(m.status)} size="sm">{m.status}</Badge></td>
                <td className="py-2">
                  <button onClick={() => setSelectedMode(m)} className="text-xs text-zinc-500 hover:text-zinc-300 underline">
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div>
        <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Findings</div>
        <div className="space-y-2">
          {findings.length === 0 && !loading && (
            <Card className="text-sm text-zinc-600">No findings recorded.</Card>
          )}
          {findings.map(f => (
            <Card key={f.id}>
              <div className="flex items-center justify-between mb-1">
                <div className="text-sm font-medium">{f.title}</div>
                <Badge variant={variantForLevel(f.priority)} size="sm">{f.priority}</Badge>
              </div>
              <div className="text-xs text-zinc-500">{f.description}</div>
            </Card>
          ))}
        </div>
      </div>

      {selectedMode && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedMode(null)}
        >
          <Card className="bg-zinc-950 max-w-lg w-full" >
            <div onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-3">
                <div className="text-sm font-medium">{selectedMode.scenario}</div>
                <button onClick={() => setSelectedMode(null)} className="text-zinc-500 hover:text-zinc-300">✕</button>
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Description</div>
                  <div>{selectedMode.description}</div>
                </div>
                <div>
                  <div className="text-xs text-zinc-500 mb-1">Impact</div>
                  <div>{selectedMode.impact}</div>
                </div>
                <div className="flex gap-6">
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">Likelihood</div>
                    <div>{selectedMode.likelihood}</div>
                  </div>
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">Category</div>
                    <div>{selectedMode.category}</div>
                  </div>
                </div>
                {selectedMode.affected_modules.length > 0 && (
                  <div>
                    <div className="text-xs text-zinc-500 mb-1">Affected Modules</div>
                    <div className="flex gap-1.5 flex-wrap">
                      {selectedMode.affected_modules.map(m => (
                        <Badge key={m} variant="neutral" size="sm">{m}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
