'use client'

import { useState, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Module = 'copilot' | 'kyc' | 'monitoring' | 'governance' | 'regulatory' | 'evidence' | 'graph' | 'crawler'

function authHeaders(token: string | null): HeadersInit {
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

export default function Home() {
  // ── Auth state ─────────────────────────────────────────────────────────────
  const [token, setToken] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('cos_token')
    if (stored) {
      setToken(stored)
      setIsLoggedIn(true)
    }
  }, [])

  async function login() {
    if (!loginEmail.trim() || !loginPassword.trim()) return
    setLoginLoading(true)
    setLoginError(null)
    try {
      const body = new URLSearchParams({
        username: loginEmail,
        password: loginPassword,
        grant_type: 'password',
      })
      const res = await fetch(`${API_URL}/api/v1/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const t: string = data.access_token
      localStorage.setItem('cos_token', t)
      setToken(t)
      setIsLoggedIn(true)
    } catch (e: any) {
      setLoginError(e.message)
    } finally {
      setLoginLoading(false)
    }
  }

  function logout() {
    localStorage.removeItem('cos_token')
    setToken(null)
    setIsLoggedIn(false)
    setLoginEmail('')
    setLoginPassword('')
  }

  // ── Module state ───────────────────────────────────────────────────────────
  const [active, setActive] = useState<Module>('copilot')

  // ── Copilot state ──────────────────────────────────────────────────────────
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function ask() {
    if (!question.trim()) return
    setLoading(true)
    setResponse(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/copilot/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ question, deep_mode: false }),
      })
      const data = await res.json()
      setResponse(data)
    } catch (e: any) {
      setResponse({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  // ── Evidence state ─────────────────────────────────────────────────────────
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null)
  const [evidenceRegulator, setEvidenceRegulator] = useState('')
  const [evidenceCountry, setEvidenceCountry] = useState('')
  const [evidenceResult, setEvidenceResult] = useState<any>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceDocs, setEvidenceDocs] = useState<any[]>([])
  const [evidenceDocsLoading, setEvidenceDocsLoading] = useState(false)

  useEffect(() => {
    if (active === 'evidence') {
      fetchEvidenceDocs()
    }
  }, [active])

  async function fetchEvidenceDocs() {
    setEvidenceDocsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/evidence/documents`, {
        headers: authHeaders(token),
      })
      const data = await res.json()
      setEvidenceDocs(Array.isArray(data) ? data : data.documents || [])
    } catch {
      setEvidenceDocs([])
    } finally {
      setEvidenceDocsLoading(false)
    }
  }

  async function extractEvidence() {
    if (!evidenceFile) return
    setEvidenceLoading(true)
    setEvidenceResult(null)
    try {
      const form = new FormData()
      form.append('file', evidenceFile)
      const params = new URLSearchParams()
      if (evidenceRegulator.trim()) params.set('regulator_hint', evidenceRegulator.trim())
      if (evidenceCountry.trim()) params.set('country_hint', evidenceCountry.trim())
      const url = `${API_URL}/api/v1/evidence/extract${params.toString() ? '?' + params.toString() : ''}`
      const res = await fetch(url, {
        method: 'POST',
        headers: authHeaders(token),
        body: form,
      })
      const data = await res.json()
      setEvidenceResult(data)
      fetchEvidenceDocs()
    } catch (e: any) {
      setEvidenceResult({ error: e.message })
    } finally {
      setEvidenceLoading(false)
    }
  }

  // ── Graph state ────────────────────────────────────────────────────────────
  const [graphStats, setGraphStats] = useState<any>(null)
  const [graphStatsLoading, setGraphStatsLoading] = useState(false)
  const [graphRegId, setGraphRegId] = useState('')
  const [graphRegData, setGraphRegData] = useState<any>(null)
  const [graphRegLoading, setGraphRegLoading] = useState(false)

  useEffect(() => {
    if (active === 'graph') {
      fetchGraphStats()
    }
  }, [active])

  async function fetchGraphStats() {
    setGraphStatsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/graph/stats`, {
        headers: authHeaders(token),
      })
      const data = await res.json()
      setGraphStats(data)
    } catch (e: any) {
      setGraphStats({ error: e.message })
    } finally {
      setGraphStatsLoading(false)
    }
  }

  async function fetchGraphRegulation() {
    if (!graphRegId.trim()) return
    setGraphRegLoading(true)
    setGraphRegData(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/graph/regulation/${encodeURIComponent(graphRegId.trim())}`, {
        headers: authHeaders(token),
      })
      const data = await res.json()
      setGraphRegData(data)
    } catch (e: any) {
      setGraphRegData({ error: e.message })
    } finally {
      setGraphRegLoading(false)
    }
  }

  // ── Crawler state ──────────────────────────────────────────────────────────
  const [crawlerStatus, setCrawlerStatus] = useState<any>(null)
  const [crawlerStatusLoading, setCrawlerStatusLoading] = useState(false)
  const [crawlerRegulator, setCrawlerRegulator] = useState('all')
  const [crawlerRunResult, setCrawlerRunResult] = useState<any>(null)
  const [crawlerRunLoading, setCrawlerRunLoading] = useState(false)

  useEffect(() => {
    if (active === 'crawler') {
      fetchCrawlerStatus()
    }
  }, [active])

  async function fetchCrawlerStatus() {
    setCrawlerStatusLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/crawler/status`, {
        headers: authHeaders(token),
      })
      const data = await res.json()
      setCrawlerStatus(data)
    } catch (e: any) {
      setCrawlerStatus({ error: e.message })
    } finally {
      setCrawlerStatusLoading(false)
    }
  }

  async function runCrawler() {
    setCrawlerRunLoading(true)
    setCrawlerRunResult(null)
    try {
      const params = new URLSearchParams()
      if (crawlerRegulator !== 'all') params.set('regulator', crawlerRegulator)
      const url = `${API_URL}/api/v1/crawler/run-now${params.toString() ? '?' + params.toString() : ''}`
      const res = await fetch(url, {
        method: 'POST',
        headers: authHeaders(token),
      })
      const data = await res.json()
      setCrawlerRunResult(data)
    } catch (e: any) {
      setCrawlerRunResult({ error: e.message })
    } finally {
      setCrawlerRunLoading(false)
    }
  }

  // ── Login screen ───────────────────────────────────────────────────────────
  if (!isLoggedIn) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold tracking-tight">ComplianceOS</h1>
            <p className="text-sm text-zinc-500 mt-1">AI-native compliance for LATAM regulated industries</p>
          </div>
          <div className="border border-zinc-800 rounded-md p-6 space-y-4">
            <div>
              <label className="text-xs text-zinc-500 block mb-1">Email</label>
              <input
                type="email"
                value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && login()}
                className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                placeholder="admin@polkorp.com"
              />
            </div>
            <div>
              <label className="text-xs text-zinc-500 block mb-1">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && login()}
                className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                placeholder="••••••••"
              />
            </div>
            {loginError && (
              <div className="p-3 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                {loginError}
              </div>
            )}
            <button
              onClick={login}
              disabled={loginLoading}
              className="w-full py-2.5 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
            >
              {loginLoading ? 'Signing in...' : 'Sign in'}
            </button>
            <p className="text-xs text-zinc-600 text-center">
              Dev fallback: <span className="font-mono text-zinc-500">X-Tenant-Id: polkorp</span> still active
            </p>
          </div>
        </div>
      </main>
    )
  }

  // ── Main app ───────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen">
      <header className="border-b border-zinc-800 px-8 py-5">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">ComplianceOS</h1>
            <p className="text-sm text-zinc-500">AI-native compliance for LATAM regulated industries</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-xs text-zinc-500">
              tenant: <span className="text-zinc-300 font-mono">polkorp</span>
            </div>
            <button
              onClick={logout}
              className="px-3 py-1.5 border border-zinc-800 rounded-md text-xs hover:bg-zinc-900 text-zinc-400"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-8 grid grid-cols-12 gap-8">
        <aside className="col-span-3">
          <h2 className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Modules</h2>
          <nav className="space-y-1">
            {[
              { id: 'regulatory', label: 'M1 — Regulatory Intel', desc: 'Parse + map regulations' },
              { id: 'copilot', label: 'M2 — Compliance Copilot', desc: 'Multi-jurisdiction Q&A' },
              { id: 'kyc', label: 'M3 — KYC/AML', desc: 'Screening + EDD' },
              { id: 'monitoring', label: 'M4 — Monitoring', desc: 'Anomalies + drift' },
              { id: 'governance', label: 'M5 — AI Governance', desc: 'Audit + safety' },
              { id: 'evidence', label: 'M6 — Evidence', desc: 'PDF extraction + custody chain' },
              { id: 'graph', label: 'Graph', desc: 'Compliance relationship graph' },
              { id: 'crawler', label: 'Crawler', desc: 'BCRA + UIF live feed' },
            ].map(m => (
              <button
                key={m.id}
                onClick={() => setActive(m.id as Module)}
                className={`w-full text-left p-3 rounded-md transition ${
                  active === m.id
                    ? 'bg-zinc-800 border border-zinc-700'
                    : 'hover:bg-zinc-900'
                }`}
              >
                <div className="text-sm font-medium">{m.label}</div>
                <div className="text-xs text-zinc-500">{m.desc}</div>
              </button>
            ))}
          </nav>
        </aside>

        <section className="col-span-9">
          {/* ── Copilot ─────────────────────────────────────────────────────── */}
          {active === 'copilot' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Compliance Copilot</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Ask any regulatory or compliance question. Powered by Kimi-K2 + fallbacks (NVIDIA NIM).
              </p>

              <div className="space-y-4">
                <textarea
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="¿Qué cambia regulatoriamente si opero como PSP en Perú vs Argentina?"
                  className="w-full p-4 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono min-h-32 focus:outline-none focus:border-zinc-600"
                />

                <div className="flex gap-3">
                  <button
                    onClick={ask}
                    disabled={loading}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    {loading ? 'Analyzing...' : 'Ask Copilot'}
                  </button>
                  <button
                    onClick={() => { setQuestion(''); setResponse(null) }}
                    className="px-5 py-2 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900"
                  >
                    Clear
                  </button>
                </div>

                {response && (
                  <div className="mt-6 space-y-3">
                    {response.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {response.error}
                      </div>
                    )}
                    {response.success && (
                      <>
                        <div className="flex gap-4 text-xs text-zinc-500">
                          <span>model: <span className="font-mono text-zinc-300">{response.model_used}</span></span>
                          <span>latency: <span className="font-mono text-zinc-300">{response.latency_ms}ms</span></span>
                          <span>audit: <span className="font-mono text-zinc-300">{response.audit_id}</span></span>
                        </div>
                        <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md text-sm whitespace-pre-wrap">
                          {typeof response.answer === 'string' ? response.answer : JSON.stringify(response.answer, null, 2)}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Evidence ────────────────────────────────────────────────────── */}
          {active === 'evidence' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">M6 — Evidence Automation</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Extract structured obligations from regulator PDFs. Custody hash logged on every extraction.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-zinc-500 block mb-1">PDF Document</label>
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={e => setEvidenceFile(e.target.files?.[0] || null)}
                    className="w-full text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:bg-zinc-800 file:text-zinc-200 hover:file:bg-zinc-700"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Regulator hint (optional)</label>
                    <input
                      type="text"
                      value={evidenceRegulator}
                      onChange={e => setEvidenceRegulator(e.target.value)}
                      placeholder="e.g. BCRA, UIF, BACEN"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Country hint (optional)</label>
                    <input
                      type="text"
                      value={evidenceCountry}
                      onChange={e => setEvidenceCountry(e.target.value)}
                      placeholder="e.g. AR, BR, PE"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                </div>

                <button
                  onClick={extractEvidence}
                  disabled={evidenceLoading || !evidenceFile}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {evidenceLoading ? 'Extracting...' : 'Extract Obligations'}
                </button>

                {evidenceResult && (
                  <div className="mt-4 space-y-3">
                    {evidenceResult.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {evidenceResult.error}
                      </div>
                    )}
                    {!evidenceResult.error && (
                      <div className="space-y-3">
                        <div className="flex gap-6 text-xs text-zinc-500">
                          <span>confidence: <span className="font-mono text-zinc-300">{evidenceResult.extraction_confidence ?? '—'}</span></span>
                          <span>obligations: <span className="font-mono text-zinc-300">{evidenceResult.obligations_count ?? (evidenceResult.structured_data?.obligations?.length ?? '—')}</span></span>
                          <span>custody hash: <span className="font-mono text-zinc-300 truncate max-w-xs inline-block align-bottom">{evidenceResult.custody_hash ?? '—'}</span></span>
                        </div>
                        {Array.isArray(evidenceResult.structured_data?.obligations) && evidenceResult.structured_data.obligations.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-2">Obligations extracted</div>
                            <div className="space-y-1.5">
                              {evidenceResult.structured_data.obligations.map((ob: any, i: number) => (
                                <div key={i} className="p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm">
                                  {typeof ob === 'string' ? ob : JSON.stringify(ob)}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Previous documents table */}
              <div className="mt-10">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-zinc-300">Previous Documents</h3>
                  <button
                    onClick={fetchEvidenceDocs}
                    disabled={evidenceDocsLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {evidenceDocsLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
                {evidenceDocs.length === 0 ? (
                  <div className="text-sm text-zinc-600 border border-dashed border-zinc-800 rounded-md p-6 text-center">
                    No documents yet.
                  </div>
                ) : (
                  <div className="border border-zinc-800 rounded-md overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-800 bg-zinc-900">
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">File</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Regulator</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Country</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Obligations</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Extracted</th>
                        </tr>
                      </thead>
                      <tbody>
                        {evidenceDocs.map((doc: any, i: number) => (
                          <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                            <td className="px-4 py-2.5 font-mono text-xs text-zinc-300">{doc.filename ?? doc.file_name ?? doc.id ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs">{doc.regulator ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs">{doc.country ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs">{doc.obligations_count ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-zinc-500">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Graph ────────────────────────────────────────────────────────── */}
          {active === 'graph' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Compliance Graph</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Regulations, obligations, entities, and controls modeled as a relationship graph.
              </p>

              {graphStatsLoading && (
                <div className="text-sm text-zinc-500">Loading stats...</div>
              )}

              {graphStats && !graphStats.error && (
                <div className="space-y-6">
                  <div>
                    <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Vertex counts</div>
                    <div className="grid grid-cols-5 gap-3">
                      {(['regulation', 'obligation', 'entity', 'control', 'regulator'] as const).map(type => (
                        <div key={type} className="p-4 bg-zinc-900 border border-zinc-800 rounded-md text-center">
                          <div className="text-xl font-mono font-semibold">
                            {graphStats.vertex_counts?.[type] ?? graphStats.vertices?.[type] ?? '—'}
                          </div>
                          <div className="text-xs text-zinc-500 mt-1 capitalize">{type}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Edge counts</div>
                    <div className="grid grid-cols-5 gap-3">
                      {(['REQUIRES', 'APPLIES_TO', 'SATISFIES', 'ISSUED_BY', 'CROSS_REFERENCES'] as const).map(type => (
                        <div key={type} className="p-4 bg-zinc-900 border border-zinc-800 rounded-md text-center">
                          <div className="text-xl font-mono font-semibold">
                            {graphStats.edge_counts?.[type] ?? graphStats.edges?.[type] ?? '—'}
                          </div>
                          <div className="text-xs text-zinc-500 mt-1 font-mono">{type}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {graphStats?.error && (
                <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200 mb-6">
                  Error: {graphStats.error}
                </div>
              )}

              {/* Regulation lookup */}
              <div className="mt-8 space-y-3">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Regulation lookup</div>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={graphRegId}
                    onChange={e => setGraphRegId(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && fetchGraphRegulation()}
                    placeholder="Regulation ID"
                    className="flex-1 p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                  />
                  <button
                    onClick={fetchGraphRegulation}
                    disabled={graphRegLoading || !graphRegId.trim()}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    {graphRegLoading ? 'Fetching...' : 'Lookup'}
                  </button>
                </div>

                {graphRegData && (
                  <div className="space-y-3">
                    {graphRegData.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {graphRegData.error}
                      </div>
                    )}
                    {!graphRegData.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex gap-6 text-xs text-zinc-500">
                          <span>vertices: <span className="font-mono text-zinc-300">{graphRegData.vertex_count ?? '—'}</span></span>
                          <span>edges: <span className="font-mono text-zinc-300">{graphRegData.edge_count ?? '—'}</span></span>
                        </div>
                        {Array.isArray(graphRegData.obligations) && graphRegData.obligations.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-2">Obligation vertices</div>
                            <div className="space-y-1">
                              {graphRegData.obligations.map((ob: any, i: number) => (
                                <div key={i} className="text-sm font-mono text-zinc-300 px-2 py-1 bg-zinc-800 rounded">
                                  {typeof ob === 'string' ? ob : ob.label ?? JSON.stringify(ob)}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Crawler ──────────────────────────────────────────────────────── */}
          {active === 'crawler' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Regulatory Crawler</h2>
              <p className="text-sm text-zinc-500 mb-6">
                BCRA + UIF live feed. Fetches new regulations, parses with M1, stores in DB + Qdrant.
              </p>

              {crawlerStatusLoading && (
                <div className="text-sm text-zinc-500">Loading status...</div>
              )}

              {crawlerStatus && !crawlerStatus.error && (
                <div className="grid grid-cols-3 gap-4 mb-8">
                  <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                    <div className="text-xs text-zinc-500 mb-1">Status</div>
                    <div className={`text-sm font-medium ${crawlerStatus.enabled ? 'text-green-400' : 'text-zinc-400'}`}>
                      {crawlerStatus.enabled ? 'Enabled' : 'Disabled'}
                    </div>
                  </div>
                  <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                    <div className="text-xs text-zinc-500 mb-1">BCRA schedule</div>
                    <div className="text-sm font-mono text-zinc-300">{crawlerStatus.bcra_schedule ?? crawlerStatus.schedules?.BCRA ?? '6h'}</div>
                  </div>
                  <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                    <div className="text-xs text-zinc-500 mb-1">UIF schedule</div>
                    <div className="text-sm font-mono text-zinc-300">{crawlerStatus.uif_schedule ?? crawlerStatus.schedules?.UIF ?? '12h'}</div>
                  </div>
                </div>
              )}

              {crawlerStatus?.error && (
                <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200 mb-6">
                  Error: {crawlerStatus.error}
                </div>
              )}

              <div className="space-y-3">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Run now</div>
                <div className="flex gap-3 items-center">
                  <select
                    value={crawlerRegulator}
                    onChange={e => setCrawlerRegulator(e.target.value)}
                    className="p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                  >
                    <option value="all">All regulators</option>
                    <option value="BCRA">BCRA</option>
                    <option value="UIF">UIF</option>
                  </select>
                  <button
                    onClick={runCrawler}
                    disabled={crawlerRunLoading}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    {crawlerRunLoading ? 'Running...' : 'Run now'}
                  </button>
                  <span className="text-xs text-zinc-600">Requires admin token</span>
                </div>

                {crawlerRunResult && (
                  <div className="mt-2">
                    {crawlerRunResult.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {crawlerRunResult.error}
                      </div>
                    )}
                    {!crawlerRunResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                        <div className="flex gap-6 text-xs text-zinc-500">
                          <span>crawled: <span className="font-mono text-zinc-300">{crawlerRunResult.crawled ?? '—'}</span></span>
                          <span>skipped: <span className="font-mono text-zinc-300">{crawlerRunResult.skipped ?? '—'}</span></span>
                          <span>errors: <span className="font-mono text-zinc-300">{crawlerRunResult.errors ?? '—'}</span></span>
                        </div>
                        {crawlerRunResult.message && (
                          <div className="mt-2 text-sm text-zinc-400">{crawlerRunResult.message}</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Other modules (placeholder) ───────────────────────────────── */}
          {active !== 'copilot' && active !== 'evidence' && active !== 'graph' && active !== 'crawler' && (
            <div className="p-12 text-center text-zinc-500 border border-dashed border-zinc-800 rounded-md">
              Module <span className="font-mono text-zinc-300">{active}</span> UI coming soon.
              <br />
              <span className="text-xs">API endpoints already live at <code className="text-zinc-400">/api/v1/{active}/*</code></span>
              <br />
              <a href={`${API_URL}/docs`} target="_blank" className="text-zinc-300 underline mt-3 inline-block">
                See API docs →
              </a>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
