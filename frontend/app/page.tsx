'use client'

import { useState, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Module = 'copilot' | 'kyc' | 'monitoring' | 'governance' | 'regulatory' | 'evidence' | 'graph' | 'crawler' | 'admin' | 'audit' | 'search' | 'score' | 'alerts' | 'webhooks' | 'home' | 'workflows' | 'predictive' | 'ticketing'

function SkeletonRow({ cols = 3 }: { cols?: number }) {
  return (
    <tr className="border-b border-zinc-800">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-zinc-800 rounded animate-pulse" style={{ width: `${60 + (i * 15) % 30}%` }} />
        </td>
      ))}
    </tr>
  )
}

function SkeletonTable({ rows = 4, cols = 3 }: { rows?: number; cols?: number }) {
  return (
    <div className="border border-zinc-700 rounded-md overflow-hidden">
      <table className="w-full">
        <tbody>
          {Array.from({ length: rows }).map((_, i) => <SkeletonRow key={i} cols={cols} />)}
        </tbody>
      </table>
    </div>
  )
}

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
  const [isLoggedIn, setIsLoggedIn] = useState(true)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState(false)
  const [currentUser, setCurrentUser] = useState<{ role: string } | null>(null)

  function decodeJwtPayload(jwt: string): any {
    try {
      const payload = jwt.split('.')[1]
      return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    } catch { return null }
  }

  useEffect(() => {
    const stored = localStorage.getItem('cos_token')
    if (stored) {
      setToken(stored)
      setIsLoggedIn(true)
      const claims = decodeJwtPayload(stored)
      if (claims) setCurrentUser({ role: claims.role ?? 'analyst' })
    } else {
      fetch(`${API_URL}/api/v1/auth/token`, {
        method: 'POST',
        body: new URLSearchParams({ username: 'federico@polkorp.com', password: '12345' }),
      }).then(r => r.json()).then(data => {
        if (data.access_token) {
          localStorage.setItem('cos_token', data.access_token)
          setToken(data.access_token)
          setIsLoggedIn(true)
          const claims = decodeJwtPayload(data.access_token)
          if (claims) setCurrentUser({ role: claims.role ?? 'analyst' })
        }
      }).catch(() => {})
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
      const claims = decodeJwtPayload(t)
      if (claims) setCurrentUser({ role: claims.role ?? 'analyst' })
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
    setCurrentUser(null)
    setLoginEmail('')
    setLoginPassword('')
  }

  // ── Module state ───────────────────────────────────────────────────────────
  const [active, setActive] = useState<Module>('home')
  const [regulations, setRegulations] = useState<any[]>([])
  const [regulationsLoading, setRegulationsLoading] = useState(false)

  // ── Toast state ────────────────────────────────────────────────────────────
  const [successToast, setSuccessToast] = useState<string | null>(null)

  function showToast(msg: string) {
    setSuccessToast(msg)
    setTimeout(() => setSuccessToast(null), 3000)
  }

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
    if (active === 'evidence') fetchEvidenceDocs()
    if (active === 'regulatory') fetchRegulations()
  }, [active])

  async function fetchRegulations() {
    setRegulationsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/regulations`, { headers: authHeaders(token) })
      const data = await res.json()
      setRegulations(data.regulations || [])
    } catch {}
    finally { setRegulationsLoading(false) }
  }

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
      if (!data.error) showToast('Document extracted successfully.')
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
  const [crawlerEvents, setCrawlerEvents] = useState<any[]>([])

  useEffect(() => {
    if (active === 'crawler') {
      fetchCrawlerStatus()
      const interval = setInterval(() => {
        fetchCrawlerStatus()
      }, 30000)
      const es = new EventSource(`${API_URL}/api/v1/crawler/events`, {})
      es.addEventListener('crawl_complete', (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          setCrawlerEvents(prev => [data, ...prev].slice(0, 10))
        } catch {}
      })
      es.onerror = () => es.close()
      return () => {
        clearInterval(interval)
        es.close()
      }
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

  // ── Admin — tenant management ──────────────────────────────────────────────
  const [tenants, setTenants] = useState<any[]>([])
  const [tenantsLoading, setTenantsLoading] = useState(false)
  const [tenantForm, setTenantForm] = useState({ name: '', slug: '', data_residency_policy: 'global' })
  const [tenantResult, setTenantResult] = useState<any>(null)

  // ── Admin — API keys ───────────────────────────────────────────────────────
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [apiKeysLoading, setApiKeysLoading] = useState(false)
  const [newKeyForm, setNewKeyForm] = useState({ name: '', scopes: 'read,write', expires_days: '' })
  const [newKeyResult, setNewKeyResult] = useState<any>(null)
  const [newKeySecret, setNewKeySecret] = useState<string | null>(null)

  async function fetchTenants() {
    setTenantsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/tenants`, { headers: authHeaders(token) })
      const data = await res.json()
      setTenants(Array.isArray(data) ? data : [])
    } catch (e: any) { setTenants([]) }
    finally { setTenantsLoading(false) }
  }

  async function createTenant() {
    try {
      const res = await fetch(`${API_URL}/api/v1/tenants`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify(tenantForm),
      })
      const data = await res.json()
      setTenantResult(data)
      if (!data.error && !data.detail) { showToast('Tenant created.'); fetchTenants() }
    } catch (e: any) { setTenantResult({ error: e.message }) }
  }

  async function fetchApiKeys() {
    setApiKeysLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/api-keys`, { headers: authHeaders(token) })
      const data = await res.json()
      setApiKeys(Array.isArray(data) ? data : [])
    } catch (e: any) { setApiKeys([]) }
    finally { setApiKeysLoading(false) }
  }

  async function createApiKey() {
    try {
      const res = await fetch(`${API_URL}/api/v1/api-keys`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newKeyForm.name,
          scopes: newKeyForm.scopes.split(',').map(s => s.trim()).filter(Boolean),
          expires_days: newKeyForm.expires_days ? parseInt(newKeyForm.expires_days) : null,
        }),
      })
      const data = await res.json()
      setNewKeyResult(data)
      if (data.key) { setNewKeySecret(data.key); fetchApiKeys() }
    } catch (e: any) { setNewKeyResult({ error: e.message }) }
  }

  async function revokeApiKey(keyId: string) {
    try {
      await fetch(`${API_URL}/api/v1/api-keys/${keyId}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      })
      fetchApiKeys()
    } catch {}
  }

  useEffect(() => {
    if (active === 'admin') {
      fetchTenants()
      fetchApiKeys()
      fetchWebhooks()
    }
  }, [active])

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
      if (data.success) showToast('Regulation parsed.')
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

  // ── Audit log state ────────────────────────────────────────────────────────
  const [auditEntries, setAuditEntries] = useState<any[]>([])
  const [auditLoading, setAuditLoading] = useState(false)
  const [auditFilter, setAuditFilter] = useState('')
  const [auditEventTypes, setAuditEventTypes] = useState<string[]>([])

  useEffect(() => {
    if (active === 'audit') {
      fetchAudit()
      fetchAuditEventTypes()
    }
  }, [active])

  async function fetchAuditEventTypes() {
    try {
      const res = await fetch(`${API_URL}/api/v1/audit/event-types`, { headers: authHeaders(token) })
      const data = await res.json()
      setAuditEventTypes(Array.isArray(data.event_types) ? data.event_types : [])
    } catch { setAuditEventTypes([]) }
  }

  async function fetchAudit() {
    setAuditLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (auditFilter) params.set('event_type', auditFilter)
      const res = await fetch(`${API_URL}/api/v1/audit?${params}`, { headers: authHeaders(token) })
      const data = await res.json()
      setAuditEntries(Array.isArray(data.entries) ? data.entries : [])
    } catch { setAuditEntries([]) }
    finally { setAuditLoading(false) }
  }

  // ── Search state ───────────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchLoading, setSearchLoading] = useState(false)

  async function doSearch() {
    if (!searchQuery.trim()) return
    setSearchLoading(true)
    try {
      const params = new URLSearchParams({ q: searchQuery, limit: '10' })
      const res = await fetch(`${API_URL}/api/v1/search?${params}`, { headers: authHeaders(token) })
      const data = await res.json()
      setSearchResults(Array.isArray(data.results) ? data.results : [])
    } catch { setSearchResults([]) }
    finally { setSearchLoading(false) }
  }

  // ── Compliance Score state ─────────────────────────────────────────────────
  const [scores, setScores] = useState<any[]>([])
  const [scoresLoading, setScoresLoading] = useState(false)
  const [selectedEntityScore, setSelectedEntityScore] = useState<any>(null)
  const [scoreEntityId, setScoreEntityId] = useState('')
  const [scoreDetailLoading, setScoreDetailLoading] = useState(false)

  useEffect(() => {
    if (active === 'score') {
      fetchScores()
    }
  }, [active])

  async function fetchScores() {
    setScoresLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/compliance/scores`, { headers: authHeaders(token) })
      const data = await res.json()
      setScores(Array.isArray(data.scores) ? data.scores : [])
    } catch { setScores([]) } finally { setScoresLoading(false) }
  }

  async function fetchEntityScore(entityId: string) {
    setScoreEntityId(entityId)
    setScoreDetailLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/compliance/score/${entityId}`, { headers: authHeaders(token) })
      setSelectedEntityScore(await res.json())
    } catch (e: any) { setSelectedEntityScore({ error: e.message }) }
    finally { setScoreDetailLoading(false) }
  }

  // ── Alerts state ───────────────────────────────────────────────────────────
  const [alerts, setAlerts] = useState<any[]>([])
  const [alertsLoading, setAlertsLoading] = useState(false)
  const [alertsCount, setAlertsCount] = useState(0)

  // Load alerts count once on login
  useEffect(() => {
    if (isLoggedIn) fetchAlertsCount()
  }, [isLoggedIn])

  useEffect(() => {
    if (active === 'alerts') {
      fetchAlerts()
    }
  }, [active])

  async function fetchAlertsCount() {
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts?acknowledged=false`, { headers: authHeaders(token) })
      const data = await res.json()
      const list = Array.isArray(data) ? data : (Array.isArray(data.alerts) ? data.alerts : [])
      setAlertsCount(list.length)
    } catch { /* silently ignore */ }
  }

  async function fetchAlerts() {
    setAlertsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/alerts?acknowledged=false`, { headers: authHeaders(token) })
      const data = await res.json()
      const list = Array.isArray(data) ? data : (Array.isArray(data.alerts) ? data.alerts : [])
      setAlerts(list)
      setAlertsCount(list.length)
    } catch { setAlerts([]) } finally { setAlertsLoading(false) }
  }

  async function acknowledgeAlert(alertId: string) {
    try {
      await fetch(`${API_URL}/api/v1/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: authHeaders(token),
      })
      fetchAlerts()
    } catch {}
  }

  // ── Webhooks state ─────────────────────────────────────────────────────────
  const [webhooks, setWebhooks] = useState<any[]>([])
  const [webhooksLoading, setWebhooksLoading] = useState(false)
  const [webhookForm, setWebhookForm] = useState({ name: '', url: '', secret: '', events: 'crawl.complete' })
  const [webhookResult, setWebhookResult] = useState<any>(null)

  async function fetchWebhooks() {
    setWebhooksLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/webhooks`, { headers: authHeaders(token) })
      const data = await res.json()
      setWebhooks(Array.isArray(data) ? data : (Array.isArray(data.webhooks) ? data.webhooks : []))
    } catch { setWebhooks([]) } finally { setWebhooksLoading(false) }
  }

  async function createWebhook() {
    try {
      const res = await fetch(`${API_URL}/api/v1/webhooks`, {
        method: 'POST',
        headers: { ...authHeaders(token), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: webhookForm.name,
          url: webhookForm.url,
          secret: webhookForm.secret || undefined,
          events: webhookForm.events.split(',').map(s => s.trim()).filter(Boolean),
        }),
      })
      const data = await res.json()
      setWebhookResult(data)
      if (!data.error && !data.detail) { showToast('Webhook created.'); fetchWebhooks() }
    } catch (e: any) { setWebhookResult({ error: e.message }) }
  }

  async function testWebhook(id: string) {
    try {
      const res = await fetch(`${API_URL}/api/v1/webhooks/${id}/test`, {
        method: 'POST',
        headers: authHeaders(token),
      })
      const data = await res.json()
      showToast(data.success ? 'Test delivered.' : `Test failed: ${data.error ?? 'unknown'}`)
    } catch {}
  }

  async function deleteWebhook(id: string) {
    try {
      await fetch(`${API_URL}/api/v1/webhooks/${id}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      })
      fetchWebhooks()
    } catch {}
  }

  // ── M7 Workflows state ─────────────────────────────────────────────────────
  const [workflowTitle, setWorkflowTitle] = useState('')
  const [workflowTrigger, setWorkflowTrigger] = useState('')
  const [workflowSeverity, setWorkflowSeverity] = useState('medium')
  const [workflowResult, setWorkflowResult] = useState<any>(null)
  const [workflowLoading, setWorkflowLoading] = useState(false)

  async function createWorkflow() {
    if (!workflowTitle.trim() || !workflowTrigger.trim()) return
    setWorkflowLoading(true)
    setWorkflowResult(null)
    try {
      const res = await fetch(`${API_URL}/api/v1/workflow/remediation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ title: workflowTitle, trigger_source: workflowTrigger, severity: workflowSeverity }),
      })
      const data = await res.json()
      setWorkflowResult(data)
      if (!data.error && !data.detail) showToast('Workflow created.')
    } catch (e: any) {
      setWorkflowResult({ error: e.message })
    } finally {
      setWorkflowLoading(false)
    }
  }

  // ── M8 Predictive state ────────────────────────────────────────────────────
  const [jurisdictionRisks, setJurisdictionRisks] = useState<any>(null)
  const [jurisdictionRisksLoading, setJurisdictionRisksLoading] = useState(false)
  const [simBusinessModel, setSimBusinessModel] = useState('')
  const [simCountries, setSimCountries] = useState('AR,BR,MX')
  const [simResult, setSimResult] = useState<any>(null)
  const [simLoading, setSimLoading] = useState(false)

  useEffect(() => {
    if (active === 'predictive') {
      fetchJurisdictionRisks()
    }
  }, [active])

  async function fetchJurisdictionRisks() {
    setJurisdictionRisksLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/predict/jurisdiction-risk`, {
        headers: authHeaders(token),
      })
      const data = await res.json()
      setJurisdictionRisks(data)
    } catch (e: any) {
      setJurisdictionRisks({ error: e.message })
    } finally {
      setJurisdictionRisksLoading(false)
    }
  }

  async function simulateMarketEntry() {
    if (!simBusinessModel.trim()) return
    setSimLoading(true)
    setSimResult(null)
    try {
      const countries = simCountries.split(',').map(c => c.trim()).filter(Boolean)
      const res = await fetch(`${API_URL}/api/v1/simulate/market-entry`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ business_model: simBusinessModel, countries }),
      })
      const data = await res.json()
      setSimResult(data)
    } catch (e: any) {
      setSimResult({ error: e.message })
    } finally {
      setSimLoading(false)
    }
  }

  // ── M9 Ticketing state ─────────────────────────────────────────────────────
  const [tickets, setTickets] = useState<any[]>([])
  const [ticketTitle, setTicketTitle] = useState('')
  const [ticketDesc, setTicketDesc] = useState('')
  const [ticketPriority, setTicketPriority] = useState('medium')
  const [ticketLoading, setTicketLoading] = useState(false)
  const [ticketsLoading, setTicketsLoading] = useState(false)

  useEffect(() => {
    if (active === 'ticketing') {
      fetchTickets()
    }
  }, [active])

  async function fetchTickets() {
    setTicketsLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/tickets`, { headers: authHeaders(token) })
      const data = await res.json()
      setTickets(Array.isArray(data) ? data : [])
    } catch { setTickets([]) } finally { setTicketsLoading(false) }
  }

  async function createTicket() {
    if (!ticketTitle.trim()) return
    setTicketLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/v1/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ title: ticketTitle, description: ticketDesc || undefined, priority: ticketPriority }),
      })
      const data = await res.json()
      if (!data.error && !data.detail) {
        showToast('Ticket created.')
        setTicketTitle('')
        setTicketDesc('')
        fetchTickets()
      }
    } catch {} finally { setTicketLoading(false) }
  }

  async function updateTicketStatus(ticketId: string, status: string) {
    try {
      await fetch(`${API_URL}/api/v1/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ status }),
      })
      fetchTickets()
    } catch {}
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
              { id: 'home', label: 'Home', desc: 'Overview dashboard' },
              { id: 'regulatory', label: 'M1 — Regulatory Intel', desc: 'Parse + map regulations' },
              { id: 'copilot', label: 'M2 — Compliance Copilot', desc: 'Multi-jurisdiction Q&A' },
              { id: 'kyc', label: 'M3 — KYC/AML', desc: 'Screening + EDD' },
              { id: 'monitoring', label: 'M4 — Monitoring', desc: 'Anomalies + drift' },
              { id: 'governance', label: 'M5 — AI Governance', desc: 'Audit + safety' },
              { id: 'evidence', label: 'M6 — Evidence', desc: 'PDF extraction + custody chain' },
              { id: 'workflows', label: 'M7 — Workflows', desc: 'Remediation workflows' },
              { id: 'predictive', label: 'M8 — Predictive', desc: 'Risk & market simulation' },
              { id: 'ticketing', label: 'M9 — Ticketing', desc: 'Compliance tickets' },
              { id: 'graph', label: 'Graph', desc: 'Compliance relationship graph' },
              { id: 'crawler', label: 'Crawler', desc: 'BCRA + UIF live feed' },
              { id: 'audit', label: 'Audit Log', desc: 'Tamper-evident event history' },
              { id: 'search', label: 'Search', desc: 'Hybrid keyword + semantic search' },
              { id: 'score', label: 'Compliance', desc: 'Entity compliance scores' },
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
            <button
              onClick={() => setActive('alerts')}
              className={`w-full text-left p-3 rounded-md transition ${
                active === 'alerts'
                  ? 'bg-zinc-800 border border-zinc-700'
                  : 'hover:bg-zinc-900'
              }`}
            >
              <div className="text-sm font-medium flex items-center">
                Alerts{alertsCount > 0 && <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-500 text-white rounded-full">{alertsCount}</span>}
              </div>
              <div className="text-xs text-zinc-500">Deadline + compliance alerts</div>
            </button>
            {currentUser?.role === 'admin' && (
              <button
                onClick={() => setActive('admin')}
                className={`w-full text-left p-3 rounded-md transition ${
                  active === 'admin'
                    ? 'bg-zinc-800 border border-zinc-700'
                    : 'hover:bg-zinc-900'
                }`}
              >
                <div className="text-sm font-medium">Admin</div>
                <div className="text-xs text-zinc-500">Tenants + API keys</div>
              </button>
            )}
          </nav>
        </aside>

        <section className="col-span-9">
          {successToast && (
            <div className="mb-4 px-4 py-2.5 bg-green-950 border border-green-800 rounded-md text-sm text-green-400 transition-opacity">
              {successToast}
            </div>
          )}

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

              {/* Regulations Library */}
              <div className="border border-zinc-800 rounded-md p-5 mb-6">
                <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Regulations Library</div>
                {regulationsLoading ? (
                  <p className="text-sm text-zinc-500">Loading...</p>
                ) : regulations.length === 0 ? (
                  <p className="text-sm text-zinc-500">No regulations yet. Run the crawler or parse a regulation below.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead><tr className="text-left text-xs text-zinc-500 border-b border-zinc-800">
                      <th className="pb-2 pr-4">Code</th>
                      <th className="pb-2 pr-4">Title</th>
                      <th className="pb-2 pr-4">Country</th>
                      <th className="pb-2">Regulator</th>
                    </tr></thead>
                    <tbody>{regulations.map(r => (
                      <tr key={r.id} className="border-b border-zinc-900 hover:bg-zinc-900/50">
                        <td className="py-2 pr-4 font-mono text-xs text-zinc-400">{r.code}</td>
                        <td className="py-2 pr-4 text-zinc-200">{r.title}</td>
                        <td className="py-2 pr-4 text-zinc-400">{r.country}</td>
                        <td className="py-2 text-zinc-400">{r.regulator}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </div>

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
                {evidenceDocsLoading && evidenceDocs.length === 0 ? (
                  <SkeletonTable rows={4} cols={5} />
                ) : evidenceDocs.length === 0 ? (
                  <div className="text-center py-10 text-zinc-600 text-sm">
                    No documents uploaded yet.
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

              {graphStatsLoading && !graphStats && (
                <div className="mb-6">
                  <SkeletonTable rows={4} cols={3} />
                </div>
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
                  <button
                    onClick={fetchGraphStats}
                    className="text-xs text-zinc-500 hover:text-zinc-300 underline ml-2"
                  >
                    retry
                  </button>
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
                        ) : Array.isArray(graphRegData.vertices) && graphRegData.vertices.length === 0 ? (
                          <div className="text-center py-10 text-zinc-600 text-sm">
                            No entities registered yet.
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

          {/* ── Admin ───────────────────────────────────────────────────────── */}
          {active === 'admin' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Admin</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Tenant management and API key administration.
              </p>

              {/* ── Tenant Management ── */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mb-8">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-zinc-500">Tenant Management</div>
                  <button
                    onClick={fetchTenants}
                    disabled={tenantsLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {tenantsLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {tenantsLoading && tenants.length === 0 ? (
                  <SkeletonTable rows={3} cols={5} />
                ) : tenants.length === 0 ? (
                  <div className="text-center py-8 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                    No tenants found.
                  </div>
                ) : (
                  <div className="border border-zinc-700 rounded-md overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-700 bg-zinc-900">
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Name</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Slug</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Policy</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Active</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tenants.map((t: any, i: number) => (
                          <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                            <td className="px-4 py-2.5 text-xs text-zinc-200">{t.name ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">{t.slug ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-zinc-400">{t.data_residency_policy ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs">
                              <span className={`px-1.5 py-0.5 rounded text-xs border ${t.is_active !== false ? 'bg-green-950 text-green-400 border-green-900' : 'bg-zinc-800 text-zinc-500 border-zinc-700'}`}>
                                {t.is_active !== false ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-xs text-zinc-500">
                              {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Create tenant form */}
                <div className="pt-2 space-y-3 border-t border-zinc-800">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider">Create Tenant</div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Name</label>
                      <input
                        type="text"
                        value={tenantForm.name}
                        onChange={e => setTenantForm(f => ({ ...f, name: e.target.value }))}
                        placeholder="Acme Corp"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Slug</label>
                      <input
                        type="text"
                        value={tenantForm.slug}
                        onChange={e => setTenantForm(f => ({ ...f, slug: e.target.value }))}
                        placeholder="acme"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Data Residency Policy</label>
                      <select
                        value={tenantForm.data_residency_policy}
                        onChange={e => setTenantForm(f => ({ ...f, data_residency_policy: e.target.value }))}
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                      >
                        <option value="global">global</option>
                        <option value="latam">latam</option>
                        <option value="ar">ar</option>
                        <option value="br">br</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={createTenant}
                    disabled={!tenantForm.name.trim() || !tenantForm.slug.trim()}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    Create Tenant
                  </button>
                  {tenantResult && (
                    <div className={`p-3 rounded-md text-sm border ${tenantResult.error || tenantResult.detail ? 'bg-red-950 border-red-900 text-red-200' : 'bg-zinc-900 border-zinc-800 text-zinc-300'}`}>
                      {tenantResult.error || tenantResult.detail
                        ? `Error: ${tenantResult.error ?? tenantResult.detail}`
                        : <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(tenantResult, null, 2)}</pre>
                      }
                    </div>
                  )}
                </div>
              </div>

              {/* ── API Keys ── */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-zinc-500">API Keys</div>
                  <button
                    onClick={fetchApiKeys}
                    disabled={apiKeysLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {apiKeysLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {apiKeysLoading && apiKeys.length === 0 ? (
                  <SkeletonTable rows={3} cols={5} />
                ) : apiKeys.length === 0 ? (
                  <div className="text-center py-8 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                    No API keys found.
                  </div>
                ) : (
                  <div className="border border-zinc-700 rounded-md overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-700 bg-zinc-900">
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Name</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Prefix</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Scopes</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Last Used</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {apiKeys.map((k: any, i: number) => {
                          const lastUsed = k.last_used_at
                            ? (() => {
                                const diff = Date.now() - new Date(k.last_used_at).getTime()
                                const mins = Math.floor(diff / 60000)
                                if (mins < 60) return `${mins}m ago`
                                const hrs = Math.floor(mins / 60)
                                if (hrs < 24) return `${hrs}h ago`
                                return `${Math.floor(hrs / 24)}d ago`
                              })()
                            : 'Never'
                          return (
                            <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                              <td className="px-4 py-2.5 text-xs text-zinc-200">{k.name ?? '—'}</td>
                              <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">{k.key_prefix ?? '—'}</td>
                              <td className="px-4 py-2.5 text-xs text-zinc-400">
                                {Array.isArray(k.scopes) ? k.scopes.join(', ') : (k.scopes ?? '—')}
                              </td>
                              <td className="px-4 py-2.5 text-xs text-zinc-500">{lastUsed}</td>
                              <td className="px-4 py-2.5 text-xs">
                                {k.is_active !== false && (
                                  <button
                                    onClick={() => revokeApiKey(k.id)}
                                    className="px-2 py-1 text-xs text-red-400 border border-red-900 rounded hover:bg-red-950"
                                  >
                                    Revoke
                                  </button>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Create key form */}
                <div className="pt-2 space-y-3 border-t border-zinc-800">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider">Create API Key</div>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Name</label>
                      <input
                        type="text"
                        value={newKeyForm.name}
                        onChange={e => setNewKeyForm(f => ({ ...f, name: e.target.value }))}
                        placeholder="CI pipeline key"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Scopes (comma-separated)</label>
                      <input
                        type="text"
                        value={newKeyForm.scopes}
                        onChange={e => setNewKeyForm(f => ({ ...f, scopes: e.target.value }))}
                        placeholder="read,write"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Expires (days, optional)</label>
                      <input
                        type="number"
                        value={newKeyForm.expires_days}
                        onChange={e => setNewKeyForm(f => ({ ...f, expires_days: e.target.value }))}
                        placeholder="e.g. 90"
                        min={1}
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                  </div>
                  <button
                    onClick={createApiKey}
                    disabled={!newKeyForm.name.trim()}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    Create API Key
                  </button>

                  {newKeyResult && (newKeyResult.error || newKeyResult.detail) && (
                    <div className="p-3 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                      Error: {newKeyResult.error ?? newKeyResult.detail}
                    </div>
                  )}

                  {newKeySecret && (
                    <div className="mt-4 p-4 bg-yellow-950 border border-yellow-800 rounded-md">
                      <div className="text-xs text-yellow-400 font-medium mb-2">
                        Copy this key now — it will not be shown again
                      </div>
                      <div className="font-mono text-sm text-yellow-200 break-all select-all bg-yellow-900/30 px-3 py-2 rounded">
                        {newKeySecret}
                      </div>
                      <button
                        onClick={() => { navigator.clipboard.writeText(newKeySecret); showToast('Key copied!') }}
                        className="mt-2 text-xs text-yellow-400 hover:text-yellow-200 underline"
                      >
                        Copy to clipboard
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* ── Webhooks ── */}
              <div className="border border-zinc-800 rounded-md p-5 space-y-4 mt-8">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-zinc-500">Webhooks</div>
                  <button
                    onClick={fetchWebhooks}
                    disabled={webhooksLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {webhooksLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {webhooksLoading && webhooks.length === 0 ? (
                  <SkeletonTable rows={3} cols={5} />
                ) : webhooks.length === 0 ? (
                  <div className="text-center py-8 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                    No webhooks configured.
                  </div>
                ) : (
                  <div className="border border-zinc-700 rounded-md overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-700 bg-zinc-900">
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Name</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">URL</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Events</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Last Status</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {webhooks.map((w: any, i: number) => (
                          <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                            <td className="px-4 py-2.5 text-xs text-zinc-200">{w.name ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs font-mono text-zinc-400 max-w-xs truncate">{w.url ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-zinc-400">
                              {Array.isArray(w.events) ? w.events.join(', ') : (w.events ?? '—')}
                            </td>
                            <td className="px-4 py-2.5 text-xs">
                              {w.last_status ? (
                                <span className={`px-1.5 py-0.5 rounded border text-xs ${w.last_status >= 200 && w.last_status < 300 ? 'bg-green-950 text-green-400 border-green-900' : 'bg-red-950 text-red-400 border-red-900'}`}>
                                  {w.last_status}
                                </span>
                              ) : <span className="text-zinc-600">—</span>}
                            </td>
                            <td className="px-4 py-2.5 text-xs flex gap-2">
                              <button
                                onClick={() => testWebhook(w.id)}
                                className="px-2 py-1 text-xs text-zinc-400 border border-zinc-700 rounded hover:bg-zinc-800"
                              >
                                Test
                              </button>
                              <button
                                onClick={() => deleteWebhook(w.id)}
                                className="px-2 py-1 text-xs text-red-400 border border-red-900 rounded hover:bg-red-950"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Create webhook form */}
                <div className="pt-2 space-y-3 border-t border-zinc-800">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider">Add Webhook</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Name</label>
                      <input
                        type="text"
                        value={webhookForm.name}
                        onChange={e => setWebhookForm(f => ({ ...f, name: e.target.value }))}
                        placeholder="My webhook"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">URL</label>
                      <input
                        type="url"
                        value={webhookForm.url}
                        onChange={e => setWebhookForm(f => ({ ...f, url: e.target.value }))}
                        placeholder="https://example.com/webhook"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Secret (optional)</label>
                      <input
                        type="password"
                        value={webhookForm.secret}
                        onChange={e => setWebhookForm(f => ({ ...f, secret: e.target.value }))}
                        placeholder="HMAC signing secret"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-zinc-500 block mb-1">Events (comma-separated)</label>
                      <input
                        type="text"
                        value={webhookForm.events}
                        onChange={e => setWebhookForm(f => ({ ...f, events: e.target.value }))}
                        placeholder="crawl.complete,alert.created"
                        className="w-full p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm font-mono focus:outline-none focus:border-zinc-600"
                      />
                    </div>
                  </div>
                  <button
                    onClick={createWebhook}
                    disabled={!webhookForm.name.trim() || !webhookForm.url.trim()}
                    className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                  >
                    Add Webhook
                  </button>
                  {webhookResult && (
                    <div className={`p-3 rounded-md text-sm border ${webhookResult.error || webhookResult.detail ? 'bg-red-950 border-red-900 text-red-200' : 'bg-zinc-900 border-zinc-800 text-zinc-300'}`}>
                      {webhookResult.error || webhookResult.detail
                        ? `Error: ${webhookResult.error ?? webhookResult.detail}`
                        : <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(webhookResult, null, 2)}</pre>
                      }
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Audit Log ────────────────────────────────────────────────────── */}
          {active === 'audit' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Audit Log</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Tamper-evident hash-chained log of every compliance decision and AI inference.
              </p>

              <div className="flex gap-3 mb-4">
                <select
                  value={auditFilter}
                  onChange={e => setAuditFilter(e.target.value)}
                  className="p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600 min-w-48"
                >
                  <option value="">All event types</option>
                  {auditEventTypes.map(et => (
                    <option key={et} value={et}>{et}</option>
                  ))}
                </select>
                <button
                  onClick={fetchAudit}
                  disabled={auditLoading}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {auditLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>

              {auditLoading && auditEntries.length === 0 ? (
                <SkeletonTable rows={5} cols={5} />
              ) : auditEntries.length === 0 ? (
                <div className="text-center py-10 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                  No audit entries found.
                </div>
              ) : (
                <div className="border border-zinc-700 rounded-md overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-700 bg-zinc-900">
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Event Type</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Summary</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">User</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Hash</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditEntries.map((e: any, i: number) => (
                        <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                          <td className="px-4 py-2.5 text-xs font-mono text-zinc-300">{e.event_type ?? '—'}</td>
                          <td className="px-4 py-2.5 text-xs text-zinc-400 max-w-xs truncate">{e.payload_summary || '—'}</td>
                          <td className="px-4 py-2.5 text-xs font-mono text-zinc-500">{e.user_id ? String(e.user_id).slice(0, 8) : '—'}</td>
                          <td className="px-4 py-2.5 text-xs font-mono text-zinc-600">{e.hash ?? '—'}</td>
                          <td className="px-4 py-2.5 text-xs text-zinc-500">
                            {e.created_at ? new Date(e.created_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'medium' }) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* ── Search ───────────────────────────────────────────────────────── */}
          {active === 'search' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Search</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Hybrid keyword + semantic search across regulations. Keyword results from Postgres, semantic from Qdrant.
              </p>

              <div className="flex gap-3 mb-6">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && doSearch()}
                  placeholder="e.g. UIF suspicious activity reporting, AML threshold..."
                  className="flex-1 p-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
                />
                <button
                  onClick={doSearch}
                  disabled={searchLoading || !searchQuery.trim()}
                  className="px-5 py-2 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {searchLoading ? 'Searching...' : 'Search'}
                </button>
              </div>

              {searchLoading && searchResults.length === 0 && (
                <div className="space-y-3">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="p-4 bg-zinc-900 border border-zinc-800 rounded-md animate-pulse space-y-2">
                      <div className="h-3 bg-zinc-800 rounded w-3/4" />
                      <div className="h-3 bg-zinc-800 rounded w-1/2" />
                    </div>
                  ))}
                </div>
              )}

              {!searchLoading && searchResults.length === 0 && searchQuery.trim() && (
                <div className="text-center py-10 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                  No results found for &ldquo;{searchQuery}&rdquo;.
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="space-y-3">
                  {searchResults.map((r: any, i: number) => (
                    <div key={i} className="p-4 bg-zinc-900 border border-zinc-800 rounded-md space-y-2">
                      <div className="flex items-start justify-between gap-3">
                        <div className="font-medium text-sm text-zinc-100">{r.title || '(No title)'}</div>
                        <span className={`shrink-0 text-xs px-2 py-0.5 rounded border font-mono ${
                          r.source === 'hybrid'
                            ? 'bg-purple-950 text-purple-300 border-purple-800'
                            : r.source === 'semantic'
                            ? 'bg-blue-950 text-blue-300 border-blue-800'
                            : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                        }`}>
                          {r.source}
                        </span>
                      </div>
                      <div className="text-xs text-zinc-500">
                        {r.regulator && <span>{r.regulator}</span>}
                        {r.regulator && r.country && <span className="text-zinc-700"> · </span>}
                        {r.country && <span>{r.country}</span>}
                      </div>
                      {r.excerpt && (
                        <p className="text-xs text-zinc-400 leading-relaxed line-clamp-3">{r.excerpt}</p>
                      )}
                      {r.code && (
                        <div className="font-mono text-xs text-zinc-600">{r.code}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── Compliance Score ─────────────────────────────────────────────── */}
          {active === 'score' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Compliance Score</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Entity-level compliance scores based on obligation satisfaction. Click a row to see the obligation breakdown.
              </p>

              <div className="flex items-center justify-between mb-3">
                <div className="text-xs uppercase tracking-wider text-zinc-500">All Entities</div>
                <button
                  onClick={fetchScores}
                  disabled={scoresLoading}
                  className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                >
                  {scoresLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>

              {scoresLoading && scores.length === 0 ? (
                <SkeletonTable rows={5} cols={3} />
              ) : scores.length === 0 ? (
                <div className="text-center py-10 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                  No compliance scores available.
                </div>
              ) : (
                <div className="border border-zinc-700 rounded-md overflow-hidden mb-8">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-700 bg-zinc-900">
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Entity Name</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Score %</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Satisfied / Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scores.map((s: any, i: number) => {
                        const pct = typeof s.score_pct === 'number' ? s.score_pct : typeof s.score === 'number' ? s.score : null
                        const barColor = pct === null ? 'bg-zinc-600' : pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                        const textColor = pct === null ? 'text-zinc-400' : pct >= 80 ? 'text-green-400' : pct >= 50 ? 'text-yellow-400' : 'text-red-400'
                        return (
                          <tr
                            key={i}
                            onClick={() => fetchEntityScore(s.entity_id ?? s.id ?? String(i))}
                            className={`border-b border-zinc-800 last:border-0 cursor-pointer hover:bg-zinc-900 ${scoreEntityId === (s.entity_id ?? s.id ?? String(i)) ? 'bg-zinc-900' : ''}`}
                          >
                            <td className="px-4 py-2.5 text-xs text-zinc-200">{s.entity_name ?? s.name ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs">
                              <div className="flex items-center gap-2">
                                <div className="w-24 bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                                  <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${Math.min(100, pct ?? 0)}%` }} />
                                </div>
                                <span className={`font-mono ${textColor}`}>{pct !== null ? `${pct}%` : '—'}</span>
                              </div>
                            </td>
                            <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">
                              {s.satisfied !== undefined && s.total !== undefined ? `${s.satisfied} / ${s.total}` : '—'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {scoreDetailLoading && (
                <div className="mt-4">
                  <SkeletonTable rows={4} cols={4} />
                </div>
              )}

              {selectedEntityScore && !scoreDetailLoading && (
                <div className="mt-4">
                  {selectedEntityScore.error && (
                    <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
                      Error: {selectedEntityScore.error}
                    </div>
                  )}
                  {!selectedEntityScore.error && (
                    <div>
                      <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Obligation Breakdown</div>
                      {Array.isArray(selectedEntityScore.obligations) && selectedEntityScore.obligations.length > 0 ? (
                        <div className="border border-zinc-700 rounded-md overflow-hidden">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="border-b border-zinc-700 bg-zinc-900">
                                <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Title</th>
                                <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Type</th>
                                <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Status</th>
                                <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Control</th>
                              </tr>
                            </thead>
                            <tbody>
                              {selectedEntityScore.obligations.map((ob: any, i: number) => (
                                <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                                  <td className="px-4 py-2.5 text-xs text-zinc-200 max-w-xs truncate">{ob.title ?? ob.description ?? '—'}</td>
                                  <td className="px-4 py-2.5 text-xs text-zinc-400">{ob.obligation_type ?? ob.type ?? '—'}</td>
                                  <td className="px-4 py-2.5 text-xs">
                                    {ob.satisfied ? (
                                      <span className="text-green-400">&#x2713;</span>
                                    ) : (
                                      <span className="text-red-400">&#x2717;</span>
                                    )}
                                  </td>
                                  <td className="px-4 py-2.5 text-xs text-zinc-500 max-w-xs truncate">{ob.control ?? ob.control_description ?? '—'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-md">
                          <pre className="text-xs font-mono text-zinc-300 whitespace-pre-wrap">{JSON.stringify(selectedEntityScore, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Alerts ───────────────────────────────────────────────────────── */}
          {active === 'alerts' && (
            <div>
              <h2 className="text-xl font-semibold mb-2">Alerts</h2>
              <p className="text-sm text-zinc-500 mb-6">
                Unacknowledged deadline and compliance alerts. Click Acknowledge to dismiss.
              </p>

              <div className="flex items-center justify-between mb-3">
                <div className="text-xs uppercase tracking-wider text-zinc-500">
                  Unacknowledged{alertsCount > 0 && <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-red-500 text-white rounded-full">{alertsCount}</span>}
                </div>
                <button
                  onClick={fetchAlerts}
                  disabled={alertsLoading}
                  className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                >
                  {alertsLoading ? 'Loading...' : 'Refresh'}
                </button>
              </div>

              {alertsLoading && alerts.length === 0 ? (
                <SkeletonTable rows={5} cols={6} />
              ) : alerts.length === 0 ? (
                <div className="text-center py-10 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded-md">
                  No unacknowledged alerts.
                </div>
              ) : (
                <div className="border border-zinc-700 rounded-md overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-zinc-700 bg-zinc-900">
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Severity</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Reg. Code</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Title</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Deadline</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Days</th>
                        <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {alerts.map((a: any, i: number) => {
                        const sev = (a.severity ?? '').toUpperCase()
                        const sevBadge =
                          sev === 'CRITICAL' ? 'bg-red-950 text-red-400 border border-red-900' :
                          sev === 'HIGH' ? 'bg-orange-950 text-orange-400 border border-orange-900' :
                          sev === 'MEDIUM' ? 'bg-yellow-950 text-yellow-400 border border-yellow-900' :
                          'bg-zinc-800 text-zinc-400 border border-zinc-700'
                        const deadline = a.deadline ? new Date(a.deadline) : null
                        const daysLeft = deadline ? Math.ceil((deadline.getTime() - Date.now()) / 86400000) : null
                        const daysColor = daysLeft === null ? 'text-zinc-500' : daysLeft <= 7 ? 'text-red-400' : daysLeft <= 30 ? 'text-orange-400' : 'text-zinc-400'
                        return (
                          <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                            <td className="px-4 py-2.5 text-xs">
                              <span className={`px-1.5 py-0.5 rounded text-xs ${sevBadge}`}>{sev || '—'}</span>
                            </td>
                            <td className="px-4 py-2.5 text-xs font-mono text-zinc-400">{a.regulation_code ?? a.code ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-zinc-200 max-w-xs truncate">{a.title ?? a.message ?? '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-zinc-400">{deadline ? deadline.toLocaleDateString() : '—'}</td>
                            <td className={`px-4 py-2.5 text-xs font-mono ${daysColor}`}>
                              {daysLeft !== null ? daysLeft : '—'}
                            </td>
                            <td className="px-4 py-2.5 text-xs">
                              <button
                                onClick={() => acknowledgeAlert(a.id)}
                                className="px-2 py-1 text-xs text-zinc-400 border border-zinc-700 rounded hover:bg-zinc-800"
                              >
                                Acknowledge
                              </button>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
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
                <div className="mb-6">
                  <SkeletonTable rows={2} cols={2} />
                </div>
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
                  <button
                    onClick={fetchCrawlerStatus}
                    className="text-xs text-zinc-500 hover:text-zinc-300 underline ml-2"
                  >
                    retry
                  </button>
                </div>
              )}

              {crawlerEvents.length > 0 && (
                <div className="mt-6">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">Recent Crawl Events</div>
                  <div className="space-y-2">
                    {crawlerEvents.map((ev, i) => (
                      <div key={i} className="flex items-center gap-3 px-4 py-2.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm">
                        <span className="font-mono text-xs text-zinc-500 w-14 shrink-0">{ev.regulator ?? 'ALL'}</span>
                        <span className="text-zinc-300">{ev.crawled ?? 0} crawled</span>
                        <span className="text-zinc-600">·</span>
                        <span className="text-zinc-500">{ev.skipped_duplicate ?? 0} skipped</span>
                        {ev.errors > 0 && <span className="text-red-400 ml-auto">{ev.errors} errors</span>}
                        {ev.timestamp && <span className="text-zinc-600 text-xs ml-auto">{new Date(ev.timestamp).toLocaleTimeString()}</span>}
                      </div>
                    ))}
                  </div>
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
          {/* ── Home Dashboard ───────────────────────────────────────────── */}
          {active === 'home' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-1">Welcome to ComplianceOS</h2>
                <p className="text-sm text-zinc-500">AI-native regulatory infrastructure for LATAM regulated industries.</p>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div className="border border-zinc-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-mono font-bold mb-1">9</div>
                  <div className="text-xs text-zinc-500">Modules Active</div>
                </div>
                <div className="border border-zinc-800 rounded-lg p-4 text-center">
                  <div className="text-sm font-medium text-green-400 mb-1">Live</div>
                  <div className="text-xs text-zinc-500">Backend Status</div>
                </div>
                <div className="border border-zinc-800 rounded-lg p-4 text-center">
                  <div className="text-sm font-mono font-medium mb-1">polkorp</div>
                  <div className="text-xs text-zinc-500">Tenant</div>
                </div>
                <div className="border border-zinc-800 rounded-lg p-4 text-center">
                  <div className="text-sm font-medium mb-1">Production</div>
                  <div className="text-xs text-zinc-500">Environment</div>
                </div>
              </div>

              <div>
                <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Quick Links</div>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'regulatory', label: 'M1 — Regulatory Intel', desc: 'Parse + map regulations' },
                    { id: 'copilot', label: 'M2 — Compliance Copilot', desc: 'Multi-jurisdiction Q&A' },
                    { id: 'kyc', label: 'M3 — KYC/AML', desc: 'Screening + EDD' },
                    { id: 'monitoring', label: 'M4 — Monitoring', desc: 'Anomalies + drift' },
                    { id: 'governance', label: 'M5 — AI Governance', desc: 'Audit + safety' },
                    { id: 'evidence', label: 'M6 — Evidence', desc: 'PDF extraction' },
                    { id: 'workflows', label: 'M7 — Workflows', desc: 'Remediation workflows' },
                    { id: 'predictive', label: 'M8 — Predictive', desc: 'Risk & market simulation' },
                    { id: 'ticketing', label: 'M9 — Ticketing', desc: 'Compliance tickets' },
                  ].map(m => (
                    <button
                      key={m.id}
                      onClick={() => setActive(m.id as Module)}
                      className="border border-zinc-800 rounded-lg p-4 text-left hover:bg-zinc-900 transition"
                    >
                      <div className="text-sm font-medium mb-1">{m.label}</div>
                      <div className="text-xs text-zinc-500">{m.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── M7 Workflows ─────────────────────────────────────────────────── */}
          {active === 'workflows' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-2">M7 — Remediation Workflows</h2>
                <p className="text-sm text-zinc-500">Create and track AI-driven compliance remediation workflows.</p>
              </div>

              <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Create Workflow</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Workflow title</label>
                  <input
                    type="text"
                    value={workflowTitle}
                    onChange={e => setWorkflowTitle(e.target.value)}
                    placeholder="e.g. Remediate UIF Reporting Gap"
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Trigger source</label>
                  <input
                    type="text"
                    value={workflowTrigger}
                    onChange={e => setWorkflowTrigger(e.target.value)}
                    placeholder="e.g. M4 anomaly detection, manual review"
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Severity</label>
                  <select
                    value={workflowSeverity}
                    onChange={e => setWorkflowSeverity(e.target.value)}
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <button
                  onClick={createWorkflow}
                  disabled={workflowLoading || !workflowTitle.trim() || !workflowTrigger.trim()}
                  className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {workflowLoading ? 'Creating...' : 'Create Workflow'}
                </button>

                {workflowResult && (
                  <div className="space-y-2">
                    {(workflowResult.error || workflowResult.detail) && (
                      <div className="p-3 bg-red-950 border border-red-900 rounded text-sm text-red-200">
                        Error: {workflowResult.error ?? workflowResult.detail}
                      </div>
                    )}
                    {!workflowResult.error && !workflowResult.detail && (
                      <pre className="bg-zinc-900 border border-zinc-800 rounded p-3 text-xs overflow-auto">{JSON.stringify(workflowResult, null, 2)}</pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── M8 Predictive ────────────────────────────────────────────────── */}
          {active === 'predictive' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-2">M8 — Predictive Risk</h2>
                <p className="text-sm text-zinc-500">Jurisdiction risk scoring and market entry simulation.</p>
              </div>

              <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-zinc-500">Jurisdiction Risk Scores</div>
                  <button
                    onClick={fetchJurisdictionRisks}
                    disabled={jurisdictionRisksLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {jurisdictionRisksLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {jurisdictionRisksLoading && !jurisdictionRisks && (
                  <div className="text-xs text-zinc-600 py-4 text-center">Loading...</div>
                )}

                {jurisdictionRisks && !jurisdictionRisks.error && (
                  <pre className="bg-zinc-900 border border-zinc-800 rounded p-3 text-xs overflow-auto">{JSON.stringify(jurisdictionRisks, null, 2)}</pre>
                )}

                {jurisdictionRisks?.error && (
                  <div className="p-3 bg-red-950 border border-red-900 rounded text-sm text-red-200">
                    Error: {jurisdictionRisks.error}
                  </div>
                )}
              </div>

              <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Market Entry Simulation</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Business model</label>
                  <input
                    type="text"
                    value={simBusinessModel}
                    onChange={e => setSimBusinessModel(e.target.value)}
                    placeholder="e.g. Digital payments PSP, crypto exchange"
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Countries (comma-separated)</label>
                  <input
                    type="text"
                    value={simCountries}
                    onChange={e => setSimCountries(e.target.value)}
                    placeholder="AR,BR,MX"
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm font-mono focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <button
                  onClick={simulateMarketEntry}
                  disabled={simLoading || !simBusinessModel.trim()}
                  className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {simLoading ? 'Simulating...' : 'Simulate Market Entry'}
                </button>

                {simResult && (
                  <div className="space-y-2">
                    {(simResult.error || simResult.detail) && (
                      <div className="p-3 bg-red-950 border border-red-900 rounded text-sm text-red-200">
                        Error: {simResult.error ?? simResult.detail}
                      </div>
                    )}
                    {!simResult.error && !simResult.detail && (
                      <pre className="bg-zinc-900 border border-zinc-800 rounded p-3 text-xs overflow-auto">{JSON.stringify(simResult, null, 2)}</pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── M9 Ticketing ─────────────────────────────────────────────────── */}
          {active === 'ticketing' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold mb-2">M9 — Compliance Ticketing</h2>
                <p className="text-sm text-zinc-500">Create and manage compliance tickets. Track status from open to resolved.</p>
              </div>

              <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="text-xs uppercase tracking-wider text-zinc-500">Create Ticket</div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Title</label>
                  <input
                    type="text"
                    value={ticketTitle}
                    onChange={e => setTicketTitle(e.target.value)}
                    placeholder="e.g. Missing UIF SAR for period 2026-04"
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Description (optional)</label>
                  <textarea
                    value={ticketDesc}
                    onChange={e => setTicketDesc(e.target.value)}
                    placeholder="Additional context..."
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm min-h-20 focus:outline-none focus:border-zinc-600"
                  />
                </div>

                <div>
                  <label className="text-xs text-zinc-500 block mb-1">Priority</label>
                  <select
                    value={ticketPriority}
                    onChange={e => setTicketPriority(e.target.value)}
                    className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded text-sm focus:outline-none focus:border-zinc-600"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <button
                  onClick={createTicket}
                  disabled={ticketLoading || !ticketTitle.trim()}
                  className="px-4 py-2 bg-zinc-100 text-zinc-900 rounded text-sm font-medium hover:bg-white disabled:opacity-50"
                >
                  {ticketLoading ? 'Creating...' : 'Create Ticket'}
                </button>
              </div>

              <div className="border border-zinc-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-wider text-zinc-500">All Tickets</div>
                  <button
                    onClick={fetchTickets}
                    disabled={ticketsLoading}
                    className="text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-50"
                  >
                    {ticketsLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>

                {ticketsLoading && tickets.length === 0 ? (
                  <SkeletonTable rows={4} cols={5} />
                ) : tickets.length === 0 ? (
                  <div className="text-center py-8 text-zinc-600 text-sm border border-dashed border-zinc-800 rounded">
                    No tickets yet. Create one above.
                  </div>
                ) : (
                  <div className="border border-zinc-700 rounded overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-700 bg-zinc-900">
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Title</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Priority</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Status</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium">Created</th>
                          <th className="text-left px-4 py-2.5 text-xs text-zinc-500 font-medium"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {tickets.map((t: any, i: number) => {
                          const prioColor =
                            t.priority === 'critical' ? 'bg-red-950 text-red-400 border-red-900' :
                            t.priority === 'high' ? 'bg-orange-950 text-orange-400 border-orange-900' :
                            t.priority === 'medium' ? 'bg-yellow-950 text-yellow-400 border-yellow-900' :
                            'bg-zinc-800 text-zinc-400 border-zinc-700'
                          const statusColor =
                            t.status === 'resolved' || t.status === 'closed' ? 'text-green-400' :
                            t.status === 'in_progress' ? 'text-yellow-400' : 'text-zinc-400'
                          return (
                            <tr key={i} className="border-b border-zinc-800 last:border-0 hover:bg-zinc-900">
                              <td className="px-4 py-2.5 text-xs text-zinc-200 max-w-xs truncate">{t.title ?? '—'}</td>
                              <td className="px-4 py-2.5 text-xs">
                                <span className={`px-1.5 py-0.5 rounded border text-xs ${prioColor}`}>{t.priority ?? '—'}</span>
                              </td>
                              <td className={`px-4 py-2.5 text-xs font-mono ${statusColor}`}>{t.status ?? '—'}</td>
                              <td className="px-4 py-2.5 text-xs text-zinc-500">
                                {t.created_at ? new Date(t.created_at).toLocaleDateString() : '—'}
                              </td>
                              <td className="px-4 py-2.5 text-xs">
                                {t.status !== 'resolved' && t.status !== 'closed' && (
                                  <select
                                    defaultValue=""
                                    onChange={e => { if (e.target.value) updateTicketStatus(t.id, e.target.value) }}
                                    className="p-1 bg-zinc-900 border border-zinc-700 rounded text-xs focus:outline-none"
                                  >
                                    <option value="" disabled>Update</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="resolved">Resolved</option>
                                    <option value="closed">Closed</option>
                                  </select>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
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
