'use client'

import { useState, useEffect, useRef } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('cos_token') : null
  const h: Record<string, string> = { 'X-Tenant-Id': 'polkorp', 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  structured?: {
    risk_level?: string
    missing_controls?: string[]
    recommended_actions?: string[]
    country_specific_notes?: string
    required_documents?: string[]
  }
  timestamp: Date
}

const RISK_COLORS: Record<string, string> = {
  critical: 'text-red-400',
  high:     'text-orange-400',
  medium:   'text-yellow-400',
  low:      'text-green-400',
}

const EXAMPLE_QUESTIONS = [
  'What are the mandatory controls for selling tickets in Argentina?',
  'Is the Botón de Arrepentimiento required for all LATAM countries?',
  'What documents do I need before launching an event in Brazil?',
  'How do I handle chargebacks for events cancelled due to force majeure?',
  'What is the maximum penalty for missing AAIP registration in Argentina?',
  'Do I need a promoter agreement if I am both promoter and ticketer?',
]

const MOCK_EVENTS = [
  { id: 'e1', name: 'Lollapalooza Argentina 2026', country_code: 'AR' },
  { id: 'e2', name: 'Buenos Aires Tech Summit', country_code: 'AR' },
  { id: 'e3', name: 'Rock in Rio São Paulo', country_code: 'BR' },
]

export default function AICopilot() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [deepMode, setDeepMode] = useState(false)
  const [events, setEvents] = useState<any[]>([])
  const [selectedEvent, setSelectedEvent] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/ticketing/events`, { headers: authHeaders() })
      .then(r => r.json())
      .then(d => setEvents(d.events ?? MOCK_EVENTS))
      .catch(() => setEvents(MOCK_EVENTS))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(question?: string) {
    const q = (question ?? input).trim()
    if (!q || loading) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: q,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const body: Record<string, any> = { question: q, deep_mode: deepMode }
      if (selectedEvent) body.event_id = selectedEvent

      const res = await fetch(`${API}/api/v1/ticketing/ai-copilot`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(body),
      })
      const d = await res.json()

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: d.answer?.summary ?? d.answer ?? 'I was unable to generate a response. Please try again.',
        structured: d.answer,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I am unable to connect to the AI service at the moment. Please ensure the backend is running.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }

  function clear() {
    setMessages([])
  }

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">AI Compliance Copilot</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Ask anything about ticketing compliance in LATAM</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedEvent}
            onChange={e => setSelectedEvent(e.target.value)}
            className="px-3 py-1.5 bg-zinc-900 border border-zinc-800 rounded-md text-sm focus:outline-none"
          >
            <option value="">No event context</option>
            {events.map(ev => <option key={ev.id} value={ev.id}>{ev.name}</option>)}
          </select>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <div
              onClick={() => setDeepMode(!deepMode)}
              className={`relative w-10 h-5 rounded-full transition-colors ${deepMode ? 'bg-blue-600' : 'bg-zinc-700'}`}
            >
              <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${deepMode ? 'translate-x-5' : ''}`} />
            </div>
            <span className="text-zinc-400">Deep mode</span>
          </label>
          {messages.length > 0 && (
            <button onClick={clear} className="text-xs text-zinc-500 hover:text-zinc-300">Clear</button>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto border border-zinc-800 rounded-lg p-4 space-y-4 mb-4 bg-zinc-950/50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-2xl mb-3">⚖️</div>
            <div className="text-zinc-400 text-sm mb-6">
              Ask me about compliance requirements, regulations, or specific event risks across LATAM.
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-xl">
              {EXAMPLE_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => send(q)}
                  className="p-3 border border-zinc-800 rounded-lg text-xs text-zinc-400 text-left hover:border-zinc-600 hover:text-zinc-200 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                  {msg.role === 'user' ? (
                    <div className="bg-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-100">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-sm text-zinc-200 leading-relaxed">
                        {msg.content}
                      </div>

                      {msg.structured?.risk_level && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-zinc-500">Risk level:</span>
                          <span className={`text-xs font-medium uppercase ${RISK_COLORS[msg.structured.risk_level] ?? 'text-zinc-400'}`}>
                            {msg.structured.risk_level}
                          </span>
                        </div>
                      )}

                      {msg.structured?.missing_controls && msg.structured.missing_controls.length > 0 && (
                        <div className="bg-zinc-900 border border-red-900/50 rounded-lg p-3">
                          <div className="text-xs font-semibold text-red-400 mb-2">Missing Controls</div>
                          <ul className="space-y-1">
                            {msg.structured.missing_controls.map((c, i) => (
                              <li key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
                                <span className="text-red-600 mt-0.5">•</span>{c}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {msg.structured?.recommended_actions && msg.structured.recommended_actions.length > 0 && (
                        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                          <div className="text-xs font-semibold text-zinc-400 mb-2">Recommended Actions</div>
                          <ol className="space-y-1">
                            {msg.structured.recommended_actions.map((a, i) => (
                              <li key={i} className="text-xs text-zinc-400 flex items-start gap-1.5">
                                <span className="text-zinc-600 mt-0.5 shrink-0">{i + 1}.</span>{a}
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}

                      {msg.structured?.country_specific_notes && (
                        <div className="bg-zinc-900 border border-yellow-900/50 rounded-lg p-3">
                          <div className="text-xs font-semibold text-yellow-600 mb-1">Country-Specific Notes</div>
                          <p className="text-xs text-zinc-400">{msg.structured.country_specific_notes}</p>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="text-xs text-zinc-600 mt-1 px-1">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-2 h-2 bg-zinc-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="Ask about compliance requirements, regulations, or specific risks…"
          disabled={loading}
          className="flex-1 px-4 py-3 bg-zinc-900 border border-zinc-800 rounded-lg text-sm focus:outline-none focus:border-zinc-600 disabled:opacity-50"
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-zinc-100 text-zinc-900 rounded-lg text-sm font-medium hover:bg-white disabled:opacity-50 shrink-0"
        >
          {loading ? '…' : 'Send'}
        </button>
      </div>
    </div>
  )
}
