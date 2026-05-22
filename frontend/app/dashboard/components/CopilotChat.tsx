'use client'

import { useState, useRef, useEffect } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Message {
  id: string
  role: 'user' | 'ai'
  text: string
  auditId?: string
  model?: string
  latencyMs?: number
}

interface CopilotChatProps {
  token: string | null
  cannedQuestions?: string[]
}

function LoadingDots() {
  return (
    <div style={{ display: 'flex', gap: 4, padding: '8px 0' }}>
      {[0, 1, 2].map(i => (
        <div
          key={i}
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#FFE135',
            animation: 'bounce 1.2s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}

export function CopilotChat({ token, cannedQuestions = [] }: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: text.trim(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Tenant-Id': 'lemon-cash',
      }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch(`${API_URL}/api/v1/copilot/ask`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ question: text.trim(), deep_mode: false }),
      })
      const data = await res.json()

      const aiMsg: Message = {
        id: `a-${Date.now()}`,
        role: 'ai',
        text: data.answer || data.error || 'No se pudo obtener una respuesta.',
        auditId: data.audit_id,
        model: data.model_used,
        latencyMs: data.latency_ms,
      }
      setMessages(prev => [...prev, aiMsg])
    } catch (e: unknown) {
      const errorMsg = e instanceof Error ? e.message : 'Error de conexión'
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'ai',
        text: `Error: ${errorMsg}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 400 }}>
      {/* Canned questions */}
      {cannedQuestions.length > 0 && messages.length === 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: '#555555', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Preguntas frecuentes
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {cannedQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => sendMessage(q)}
                style={{
                  textAlign: 'left',
                  background: '#1A1A1A',
                  border: '1px solid #242424',
                  borderRadius: 12,
                  padding: '10px 14px',
                  fontSize: 13,
                  color: '#CCCCCC',
                  cursor: 'pointer',
                  lineHeight: 1.4,
                  transition: 'border-color 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = '#FFE135')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#242424')}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        marginBottom: 16,
        maxHeight: 480,
      }}>
        {messages.map(msg => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div style={{
              maxWidth: '80%',
              padding: '10px 14px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '4px 16px 16px 16px',
              background: msg.role === 'user' ? '#FFE135' : '#1A1A1A',
              color: msg.role === 'user' ? '#0A0A0A' : '#CCCCCC',
              fontSize: 13,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {msg.text}
            </div>
            {msg.role === 'ai' && (msg.auditId || msg.model) && (
              <div style={{ fontSize: 10, color: '#555555', marginTop: 4, paddingLeft: 2 }}>
                {[msg.auditId, msg.model, msg.latencyMs ? `${msg.latencyMs}ms` : null].filter(Boolean).join(' · ')}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <div style={{
              background: '#1A1A1A',
              borderRadius: '4px 16px 16px 16px',
              padding: '8px 16px',
            }}>
              <LoadingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        display: 'flex',
        gap: 8,
        alignItems: 'flex-end',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              sendMessage(input)
            }
          }}
          placeholder="Pregunta sobre regulación BCRA, UIF, FATF..."
          rows={2}
          style={{
            flex: 1,
            background: '#1A1A1A',
            border: '1px solid #242424',
            borderRadius: 12,
            padding: '10px 14px',
            fontSize: 13,
            color: '#FFFFFF',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.5,
          }}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            width: 44,
            height: 44,
            borderRadius: '50%',
            background: '#FFE135',
            border: 'none',
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() ? 0.5 : 1,
            fontSize: 18,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          ↑
        </button>
      </div>
    </div>
  )
}
