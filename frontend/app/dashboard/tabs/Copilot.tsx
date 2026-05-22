'use client'

import { CopilotChat } from '../components/CopilotChat'
import { useCannedQuestions } from '../hooks/useDashboard'

interface CopilotProps {
  token: string | null
}

const RAG_SOURCES = [
  { label: 'BCRA', color: '#4A9FD4' },
  { label: 'UIF', color: '#A78BFA' },
  { label: 'CNV', color: '#FF8C42' },
  { label: 'FATF', color: '#00D68F' },
  { label: 'OFAC', color: '#FF4D6A' },
]

export function Copilot({ token }: CopilotProps) {
  const { data: cannedData } = useCannedQuestions(token, 'CRYPTO_VASP')
  const questions: string[] = cannedData?.questions ?? []

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Compliance Copilot</h2>
        <p style={{ fontSize: 13, color: '#888888', margin: '4px 0 0' }}>
          Asistente AI especializado en regulación LATAM VASP — BCRA, UIF, FATF, OFAC
        </p>
      </div>

      {/* RAG Status pills */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        <span style={{ fontSize: 11, color: '#555555', alignSelf: 'center' }}>Fuentes indexadas:</span>
        {RAG_SOURCES.map(s => (
          <span key={s.label} style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 12px',
            borderRadius: 24,
            background: `${s.color}18`,
            color: s.color,
            border: `1px solid ${s.color}40`,
            fontSize: 11,
            fontWeight: 600,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, display: 'inline-block' }} />
            {s.label}
          </span>
        ))}
      </div>

      {/* Chat */}
      <div style={{
        background: '#111111',
        border: '1px solid #242424',
        borderRadius: 16,
        padding: 20,
      }}>
        <CopilotChat token={token} cannedQuestions={questions} />
      </div>
    </div>
  )
}
