'use client'

import { useState, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Module = 'copilot' | 'kyc' | 'monitoring' | 'governance' | 'regulatory' | 'evidence' | 'graph' | 'crawler'

function authHeaders(token: string | null): HeadersInit {
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

function tryParseJSON(str: string): [any, string | null] {
  try { return [JSON.parse(str), null] }
  catch (e: any) { return [null, e.message] }
}

const SEVERITY_COLORS: Record<string, string> = {
  HIGH: 'bg-red-950 text-red-300 border border-red-900',
  MEDIUM: 'bg-yellow-950 text-yellow-300 border border-yellow-900',
  LOW: 'bg-zinc-800 text-zinc-300 border border-zinc-700',
  CRITICAL: 'bg-red-950 text-red-200 border border-red-800',
}

const RISK_COLORS: Record<string, string> = {
  LOW: 'bg-green-950 text-green-300 border border-green-900',
  MEDIUM: 'bg-yellow-950 text-yellow-300 border border-yellow-900',
  HIGH: 'bg-orange-950 text-orange-300 border border-orange-900',
  CRITICAL: 'bg-red-950 text-red-300 border border-red-900',
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
  const [crawlerLastUpdated, setCrawlerLastUpdated] = useState<string | null>(null)
  const [crawlerRegulator, setCrawlerRegulator] = useState('all')
  const [crawlerRunResult, setCrawlerRunResult] = useState<any>(null)
  const [crawlerRunLoading, setCrawlerRunLoading] = useState(false)

  useEffect(() => {
    if (active === 'crawler') {
      fetchCrawlerStatus()
      const interval = setInterval(() => {
        fetchCrawlerStatus()
      }, 30000)
      return () => clearInterval(interval)
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
      const now = new Date()
      setCrawlerLastUpdated(
        now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      )
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

  // ── M1 Regulatory state ────────────────────────────────────────────────────
  const [regCountry, setRegCountry] = useState('AR')
  const [regRegulator, setRegRegulator] = useState('BCRA')
  const [regCode, setRegCode] = useState('Com. A 7825')
  const [regTitle, setRegTitle] = useState('')
  const [regText, setRegText] = useState('')
  const [regParseResult, setRegParseResult] = useState<any>(null)
  const [regParseLoading, setRegParseLoading] = useState(false)

  const [mapTopic, setMapTopic] = useState('Suspicious Activity Reporting')
  const [mapCountries, setMapCountries] = useState('AR,BR,MX')
  const [mapResult, setMapResult] = useState<any>(null)
  const [mapLoading, setMapLoading] = useState(false)

  async function parseRegulation() {
    if (!regText.trim()) return
    setRegParseLoading(true)
    setRegParseResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/regulatory/parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          country: regCountry,
          regulator: regRegulator,
          code: regCode,
          title: regTitle,
          text: regText,
        }),
      })
      const data = await res.json()
      setRegParseResult(data)
    } catch (e: any) {
      setRegParseResult({ error: e.message })
    } finally {
      setRegParseLoading(false)
    }
  }

  async function mapCrossBorder() {
    if (!mapTopic.trim()) return
    setMapLoading(true)
    setMapResult(null)
    try {
      const countries = mapCountries.split(',').map(c => c.trim()).filter(Boolean)
      const res = await fetch(`${API_URL}/api/v1/regulatory/map`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ obligation_topic: mapTopic, countries }),
      })
      const data = await res.json()
      setMapResult(data)
    } catch (e: any) {
      setMapResult({ error: e.message })
    } finally {
      setMapLoading(false)
    }
  }

  // ── M3 KYC/AML state ──────────────────────────────────────────────────────
  const DEFAULT_CUSTOMER_JSON = `{
  "name": "Juan García",
  "document_id": "20-12345678-9",
  "document_type": "CUIT",
  "nationality": "AR",
  "pep": false,
  "occupation": "Software Engineer",
  "monthly_income_usd": 5000
}`
  const [kycCustomerJson, setKycCustomerJson] = useState(DEFAULT_CUSTOMER_JSON)
  const [kycScreenResult, setKycScreenResult] = useState<any>(null)
  const [kycScreenLoading, setKycScreenLoading] = useState(false)

  const [sanctionName, setSanctionName] = useState('')
  const [sanctionDocId, setSanctionDocId] = useState('')
  const [sanctionCountry, setSanctionCountry] = useState('')
  const [sanctionResult, setSanctionResult] = useState<any>(null)
  const [sanctionLoading, setSanctionLoading] = useState(false)

  const [kycJsonError, setKycJsonError] = useState<string | null>(null)

  function onKycJsonChange(val: string) {
    setKycCustomerJson(val)
    const [, err] = tryParseJSON(val)
    setKycJsonError(err)
  }

  async function screenCustomer() {
    const [parsed, err] = tryParseJSON(kycCustomerJson)
    if (err) return
    setKycScreenLoading(true)
    setKycScreenResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/kyc/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ customer_data: parsed }),
      })
      const data = await res.json()
      setKycScreenResult(data)
    } catch (e: any) {
      setKycScreenResult({ error: e.message })
    } finally {
      setKycScreenLoading(false)
    }
  }

  async function checkSanctions() {
    if (!sanctionName.trim()) return
    setSanctionLoading(true)
    setSanctionResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/kyc/sanctions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          subject_data: {
            name: sanctionName,
            document_id: sanctionDocId,
            country: sanctionCountry,
          },
        }),
      })
      const data = await res.json()
      setSanctionResult(data)
    } catch (e: any) {
      setSanctionResult({ error: e.message })
    } finally {
      setSanctionLoading(false)
    }
  }

  // ── M4 Monitoring state ────────────────────────────────────────────────────
  const DEFAULT_TX_JSON = `{
  "period": "2026-05",
  "total_transactions": 142,
  "total_volume_usd": 87500,
  "avg_ticket_usd": 616,
  "flagged_count": 3,
  "high_value_count": 8,
  "cross_border_pct": 0.34
}`
  const [monTxJson, setMonTxJson] = useState(DEFAULT_TX_JSON)
  const [monTxResult, setMonTxResult] = useState<any>(null)
  const [monTxLoading, setMonTxLoading] = useState(false)
  const [monTxJsonError, setMonTxJsonError] = useState<string | null>(null)

  const [driftPolicy, setDriftPolicy] = useState('')
  const [driftBehaviorJson, setDriftBehaviorJson] = useState('{}')
  const [driftResult, setDriftResult] = useState<any>(null)
  const [driftLoading, setDriftLoading] = useState(false)
  const [driftJsonError, setDriftJsonError] = useState<string | null>(null)

  function onMonTxJsonChange(val: string) {
    setMonTxJson(val)
    const [, err] = tryParseJSON(val)
    setMonTxJsonError(err)
  }

  function onDriftJsonChange(val: string) {
    setDriftBehaviorJson(val)
    const [, err] = tryParseJSON(val)
    setDriftJsonError(err)
  }

  async function analyzeTransactions() {
    const [parsed, err] = tryParseJSON(monTxJson)
    if (err) return
    setMonTxLoading(true)
    setMonTxResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/monitoring/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ transaction_summary: parsed }),
      })
      const data = await res.json()
      setMonTxResult(data)
    } catch (e: any) {
      setMonTxResult({ error: e.message })
    } finally {
      setMonTxLoading(false)
    }
  }

  async function detectDrift() {
    const [parsed, err] = tryParseJSON(driftBehaviorJson)
    if (err || !driftPolicy.trim()) return
    setDriftLoading(true)
    setDriftResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/monitoring/drift`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ policy_description: driftPolicy, observed_behavior: parsed }),
      })
      const data = await res.json()
      setDriftResult(data)
    } catch (e: any) {
      setDriftResult({ error: e.message })
    } finally {
      setDriftLoading(false)
    }
  }

  // ── M5 Governance state ────────────────────────────────────────────────────
  const [govQuestion, setGovQuestion] = useState('')
  const [govAiResponse, setGovAiResponse] = useState('')
  const [govContext, setGovContext] = useState('')
  const [govAuditResult, setGovAuditResult] = useState<any>(null)
  const [govAuditLoading, setGovAuditLoading] = useState(false)

  const [injectionText, setInjectionText] = useState('')
  const [injectionResult, setInjectionResult] = useState<any>(null)
  const [injectionLoading, setInjectionLoading] = useState(false)

  async function auditAiResponse() {
    if (!govQuestion.trim() || !govAiResponse.trim()) return
    setGovAuditLoading(true)
    setGovAuditResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/governance/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          original_question: govQuestion,
          ai_response: govAiResponse,
          factual_context: govContext,
        }),
      })
      const data = await res.json()
      setGovAuditResult(data)
    } catch (e: any) {
      setGovAuditResult({ error: e.message })
    } finally {
      setGovAuditLoading(false)
    }
  }

  async function checkInjection() {
    if (!injectionText.trim()) return
    setInjectionLoading(true)
    setInjectionResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/governance/check-injection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ text: injectionText }),
      })
      const data = await res.json()
      setInjectionResult(data)
    } catch (e: any) {
      setInjectionResult({ error: e.message })
    } finally {
      setInjectionLoading(false)
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

          {/* ── M1 Regulatory Intelligence ───────────────────────────────── */}
          {active === 'regulatory' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">M1 — Regulatory Intelligence</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Parse regulation text into structured obligations. Map cross-border obligations across jurisdictions.
              </p>

              {/* Parse Regulation */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mb-6">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Parse Regulation</div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Country (2-char)</label>
                    <input
                      type="text"
                      value={regCountry}
                      onChange={e => setRegCountry(e.target.value)}
                      placeholder="AR"
                      maxLength={2}
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Regulator</label>
                    <input
                      type="text"
                      value={regRegulator}
                      onChange={e => setRegRegulator(e.target.value)}
                      placeholder="BCRA"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Code</label>
                    <input
                      type="text"
                      value={regCode}
                      onChange={e => setRegCode(e.target.value)}
                      placeholder="Com. A 7825"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Title</label>
                  <input
                    type="text"
                    value={regTitle}
                    onChange={e => setRegTitle(e.target.value)}
                    placeholder="Regulation title"
                    className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Regulation text</label>
                  <textarea
                    value={regText}
                    onChange={e => setRegText(e.target.value)}
                    placeholder="Paste the full regulation text..."
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono min-h-40 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <button
                  onClick={parseRegulation}
                  disabled={regParseLoading || !regText.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {regParseLoading ? 'Parsing...' : 'Parse Regulation'}
                </button>

                {regParseResult && (
                  <div className="space-y-3">
                    {(regParseResult.error || regParseResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {regParseResult.error || regParseResult.detail || 'Parse failed'}
                      </div>
                    )}
                    {regParseResult.success && (
                      <div className="space-y-3">
                        <div className="flex gap-4 text-xs text-zinc-500">
                          <span>obligations persisted: <span className="font-mono text-zinc-300">{regParseResult.obligations_persisted ?? '—'}</span></span>
                        </div>
                        {regParseResult.summary && (
                          <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md text-sm whitespace-pre-wrap">
                            {regParseResult.summary}
                          </div>
                        )}
                        {Array.isArray(regParseResult.obligations) && regParseResult.obligations.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-xs text-zinc-500">Obligations</div>
                            {regParseResult.obligations.map((ob: any, i: number) => (
                              <div key={i} className="p-3 bg-zinc-900 border border-zinc-800 rounded-md space-y-1">
                                <div className="flex items-center gap-2">
                                  {ob.obligation_code && (
                                    <span className="font-mono text-xs text-zinc-400">{ob.obligation_code}</span>
                                  )}
                                  {ob.obligation_type && (
                                    <span className="text-xs text-zinc-500">{ob.obligation_type}</span>
                                  )}
                                  {ob.severity && (
                                    <span className={`text-xs px-1.5 py-0.5 rounded ${SEVERITY_COLORS[ob.severity] ?? 'bg-zinc-800 text-zinc-300'}`}>
                                      {ob.severity}
                                    </span>
                                  )}
                                </div>
                                {ob.description && (
                                  <div className="text-sm text-zinc-300">{ob.description}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Cross-border mapping */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Map Cross-Border Obligations</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Obligation topic</label>
                  <input
                    type="text"
                    value={mapTopic}
                    onChange={e => setMapTopic(e.target.value)}
                    placeholder="Suspicious Activity Reporting"
                    className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Countries (comma-separated)</label>
                  <input
                    type="text"
                    value={mapCountries}
                    onChange={e => setMapCountries(e.target.value)}
                    placeholder="AR,BR,MX"
                    className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <button
                  onClick={mapCrossBorder}
                  disabled={mapLoading || !mapTopic.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {mapLoading ? 'Mapping...' : 'Map Jurisdictions'}
                </button>

                {mapResult && (
                  <div className="space-y-3">
                    {(mapResult.error || mapResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {mapResult.error || mapResult.detail || 'Mapping failed'}
                      </div>
                    )}
                    {mapResult.mapping?.jurisdictions && Array.isArray(mapResult.mapping.jurisdictions) && (
                      <div className="border border-zinc-800 rounded-md overflow-hidden">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-zinc-800 bg-zinc-900">
                              <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Country</th>
                              <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Regulator</th>
                              <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Threshold USD</th>
                              <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Deadline (h)</th>
                              <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Penalties</th>
                            </tr>
                          </thead>
                          <tbody>
                            {mapResult.mapping.jurisdictions.map((j: any, i: number) => (
                              <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                                <td className="px-4 py-2.5 font-mono text-xs text-zinc-300">{j.country ?? '—'}</td>
                                <td className="px-4 py-2.5 text-xs">{j.regulator ?? '—'}</td>
                                <td className="px-4 py-2.5 text-xs font-mono">{j.threshold_usd ?? '—'}</td>
                                <td className="px-4 py-2.5 text-xs font-mono">{j.deadline_hours ?? '—'}</td>
                                <td className="px-4 py-2.5 text-xs text-zinc-400">{j.penalties ?? '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                    {mapResult.success && !mapResult.mapping?.jurisdictions && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md text-sm">
                        <pre className="whitespace-pre-wrap text-zinc-300 text-xs">{JSON.stringify(mapResult, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── M3 KYC/AML ──────────────────────────────────────────────────── */}
          {active === 'kyc' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">M3 — KYC/AML</h2>
              <p className="text-sm text-zinc-500 mb-6">
                AI-powered customer risk screening and sanctions checks. Powered by NVIDIA NIM.
              </p>

              {/* Screen customer */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mb-6">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Screen Customer</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Customer data (JSON)</label>
                  <textarea
                    value={kycCustomerJson}
                    onChange={e => onKycJsonChange(e.target.value)}
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono min-h-48 focus:outline-none focus:border-zinc-600"
                  />
                  {kycJsonError && (
                    <div className="text-red-400 text-xs mt-1">JSON error: {kycJsonError}</div>
                  )}
                </div>

                <button
                  onClick={screenCustomer}
                  disabled={kycScreenLoading || !!kycJsonError}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {kycScreenLoading ? 'Screening...' : 'Screen Customer'}
                </button>

                {kycScreenResult && (
                  <div className="space-y-3">
                    {(kycScreenResult.error || kycScreenResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {kycScreenResult.error || kycScreenResult.detail || 'Screening failed'}
                      </div>
                    )}
                    {kycScreenResult.success !== false && !kycScreenResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex items-center gap-3 flex-wrap">
                          {kycScreenResult.risk_level && (
                            <span className={`px-2.5 py-1 rounded text-sm font-medium ${RISK_COLORS[kycScreenResult.risk_level] ?? 'bg-zinc-800 text-zinc-300'}`}>
                              {kycScreenResult.risk_level}
                            </span>
                          )}
                          {kycScreenResult.ai_risk_score !== undefined && (
                            <span className="text-sm text-zinc-400">
                              AI risk score: <span className="font-mono text-zinc-200">{kycScreenResult.ai_risk_score}<span className="text-zinc-500">/100</span></span>
                            </span>
                          )}
                          {kycScreenResult.requires_human_review !== undefined && (
                            <span className={`text-xs px-2 py-0.5 rounded border ${kycScreenResult.requires_human_review ? 'border-yellow-900 bg-yellow-950 text-yellow-300' : 'border-zinc-700 bg-zinc-800 text-zinc-400'}`}>
                              {kycScreenResult.requires_human_review ? 'Requires human review' : 'No human review required'}
                            </span>
                          )}
                        </div>
                        {Array.isArray(kycScreenResult.red_flags) && kycScreenResult.red_flags.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Red flags</div>
                            <ul className="space-y-1">
                              {kycScreenResult.red_flags.map((flag: string, i: number) => (
                                <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                                  <span className="text-red-600 mt-0.5">&#x25CF;</span>{flag}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Sanctions check */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Sanctions Check</div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Name</label>
                    <input
                      type="text"
                      value={sanctionName}
                      onChange={e => setSanctionName(e.target.value)}
                      placeholder="Full name"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Document ID</label>
                    <input
                      type="text"
                      value={sanctionDocId}
                      onChange={e => setSanctionDocId(e.target.value)}
                      placeholder="e.g. 20-12345678-9"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500 block mb-1">Country</label>
                    <input
                      type="text"
                      value={sanctionCountry}
                      onChange={e => setSanctionCountry(e.target.value)}
                      placeholder="AR"
                      className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                    />
                  </div>
                </div>

                <button
                  onClick={checkSanctions}
                  disabled={sanctionLoading || !sanctionName.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {sanctionLoading ? 'Checking...' : 'Check Sanctions'}
                </button>

                {sanctionResult && (
                  <div className="space-y-2">
                    {sanctionResult.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {sanctionResult.error}
                      </div>
                    )}
                    {!sanctionResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                        <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{JSON.stringify(sanctionResult, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── M4 Monitoring ───────────────────────────────────────────────── */}
          {active === 'monitoring' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">M4 — Continuous Monitoring</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Analyze transaction patterns for anomalies, and detect policy drift in AI behavior.
              </p>

              {/* Transaction analysis */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mb-6">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Transaction Analysis</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Transaction summary (JSON)</label>
                  <textarea
                    value={monTxJson}
                    onChange={e => onMonTxJsonChange(e.target.value)}
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono min-h-48 focus:outline-none focus:border-zinc-600"
                  />
                  {monTxJsonError && (
                    <div className="text-red-400 text-xs mt-1">JSON error: {monTxJsonError}</div>
                  )}
                </div>

                <button
                  onClick={analyzeTransactions}
                  disabled={monTxLoading || !!monTxJsonError}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {monTxLoading ? 'Analyzing...' : 'Analyze Transactions'}
                </button>

                {monTxResult && (
                  <div className="space-y-3">
                    {(monTxResult.error || monTxResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {monTxResult.error || monTxResult.detail || 'Analysis failed'}
                      </div>
                    )}
                    {monTxResult.success !== false && !monTxResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex items-center gap-3">
                          {monTxResult.risk_level && (
                            <span className={`px-2.5 py-1 rounded text-sm font-medium ${RISK_COLORS[monTxResult.risk_level] ?? 'bg-zinc-800 text-zinc-300'}`}>
                              {monTxResult.risk_level}
                            </span>
                          )}
                        </div>
                        {Array.isArray(monTxResult.anomalies) && monTxResult.anomalies.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Anomalies detected</div>
                            <ul className="space-y-1">
                              {monTxResult.anomalies.map((a: any, i: number) => (
                                <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                                  <span className="text-yellow-600 mt-0.5">&#x25CF;</span>
                                  {typeof a === 'string' ? a : JSON.stringify(a)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {Array.isArray(monTxResult.recommendations) && monTxResult.recommendations.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Recommendations</div>
                            <ul className="space-y-1">
                              {monTxResult.recommendations.map((r: any, i: number) => (
                                <li key={i} className="text-sm text-zinc-400">
                                  {typeof r === 'string' ? r : JSON.stringify(r)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {!monTxResult.risk_level && !monTxResult.anomalies && (
                          <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{JSON.stringify(monTxResult, null, 2)}</pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Policy drift detection */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Policy Drift Detection</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Policy description</label>
                  <textarea
                    value={driftPolicy}
                    onChange={e => setDriftPolicy(e.target.value)}
                    placeholder="Describe the expected policy or control behavior..."
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm min-h-24 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Observed behavior (JSON)</label>
                  <textarea
                    value={driftBehaviorJson}
                    onChange={e => onDriftJsonChange(e.target.value)}
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono min-h-32 focus:outline-none focus:border-zinc-600"
                  />
                  {driftJsonError && (
                    <div className="text-red-400 text-xs mt-1">JSON error: {driftJsonError}</div>
                  )}
                </div>

                <button
                  onClick={detectDrift}
                  disabled={driftLoading || !!driftJsonError || !driftPolicy.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {driftLoading ? 'Detecting...' : 'Detect Drift'}
                </button>

                {driftResult && (
                  <div className="space-y-3">
                    {(driftResult.error || driftResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {driftResult.error || driftResult.detail || 'Drift detection failed'}
                      </div>
                    )}
                    {driftResult.success !== false && !driftResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex items-center gap-3">
                          {driftResult.drift_detected !== undefined && (
                            <span className={`px-2.5 py-1 rounded text-sm font-medium border ${driftResult.drift_detected ? 'bg-red-950 text-red-300 border-red-900' : 'bg-green-950 text-green-300 border-green-900'}`}>
                              {driftResult.drift_detected ? 'Drift detected' : 'No drift'}
                            </span>
                          )}
                          {driftResult.drift_score !== undefined && (
                            <span className="text-sm text-zinc-400">
                              Score: <span className="font-mono text-zinc-200">{driftResult.drift_score}</span>
                            </span>
                          )}
                        </div>
                        {Array.isArray(driftResult.findings) && driftResult.findings.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Findings</div>
                            <ul className="space-y-1">
                              {driftResult.findings.map((f: any, i: number) => (
                                <li key={i} className="text-sm text-zinc-300 flex items-start gap-2">
                                  <span className="text-orange-500 mt-0.5">&#x25CF;</span>
                                  {typeof f === 'string' ? f : JSON.stringify(f)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {driftResult.drift_detected === undefined && (
                          <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{JSON.stringify(driftResult, null, 2)}</pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── M5 AI Governance ────────────────────────────────────────────── */}
          {active === 'governance' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">M5 — AI Governance</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Audit AI responses for factual accuracy. Check inputs for prompt injection attempts.
              </p>

              {/* Audit AI response */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mb-6">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Audit AI Response</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Original question</label>
                  <input
                    type="text"
                    value={govQuestion}
                    onChange={e => setGovQuestion(e.target.value)}
                    placeholder="What was asked to the AI?"
                    className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">AI response</label>
                  <textarea
                    value={govAiResponse}
                    onChange={e => setGovAiResponse(e.target.value)}
                    placeholder="Paste the AI response to audit..."
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm min-h-32 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Factual context (ground truth)</label>
                  <textarea
                    value={govContext}
                    onChange={e => setGovContext(e.target.value)}
                    placeholder="Provide factual context or source material to check against..."
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm min-h-24 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <button
                  onClick={auditAiResponse}
                  disabled={govAuditLoading || !govQuestion.trim() || !govAiResponse.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {govAuditLoading ? 'Auditing...' : 'Audit Response'}
                </button>

                {govAuditResult && (
                  <div className="space-y-3">
                    {(govAuditResult.error || govAuditResult.success === false) && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {govAuditResult.error || govAuditResult.detail || 'Audit failed'}
                      </div>
                    )}
                    {govAuditResult.success !== false && !govAuditResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex items-center gap-3 flex-wrap">
                          {govAuditResult.verdict && (
                            <span className={`px-2.5 py-1 rounded text-sm font-medium border ${govAuditResult.verdict === 'PASS' ? 'bg-green-950 text-green-300 border-green-900' : 'bg-red-950 text-red-300 border-red-900'}`}>
                              {govAuditResult.verdict}
                            </span>
                          )}
                          {govAuditResult.factual_accuracy !== undefined && (
                            <span className="text-sm text-zinc-400">
                              Factual accuracy: <span className="font-mono text-zinc-200">{govAuditResult.factual_accuracy}</span>
                            </span>
                          )}
                        </div>
                        {Array.isArray(govAuditResult.issues) && govAuditResult.issues.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Issues found</div>
                            <ul className="space-y-1">
                              {govAuditResult.issues.map((issue: any, i: number) => (
                                <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                                  <span className="text-red-600 mt-0.5">&#x25CF;</span>
                                  {typeof issue === 'string' ? issue : JSON.stringify(issue)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {!govAuditResult.verdict && !govAuditResult.factual_accuracy && (
                          <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{JSON.stringify(govAuditResult, null, 2)}</pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Injection check */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Prompt Injection Check</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Text to check</label>
                  <textarea
                    value={injectionText}
                    onChange={e => setInjectionText(e.target.value)}
                    placeholder="Paste any user-submitted text to scan for injection patterns..."
                    className="w-full p-3 bg-zinc-900 border border-zinc-800 rounded-md text-sm min-h-28 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <button
                  onClick={checkInjection}
                  disabled={injectionLoading || !injectionText.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {injectionLoading ? 'Checking...' : 'Check for Injection'}
                </button>

                {injectionResult && (
                  <div className="space-y-3">
                    {injectionResult.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {injectionResult.error}
                      </div>
                    )}
                    {!injectionResult.error && (
                      <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-3">
                        <div className="flex items-center gap-3">
                          {injectionResult.injected !== undefined && (
                            <span className={`px-2.5 py-1 rounded text-sm font-medium border ${injectionResult.injected ? 'bg-red-950 text-red-300 border-red-900' : 'bg-green-950 text-green-300 border-green-900'}`}>
                              {injectionResult.injected ? 'Injection detected' : 'Clean'}
                            </span>
                          )}
                        </div>
                        {Array.isArray(injectionResult.matched_patterns) && injectionResult.matched_patterns.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1.5">Matched patterns</div>
                            <ul className="space-y-1">
                              {injectionResult.matched_patterns.map((p: string, i: number) => (
                                <li key={i} className="text-sm font-mono text-red-300 px-2 py-1 bg-red-950 rounded">{p}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
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

              {/* Regulation subgraph lookup */}
              <div className="mt-8 space-y-3">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Subgraph lookup</div>
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

                {!graphRegData && !graphRegLoading && (
                  <div className="p-6 border border-dashed border-zinc-800 rounded-md text-sm text-zinc-600 text-center">
                    No subgraph loaded — enter a regulation ID above
                  </div>
                )}

                {graphRegData && (
                  <div className="space-y-4">
                    {graphRegData.error && (
                      <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                        Error: {graphRegData.error}
                      </div>
                    )}
                    {!graphRegData.error && (
                      <div className="space-y-5">
                        <div className="flex gap-6 text-xs text-zinc-500">
                          <span>vertices: <span className="font-mono text-zinc-300">{graphRegData.vertex_count ?? graphRegData.vertices?.length ?? '—'}</span></span>
                          <span>edges: <span className="font-mono text-zinc-300">{graphRegData.edge_count ?? graphRegData.edges?.length ?? '—'}</span></span>
                        </div>

                        {/* Vertices table */}
                        {Array.isArray(graphRegData.vertices) && graphRegData.vertices.length > 0 ? (
                          <div>
                            <div className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">Vertices</div>
                            <div className="border border-zinc-700 rounded-md overflow-hidden">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-zinc-700 bg-zinc-900">
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Type</th>
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Label</th>
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">ID</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {graphRegData.vertices.map((v: any, i: number) => (
                                    <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                                      <td className="px-4 py-2.5 text-xs text-zinc-400 capitalize">{v.type ?? v.label_type ?? '—'}</td>
                                      <td className="px-4 py-2.5 text-xs text-zinc-300">{v.label ?? v.name ?? v.code ?? '—'}</td>
                                      <td className="px-4 py-2.5 text-xs font-mono text-zinc-500">{v.id ? String(v.id).slice(0, 8) : '—'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ) : (
                          Array.isArray(graphRegData.obligations) && graphRegData.obligations.length > 0 && (
                            <div>
                              <div className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">Obligation Vertices</div>
                              <div className="border border-zinc-700 rounded-md overflow-hidden">
                                <table className="w-full text-sm">
                                  <thead>
                                    <tr className="border-b border-zinc-700 bg-zinc-900">
                                      <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Type</th>
                                      <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Label</th>
                                      <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">ID</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {graphRegData.obligations.map((ob: any, i: number) => (
                                      <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                                        <td className="px-4 py-2.5 text-xs text-zinc-400">obligation</td>
                                        <td className="px-4 py-2.5 text-xs text-zinc-300">
                                          {typeof ob === 'string' ? ob : ob.label ?? ob.description ?? JSON.stringify(ob)}
                                        </td>
                                        <td className="px-4 py-2.5 text-xs font-mono text-zinc-500">
                                          {ob.id ? String(ob.id).slice(0, 8) : '—'}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )
                        )}

                        {/* Edges table */}
                        {Array.isArray(graphRegData.edges) && graphRegData.edges.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-2 uppercase tracking-wider">Edges</div>
                            <div className="border border-zinc-700 rounded-md overflow-hidden">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b border-zinc-700 bg-zinc-900">
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">From</th>
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Edge Type</th>
                                    <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">To</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {graphRegData.edges.map((e: any, i: number) => (
                                    <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                                      <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">
                                        {e.from_id ?? e.source ?? e.from ? String(e.from_id ?? e.source ?? e.from).slice(0, 8) : '—'}
                                      </td>
                                      <td className="px-4 py-2.5 text-xs font-mono text-zinc-300">{e.type ?? e.edge_type ?? e.label ?? '—'}</td>
                                      <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">
                                        {e.to_id ?? e.target ?? e.to ? String(e.to_id ?? e.target ?? e.to).slice(0, 8) : '—'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
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
              <div className="flex items-center gap-3 mb-2">
                <h2 className="text-xl font-semibold">Regulatory Crawler</h2>
                {crawlerStatus && !crawlerStatus.error && crawlerStatus.enabled && (
                  <span className="flex items-center gap-1.5">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                    </span>
                    <span className="text-xs text-green-500 font-medium">Live</span>
                  </span>
                )}
                {crawlerLastUpdated && (
                  <span className="text-xs text-zinc-600 ml-auto">
                    Last updated: <span className="font-mono text-zinc-500">{crawlerLastUpdated}</span>
                  </span>
                )}
              </div>
              <p className="text-sm text-zinc-500 mb-6">
                BCRA + UIF live feed. Fetches new regulations, parses with M1, stores in DB + Qdrant.
              </p>

              {crawlerStatusLoading && !crawlerStatus && (
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
        </section>
      </div>
    </main>
  )
}
