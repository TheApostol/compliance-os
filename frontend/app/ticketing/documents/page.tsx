'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp', 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

const DOCUMENT_TYPES = [
  { value: 'promoter_agreement',       label: 'Promoter Compliance Agreement',       desc: 'Platform–promoter liability allocation contract' },
  { value: 'consumer_terms',           label: 'Consumer Terms & Conditions',          desc: 'Purchase terms including transfer and refund rights' },
  { value: 'refund_policy',            label: 'Refund & Cancellation Policy',         desc: 'Country-specific refund obligations and SLA' },
  { value: 'privacy_policy',           label: 'Privacy Policy',                       desc: 'LGPD/PDPA-compliant data protection statement' },
  { value: 'withdrawal_notice',        label: 'Botón de Arrepentimiento Notice',       desc: 'Argentina-specific withdrawal right notice (AR only)' },
  { value: 'resale_policy',            label: 'Resale & Anti-Scalping Policy',         desc: 'Secondary market rules and price cap enforcement' },
  { value: 'compliance_checklist',     label: 'Compliance Checklist PDF',             desc: 'Printable checklist of all controls with status' },
  { value: 'risk_summary',             label: 'Risk Assessment Summary',              desc: 'Executive summary of risk dimensions and launch decision' },
  { value: 'chargeback_evidence',      label: 'Chargeback Evidence Pack',             desc: 'Pre-packaged dispute resolution evidence template' },
  { value: 'data_processing_agreement', label: 'Data Processing Agreement (DPA)',    desc: 'GDPR/LGPD-compliant DPA for processors' },
  { value: 'force_majeure_clause',     label: 'Force Majeure Clause',                 desc: 'Epidemic / disaster / government restriction coverage' },
]

const MOCK_EVENTS = [
  { id: 'e1', name: 'Lollapalooza Argentina 2026' },
  { id: 'e2', name: 'Buenos Aires Tech Summit' },
  { id: 'e3', name: 'Rock in Rio São Paulo' },
]

type GeneratedDoc = {
  document_type: string
  content: string
  created_at: string
}

export default function DocumentsPage() {
  const searchParams = useSearchParams()
  const [events, setEvents] = useState<any[]>([])
  const [selectedEvent, setSelectedEvent] = useState(searchParams.get('event_id') ?? '')
  const [selectedType, setSelectedType] = useState('')
  const [generating, setGenerating] = useState(false)
  const [doc, setDoc] = useState<GeneratedDoc | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/ticketing/events`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setEvents(d.events ?? MOCK_EVENTS))
      .catch(() => setEvents(MOCK_EVENTS))
  }, [])

  async function generate() {
    if (!selectedEvent || !selectedType) return
    setGenerating(true)
    setError(null)
    setDoc(null)
    try {
      const res = await fetch(`${API}/api/v1/ticketing/documents/generate`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          event_id: selectedEvent,
          document_type: selectedType,
        }),
      })
      const d = await res.json()
      if (d.content) {
        setDoc({ document_type: selectedType, content: d.content, created_at: new Date().toISOString() })
      } else {
        setError(d.detail ?? 'Failed to generate document')
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  function download() {
    if (!doc) return
    const blob = new Blob([doc.content], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${doc.document_type}_${selectedEvent}.txt`
    a.click()
  }

  const selectedDocType = DOCUMENT_TYPES.find(d => d.value === selectedType)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Document Generation</h1>
        <p className="text-sm text-zinc-500 mt-1">AI-generated compliance documents tailored to your event and country</p>
      </div>

      {/* Generator */}
      <div className="border border-zinc-800 rounded-lg p-6 space-y-5">
        <div className="text-xs uppercase tracking-wider text-zinc-500">Generate Document</div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Event</label>
            <select
              value={selectedEvent}
              onChange={e => setSelectedEvent(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
            >
              <option value="">Select event…</option>
              {events.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-500 block mb-1">Document Type</label>
            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
            >
              <option value="">Select document type…</option>
              {DOCUMENT_TYPES.map(dt => <option key={dt.value} value={dt.value}>{dt.label}</option>)}
            </select>
          </div>
        </div>

        {selectedDocType && (
          <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-md">
            <p className="text-xs text-zinc-400">{selectedDocType.desc}</p>
          </div>
        )}

        <button
          onClick={generate}
          disabled={generating || !selectedEvent || !selectedType}
          className="px-5 py-2.5 bg-zinc-100 text-zinc-900 rounded-md text-sm font-medium hover:bg-white disabled:opacity-50"
        >
          {generating ? 'Generating…' : 'Generate with AI'}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-950 border border-red-900 rounded-md text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Document viewer */}
      {doc && (
        <div className="border border-zinc-800 rounded-lg overflow-hidden">
          <div className="px-5 py-3 bg-zinc-900 border-b border-zinc-800 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-zinc-200">
                {DOCUMENT_TYPES.find(d => d.value === doc.document_type)?.label ?? doc.document_type}
              </div>
              <div className="text-xs text-zinc-500">
                Generated {new Date(doc.created_at).toLocaleString()}
              </div>
            </div>
            <button
              onClick={download}
              className="px-3 py-1.5 border border-zinc-700 rounded-md text-xs hover:bg-zinc-800 transition-colors"
            >
              Download .txt
            </button>
          </div>
          <div className="p-6 font-mono text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto bg-zinc-950">
            {doc.content}
          </div>
        </div>
      )}

      {/* Document type catalog */}
      <div>
        <div className="text-sm font-semibold text-zinc-300 mb-4">Available Document Types</div>
        <div className="grid grid-cols-2 gap-3">
          {DOCUMENT_TYPES.map(dt => (
            <button
              key={dt.value}
              onClick={() => setSelectedType(dt.value)}
              className={`p-4 border rounded-lg text-left transition-colors hover:border-zinc-600 ${
                selectedType === dt.value ? 'border-zinc-500 bg-zinc-800/50' : 'border-zinc-800'
              }`}
            >
              <div className="text-sm font-medium mb-1">{dt.label}</div>
              <div className="text-xs text-zinc-500">{dt.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
