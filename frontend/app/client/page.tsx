'use client'

import { useState, useEffect, useCallback } from 'react'

const API_URL = ''

function authHeaders(token: string | null): HeadersInit {
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

function decodeJwtPayload(jwt: string): any {
  try {
    return JSON.parse(atob(jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  } catch { return null }
}

function ScoreRing({ score }: { score: number }) {
  const r = 36
  const circ = 2 * Math.PI * r
  const filled = (score / 100) * circ
  const color = score >= 75 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444'
  const label = score >= 75 ? 'GOOD' : score >= 50 ? 'FAIR' : 'RISK'
  return (
    <div className="flex flex-col items-center justify-center gap-1">
      <svg width="96" height="96" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={r} fill="none" stroke="#27272a" strokeWidth="8" />
        <circle
          cx="48" cy="48" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${filled} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
        />
        <text x="48" y="44" textAnchor="middle" fill="white" fontSize="18" fontWeight="bold">{score}</text>
        <text x="48" y="58" textAnchor="middle" fill={color} fontSize="9" fontWeight="600">{label}</text>
      </svg>
    </div>
  )
}

export default function ClientDashboard() {
  const [token, setToken] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)
  const [tenantInfo, setTenantInfo] = useState<{ vertical?: string; name?: string } | null>(null)

  // Dashboard data
  const [score, setScore] = useState<number | null>(null)
  const [scoreLoading, setScoreLoading] = useState(false)
  const [alerts, setAlerts] = useState<any[]>([])
  const [alertsLoading, setAlertsLoading] = useState(false)
  const [workflows, setWorkflows] = useState<any[]>([])
  const [workflowsLoading, setWorkflowsLoading] = useState(false)
  const [obligations, setObligations] = useState<any[]>([])
  const [obligationsLoading, setObligationsLoading] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem('cos_client_token')
    if (stored) {
      setToken(stored)
      setIsLoggedIn(true)
      const claims = decodeJwtPayload(stored)
      if (claims) setTenantInfo({ name: claims.tenant_id, vertical: claims.vertical })
    }
  }, [])

  const loadDashboard = useCallback(async (t: string) => {
    setScoreLoading(true)
    setAlertsLoading(true)
    setWorkflowsLoading(true)
    setObligationsLoading(true)
    setLastRefresh(new Date())

    const headers = authHeaders(t)

    fetch(`${API_URL}/api/v1/compliance/scores`, { headers })
      .then(r => r.json())
      .then(d => {
        const list = Array.isArray(d.scores) ? d.scores : []
        const avg = list.length
          ? Math.round(list.reduce((s: number, e: any) => s + (e.score ?? 0), 0) / list.length)
          : null
        setScore(avg)
      })
      .catch(() => setScore(null))
      .finally(() => setScoreLoading(false))

    fetch(`${API_URL}/api/v1/alerts?acknowledged=false`, { headers })
      .then(r => r.json())
      .then(d => setAlerts(Array.isArray(d) ? d : (d.alerts ?? [])))
      .catch(() => setAlerts([]))
      .finally(() => setAlertsLoading(false))

    fetch(`${API_URL}/api/v1/workflow/`, { headers })
      .then(r => r.json())
      .then(d => setWorkflows(Array.isArray(d) ? d : []))
      .catch(() => setWorkflows([]))
      .finally(() => setWorkflowsLoading(false))

    // Use the obligation list from the regulatory module
    fetch(`${API_URL}/api/v1/regulatory/obligations?limit=20`, { headers })
      .then(r => r.json())
      .then(d => setObligations(Array.isArray(d) ? d : (d.obligations ?? [])))
      .catch(() => setObligations([]))
      .finally(() => setObligationsLoading(false))
  }, [])

  useEffect(() => {
    if (!isLoggedIn || !token) return
    loadDashboard(token)
    const interval = setInterval(() => loadDashboard(token), 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [isLoggedIn, token, loadDashboard])

  async function login() {
    if (!loginEmail.trim() || !loginPassword.trim()) return
    setLoginLoading(true)
    setLoginError(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: loginEmail, password: loginPassword, grant_type: 'password' }).toString(),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const t: string = data.access_token
      localStorage.setItem('cos_client_token', t)
      setToken(t)
      setIsLoggedIn(true)
      const claims = decodeJwtPayload(t)
      if (claims) setTenantInfo({ name: claims.tenant_id, vertical: claims.vertical })
    } catch (e: any) {
      setLoginError(e.message)
    } finally {
      setLoginLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('cos_client_token')
    setToken(null)
    setIsLoggedIn(false)
    setTenantInfo(null)
  }

  // ── Login screen ────────────────────────────────────────────────────────────
  if (!isLoggedIn) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-black">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <div className="text-3xl mb-2">🛡</div>
            <h1 className="text-2xl font-bold tracking-tight">ComplianceOS</h1>
            <p className="text-sm text-zinc-500 mt-1">Client compliance portal</p>
          </div>
          <div className="border border-zinc-800 rounded-xl p-6 space-y-4">
            <div>
              <label className="text-xs text-zinc-500 block mb-1">Email</label>
              <input
                type="email"
                value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && login()}
                className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-sm focus:outline-none focus:border-zinc-600"
                placeholder="you@company.com"
                autoComplete="email"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && login()}
                className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-sm focus:outline-none focus:border-zinc-600"
                placeholder="••••••••"
                autoComplete="current-password"
              />
            </div>
            {loginError && (
              <div className="p-3 bg-red-950 border border-red-900 rounded-lg text-sm text-red-200">
                {loginError}
              </div>
            )}
            <button
              onClick={login}
              disabled={loginLoading}
              className="w-full py-2.5 bg-zinc-100 text-zinc-900 rounded-lg text-sm font-medium hover:bg-white disabled:opacity-50"
            >
              {loginLoading ? 'Signing in…' : 'Sign in'}
            </button>
          </div>
          <p className="mt-6 text-center text-xs text-zinc-600">
            Admin access? <a href="/" className="text-zinc-400 hover:text-zinc-200 underline">Go to operator console</a>
          </p>
        </div>
      </main>
    )
  }

  // ── Dashboard ────────────────────────────────────────────────────────────────
  const criticalAlerts = alerts.filter(a => (a.severity ?? '').toUpperCase() === 'CRITICAL' || (a.severity ?? '').toUpperCase() === 'HIGH')
  const activeWorkflows = workflows.filter(w => !['completed', 'cancelled'].includes(w.status ?? ''))
  const nowStr = lastRefresh ? lastRefresh.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '—'

  return (
    <main className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight">ComplianceOS</span>
          <span className="text-xs text-zinc-600">|</span>
          <span className="text-sm text-zinc-400">Client Portal</span>
          {tenantInfo?.vertical && (
            <span className="px-2 py-0.5 text-xs border border-zinc-700 rounded text-zinc-400">
              {tenantInfo.vertical}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-zinc-600">Refreshed {nowStr}</span>
          <button
            onClick={() => token && loadDashboard(token)}
            className="text-xs text-zinc-400 hover:text-zinc-200 border border-zinc-800 rounded px-3 py-1.5"
          >
            Refresh
          </button>
          <button onClick={logout} className="text-xs text-zinc-600 hover:text-zinc-400">
            Sign out
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">

        {/* Row 1 — KPI cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Compliance Score */}
          <div className="border border-zinc-800 rounded-xl p-6 flex items-center gap-5">
            {scoreLoading ? (
              <div className="w-24 h-24 bg-zinc-800 rounded-full animate-pulse" />
            ) : score !== null ? (
              <ScoreRing score={score} />
            ) : (
              <div className="w-24 h-24 flex items-center justify-center text-zinc-600 text-xs">No data</div>
            )}
            <div>
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Compliance Score</div>
              <div className="text-2xl font-bold">{score !== null ? `${score}/100` : '—'}</div>
              <div className="text-xs text-zinc-500 mt-1">Avg across all entities</div>
            </div>
          </div>

          {/* Critical Alerts */}
          <div className="border border-zinc-800 rounded-xl p-6">
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Critical Alerts</div>
            {alertsLoading ? (
              <div className="h-8 bg-zinc-800 rounded animate-pulse" />
            ) : (
              <>
                <div className={`text-3xl font-bold ${criticalAlerts.length > 0 ? 'text-red-400' : 'text-green-400'}`}>
                  {criticalAlerts.length}
                </div>
                <div className="text-xs text-zinc-500 mt-1">
                  {criticalAlerts.length === 0
                    ? 'No critical issues'
                    : `${criticalAlerts.length} need${criticalAlerts.length === 1 ? 's' : ''} attention`}
                </div>
              </>
            )}
          </div>

          {/* Active Workflows */}
          <div className="border border-zinc-800 rounded-xl p-6">
            <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Active Remediations</div>
            {workflowsLoading ? (
              <div className="h-8 bg-zinc-800 rounded animate-pulse" />
            ) : (
              <>
                <div className="text-3xl font-bold text-blue-400">{activeWorkflows.length}</div>
                <div className="text-xs text-zinc-500 mt-1">
                  {activeWorkflows.length === 0 ? 'All clear' : 'workflows in progress'}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Row 2 — Alerts panel */}
        {(criticalAlerts.length > 0 || alertsLoading) && (
          <div className="border border-red-900 bg-red-950/20 rounded-xl p-5">
            <div className="text-xs uppercase tracking-wider text-red-400 mb-3 font-medium">Active Alerts</div>
            {alertsLoading ? (
              <div className="space-y-2">
                {[0, 1].map(i => <div key={i} className="h-4 bg-red-950 rounded animate-pulse" />)}
              </div>
            ) : (
              <div className="space-y-2">
                {criticalAlerts.slice(0, 5).map((a: any, i: number) => (
                  <div key={a.id ?? i} className="flex items-start gap-3 text-sm">
                    <span className={`mt-0.5 px-1.5 py-0.5 text-xs rounded border shrink-0 ${
                      (a.severity ?? '').toUpperCase() === 'CRITICAL'
                        ? 'bg-red-950 text-red-300 border-red-800'
                        : 'bg-amber-950 text-amber-300 border-amber-800'
                    }`}>
                      {a.severity ?? 'HIGH'}
                    </span>
                    <span className="text-zinc-200">{a.title ?? a.alert_type ?? 'Compliance alert'}</span>
                  </div>
                ))}
                <p className="text-xs text-zinc-500 mt-3">
                  Contact your compliance officer to address these items.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Row 3 — Obligations table */}
        <div className="border border-zinc-800 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
            <div className="text-sm font-medium">Active Obligations</div>
            <div className="text-xs text-zinc-500">{obligations.length} items</div>
          </div>
          {obligationsLoading ? (
            <div className="p-5 space-y-3">
              {[0, 1, 2, 3].map(i => (
                <div key={i} className="h-4 bg-zinc-800 rounded animate-pulse" style={{ width: `${70 + i * 8}%` }} />
              ))}
            </div>
          ) : obligations.length === 0 ? (
            <div className="px-5 py-8 text-center text-zinc-600 text-sm">No obligations found.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-950">
                  <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Obligation</th>
                  <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Regulator</th>
                  <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Due Date</th>
                  <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {obligations.slice(0, 15).map((ob: any, i: number) => {
                  const status = ob.status ?? 'pending'
                  const stCls =
                    status === 'compliant' ? 'bg-green-950 text-green-400 border-green-900' :
                    status === 'overdue' ? 'bg-red-950 text-red-400 border-red-900' :
                    status === 'in_progress' ? 'bg-blue-950 text-blue-400 border-blue-900' :
                    'bg-zinc-800 text-zinc-400 border-zinc-700'
                  return (
                    <tr key={ob.id ?? i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                      <td className="px-5 py-3 text-zinc-200 max-w-xs truncate">
                        {ob.title ?? ob.obligation_type ?? ob.name ?? '—'}
                      </td>
                      <td className="px-5 py-3 text-xs text-zinc-500">
                        {ob.regulator ?? ob.country ?? '—'}
                      </td>
                      <td className="px-5 py-3 text-xs text-zinc-400">
                        {ob.due_date ? new Date(ob.due_date).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-5 py-3">
                        <span className={`px-1.5 py-0.5 text-xs rounded border ${stCls}`}>{status}</span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Row 4 — Active workflows */}
        {(activeWorkflows.length > 0 || workflowsLoading) && (
          <div className="border border-zinc-800 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
              <div className="text-sm font-medium">Remediation Workflows</div>
              <div className="text-xs text-zinc-500">{activeWorkflows.length} active</div>
            </div>
            {workflowsLoading ? (
              <div className="p-5 space-y-2">
                {[0, 1, 2].map(i => <div key={i} className="h-4 bg-zinc-800 rounded animate-pulse" />)}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 bg-zinc-950">
                    <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Title</th>
                    <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Severity</th>
                    <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Status</th>
                    <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Steps</th>
                    <th className="text-left px-5 py-3 text-xs text-zinc-500 font-medium">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {activeWorkflows.slice(0, 10).map((w: any, i: number) => {
                    const sev = (w.severity ?? '').toLowerCase()
                    const sevCls =
                      sev === 'critical' ? 'bg-red-950 text-red-400 border-red-900' :
                      sev === 'high' ? 'bg-amber-950 text-amber-400 border-amber-900' :
                      sev === 'medium' ? 'bg-blue-950 text-blue-400 border-blue-900' :
                      'bg-zinc-800 text-zinc-400 border-zinc-700'
                    const st = w.status ?? 'pending'
                    const stCls =
                      st === 'approval_required' ? 'bg-amber-950 text-amber-400 border-amber-900' :
                      st === 'running' ? 'bg-blue-950 text-blue-400 border-blue-900' :
                      'bg-zinc-800 text-zinc-400 border-zinc-700'
                    return (
                      <tr key={w.id ?? w.workflow_id ?? i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                        <td className="px-5 py-3 text-zinc-200 max-w-xs truncate">{w.title ?? '—'}</td>
                        <td className="px-5 py-3">
                          <span className={`px-1.5 py-0.5 text-xs rounded border ${sevCls}`}>{sev || '—'}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`px-1.5 py-0.5 text-xs rounded border ${stCls}`}>{st}</span>
                        </td>
                        <td className="px-5 py-3 text-xs text-zinc-500">{w.step_count ?? '—'}</td>
                        <td className="px-5 py-3 text-xs text-zinc-500">
                          {w.created_at ? new Date(w.created_at).toLocaleDateString() : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Footer CTA */}
        <div className="border border-zinc-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">Need help or found an issue?</div>
            <div className="text-xs text-zinc-500 mt-0.5">Contact your assigned compliance officer for guidance.</div>
          </div>
          <a
            href="mailto:compliance@polkorp.com"
            className="px-4 py-2 text-sm border border-zinc-700 rounded-lg hover:bg-zinc-900"
          >
            Contact compliance
          </a>
        </div>

      </div>
    </main>
  )
}
