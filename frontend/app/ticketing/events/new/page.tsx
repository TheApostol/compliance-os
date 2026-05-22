'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp', 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

const COUNTRIES = ['AR', 'BR', 'MX', 'CO', 'CL', 'PE', 'UY', 'PY']

const COMPLIANCE_FLAGS = [
  { key: 'has_promoter_agreement',  label: 'Promoter Agreement',          blocker: true },
  { key: 'has_refund_policy',       label: 'Refund & Cancellation Policy', blocker: true },
  { key: 'has_consumer_terms',      label: 'Consumer Terms & Conditions',  blocker: true },
  { key: 'has_payment_processor',   label: 'Payment Processor Record',     blocker: true },
  { key: 'has_privacy_policy',      label: 'Privacy Policy' },
  { key: 'has_withdrawal_button',   label: 'Botón de Arrepentimiento',     blocker: true, arOnly: true },
  { key: 'has_cancellation_clause', label: 'Cancellation Clause' },
  { key: 'has_postponement_clause', label: 'Postponement Clause' },
  { key: 'has_marketing_consent',   label: 'Marketing Consent' },
  { key: 'has_anti_bot_protection', label: 'Anti-Bot Protection' },
  { key: 'has_electronic_invoice',  label: 'Electronic Invoice Setup' },
  { key: 'has_aaip_registration',   label: 'AAIP Registration',                        arOnly: true },
  { key: 'has_venue_authorization', label: 'Venue Authorization' },
  { key: 'has_event_permit',        label: 'Event Permit' },
  { key: 'has_chargeback_evidence', label: 'Chargeback Evidence Pack' },
]

const HIGH_RISK_FLAGS = [
  { key: 'resale_enabled',         label: 'Resale Marketplace Enabled' },
  { key: 'has_resale_policy',      label: 'Resale Policy Defined' },
  { key: 'crypto_payments_enabled', label: 'Crypto Payments Enabled' },
  { key: 'has_aml_kyc_controls',   label: 'AML/KYC Controls for Crypto' },
  { key: 'wallet_balance_enabled', label: 'Wallet/Stored Funds Enabled' },
]

export default function NewEvent() {
  const router = useRouter()

  const [form, setForm] = useState({
    name: '',
    description: '',
    country_code: 'AR',
    city: '',
    event_date: '',
    expected_attendance: '',
    service_fee_pct: '10',
    taxes_included: true,
    refund_sla_days: '10',
    complaint_sla_days: '15',
    resale_type: 'disabled',
    // compliance flags
    has_promoter_agreement: false,
    has_refund_policy: false,
    has_consumer_terms: false,
    has_payment_processor: false,
    has_privacy_policy: false,
    has_withdrawal_button: false,
    has_cancellation_clause: false,
    has_postponement_clause: false,
    has_marketing_consent: false,
    has_anti_bot_protection: false,
    has_electronic_invoice: false,
    has_aaip_registration: false,
    has_venue_authorization: false,
    has_event_permit: false,
    has_chargeback_evidence: false,
    resale_enabled: false,
    has_resale_policy: false,
    crypto_payments_enabled: false,
    has_aml_kyc_controls: false,
    wallet_balance_enabled: false,
  } as Record<string, any>)

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  function toggle(key: string) {
    setForm(f => ({ ...f, [key]: !f[key] }))
  }

  async function submit() {
    if (!form.name.trim() || !form.country_code) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const body: Record<string, any> = {
        ...form,
        expected_attendance: form.expected_attendance ? parseInt(form.expected_attendance) : null,
        service_fee_pct: parseFloat(form.service_fee_pct) || 0,
        refund_sla_days: parseInt(form.refund_sla_days) || 10,
        complaint_sla_days: parseInt(form.complaint_sla_days) || 15,
        event_date: form.event_date || null,
        resale_type: form.resale_enabled ? (form.resale_type || 'controlled') : null,
      }
      const res = await fetch(`${API}/api/v1/ticketing/events`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (data.success) {
        setResult(data)
        setTimeout(() => router.push(`/ticketing/events/${data.event.id}/risk`), 1500)
      } else {
        setError(data.detail ?? JSON.stringify(data))
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const isAR = form.country_code === 'AR'

  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold">New Event</h1>
        <p className="text-sm text-zinc-500 mt-1">
          Complete the compliance checklist to get a launch decision
        </p>
      </div>

      {/* Basic info */}
      <div className="border border-zinc-800 rounded-lg p-6 space-y-4">
        <div className="text-xs uppercase tracking-wider text-zinc-500">Event Information</div>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="text-xs text-zinc-500 block mb-1">Event Name *</label>
            <input
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              placeholder="e.g. Lollapalooza Buenos Aires 2026"
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Country *</label>
            <select
              value={form.country_code}
              onChange={e => setForm(f => ({ ...f, country_code: e.target.value }))}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
            >
              {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">City</label>
            <input
              value={form.city}
              onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
              placeholder="Buenos Aires"
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Event Date</label>
            <input
              type="datetime-local"
              value={form.event_date}
              onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Expected Attendance</label>
            <input
              type="number"
              value={form.expected_attendance}
              onChange={e => setForm(f => ({ ...f, expected_attendance: e.target.value }))}
              placeholder="5000"
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Service Fee %</label>
            <input
              type="number"
              value={form.service_fee_pct}
              onChange={e => setForm(f => ({ ...f, service_fee_pct: e.target.value }))}
              placeholder="10"
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Refund SLA (days)</label>
            <input
              type="number"
              value={form.refund_sla_days}
              onChange={e => setForm(f => ({ ...f, refund_sla_days: e.target.value }))}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none focus:border-zinc-600"
            />
          </div>
        </div>
      </div>

      {/* Compliance flags */}
      <div className="border border-zinc-800 rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-wider text-zinc-500">Compliance Controls</div>
          <span className="text-xs text-red-400">* BLOCKER = event cannot launch without this</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {COMPLIANCE_FLAGS.map(flag => {
            if (flag.arOnly && !isAR) return null
            return (
              <label
                key={flag.key}
                className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${
                  form[flag.key]
                    ? 'border-green-800 bg-green-950/20'
                    : flag.blocker
                    ? 'border-red-900 bg-red-950/10'
                    : 'border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <input
                  type="checkbox"
                  checked={!!form[flag.key]}
                  onChange={() => toggle(flag.key)}
                  className="rounded"
                />
                <span className="text-sm">
                  {flag.label}
                  {flag.blocker && !form[flag.key] && (
                    <span className="ml-1 text-xs text-red-500">*</span>
                  )}
                </span>
              </label>
            )
          })}
        </div>
      </div>

      {/* High-risk features */}
      <div className="border border-yellow-900 rounded-lg p-6 space-y-4">
        <div className="text-xs uppercase tracking-wider text-yellow-600">High-Risk Features</div>
        <p className="text-xs text-yellow-700">
          Enabling these features without corresponding controls will increase risk score.
        </p>
        <div className="grid grid-cols-2 gap-2">
          {HIGH_RISK_FLAGS.map(flag => (
            <label
              key={flag.key}
              className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${
                form[flag.key]
                  ? 'border-yellow-800 bg-yellow-950/20'
                  : 'border-zinc-800 hover:border-zinc-700'
              }`}
            >
              <input
                type="checkbox"
                checked={!!form[flag.key]}
                onChange={() => toggle(flag.key)}
                className="rounded"
              />
              <span className="text-sm">{flag.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Actions */}
      {error && (
        <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
          Error: {error}
        </div>
      )}
      {result?.success && (
        <div className="p-4 bg-green-950 border border-green-900 rounded-md text-sm text-green-200">
          Event created! Decision: <strong>{result.event?.launch_decision}</strong>. Redirecting to risk assessment…
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={submit}
          disabled={loading || !form.name.trim()}
          className="px-6 py-2.5 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
        >
          {loading ? 'Running compliance check…' : 'Create Event & Run Risk Assessment'}
        </button>
        <button
          onClick={() => router.back()}
          className="px-4 py-2.5 border border-zinc-800 rounded-md text-sm hover:bg-zinc-900"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
