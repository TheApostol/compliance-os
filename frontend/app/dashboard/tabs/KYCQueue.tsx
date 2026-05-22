'use client'

import { useState } from 'react'
import { KYCCard } from '../components/KYCCard'
import { useKYCQueue } from '../hooks/useDashboard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface KYCCase {
  id: string
  name: string
  risk_level: string
  flag_text: string
  sla_days: number
  ai_analysis: string
  applicable_regulations: string[]
  status: string
}

interface KYCQueueProps {
  token: string | null
}

interface RoFResult {
  rof_draft: string
  audit_id: string
  model: string
  case_id: string
}

export function KYCQueue({ token }: KYCQueueProps) {
  const { data } = useKYCQueue(token)
  const [riskFilter, setRiskFilter] = useState('all')
  const [rofModal, setRofModal] = useState<{ kycCase: KYCCase; result: RoFResult | null; loading: boolean } | null>(null)

  const cases: KYCCase[] = data?.cases ?? []

  const filtered = riskFilter === 'all'
    ? cases
    : cases.filter(c => c.risk_level === riskFilter)

  async function generateRoF(kycCase: KYCCase) {
    setRofModal({ kycCase, result: null, loading: true })

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Tenant-Id': 'lemon-cash',
      }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch(`${API_URL}/api/v1/kyc/generate-rof`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          case_id: kycCase.id,
          case_name: kycCase.name,
          risk_level: kycCase.risk_level,
        }),
      })
      const result: RoFResult = await res.json()
      setRofModal(prev => prev ? { ...prev, result, loading: false } : null)
    } catch (e) {
      console.error('RoF generation failed', e)
      setRofModal(prev => prev ? { ...prev, loading: false } : null)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Cola KYC / AML</h2>
        <p style={{ fontSize: 13, color: '#888888', margin: '4px 0 0' }}>
          {data?.total ?? 0} casos activos · gestione investigaciones y reportes UIF
        </p>
      </div>

      {/* Risk filter */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
        {['all', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
          <button
            key={level}
            onClick={() => setRiskFilter(level)}
            style={{
              padding: '6px 14px',
              borderRadius: 12,
              border: riskFilter === level ? '1px solid #FFE135' : '1px solid #242424',
              background: riskFilter === level ? 'rgba(255,225,53,0.12)' : '#111111',
              color: riskFilter === level ? '#FFE135' : '#888888',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {level === 'all' ? 'Todos' : level}
          </button>
        ))}
      </div>

      {/* Cases */}
      {filtered.length === 0 ? (
        <div style={{
          background: '#111111',
          border: '1px solid #242424',
          borderRadius: 16,
          padding: 40,
          textAlign: 'center',
          color: '#555555',
          fontSize: 14,
        }}>
          No hay casos en cola
        </div>
      ) : (
        filtered.map((c, i) => (
          <KYCCard
            key={c.id || i}
            kycCase={c}
            onGenerateRoF={generateRoF}
          />
        ))
      )}

      {/* RoF Modal */}
      {rofModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20,
        }}>
          <div style={{
            background: '#111111',
            border: '1px solid #242424',
            borderRadius: 16,
            padding: 28,
            maxWidth: 680,
            width: '100%',
            maxHeight: '80vh',
            overflowY: 'auto',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#FFFFFF' }}>
                  Borrador RoS / RoF
                </h3>
                <div style={{ fontSize: 12, color: '#888888', marginTop: 2 }}>
                  Caso: {rofModal.kycCase.name}
                </div>
              </div>
              <button
                onClick={() => setRofModal(null)}
                style={{ background: 'transparent', border: 'none', color: '#888888', fontSize: 20, cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {rofModal.loading ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <div style={{ color: '#FFE135', fontSize: 14, marginBottom: 8 }}>Generando borrador con AI...</div>
                <div style={{ color: '#555555', fontSize: 12 }}>Esto puede tomar 15-30 segundos</div>
              </div>
            ) : rofModal.result ? (
              <>
                <div style={{
                  background: '#1A1A1A',
                  border: '1px solid #242424',
                  borderRadius: 12,
                  padding: 16,
                  fontFamily: 'monospace',
                  fontSize: 12,
                  color: '#CCCCCC',
                  lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                  marginBottom: 16,
                }}>
                  {rofModal.result.rof_draft}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 11, color: '#555555' }}>
                    audit: {rofModal.result.audit_id} · modelo: {rofModal.result.model}
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={() => {
                        const text = rofModal.result?.rof_draft || ''
                        navigator.clipboard.writeText(text).catch(() => {})
                      }}
                      style={{
                        padding: '8px 16px',
                        background: '#242424',
                        color: '#CCCCCC',
                        border: 'none',
                        borderRadius: 10,
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      Copiar
                    </button>
                    <button
                      onClick={() => setRofModal(null)}
                      style={{
                        padding: '8px 16px',
                        background: '#FFE135',
                        color: '#0A0A0A',
                        border: 'none',
                        borderRadius: 10,
                        fontWeight: 700,
                        fontSize: 12,
                        cursor: 'pointer',
                      }}
                    >
                      Listo
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div style={{ color: '#FF4D6A', fontSize: 14 }}>Error generando el borrador. Intente de nuevo.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
