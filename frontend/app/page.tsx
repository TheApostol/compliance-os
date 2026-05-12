'use client'

import { useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Module = 'copilot' | 'kyc' | 'monitoring' | 'governance' | 'regulatory'

export default function Home() {
  const [active, setActive] = useState<Module>('copilot')
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
        headers: { 'Content-Type': 'application/json', 'X-Tenant-Id': 'polkorp' },
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

  return (
    <main className="min-h-screen">
      <header className="border-b border-zinc-800 px-8 py-5">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">ComplianceOS</h1>
            <p className="text-sm text-zinc-500">AI-native compliance for LATAM regulated industries</p>
          </div>
          <div className="text-xs text-zinc-500">
            tenant: <span className="text-zinc-300 font-mono">polkorp</span>
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

          {active !== 'copilot' && (
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
