'use client'

import { useState } from 'react'

const RISK_COLORS: Record<string, { border: string; label: string; badge: string }> = {
  CRITICAL: { border: '#FF4D6A', label: '#FF4D6A', badge: 'rgba(255,77,106,0.12)' },
  HIGH:     { border: '#FF8C42', label: '#FF8C42', badge: 'rgba(255,140,66,0.12)' },
  MEDIUM:   { border: '#FFE135', label: '#0A0A0A', badge: 'rgba(255,225,53,0.12)' },
  LOW:      { border: '#888888', label: '#888888', badge: 'rgba(136,136,136,0.12)' },
}

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

interface KYCCardProps {
  kycCase: KYCCase
  onGenerateRoF?: (kycCase: KYCCase) => void
}

export function KYCCard({ kycCase, onGenerateRoF }: KYCCardProps) {
  const [expanded, setExpanded] = useState(false)
  const riskStyle = RISK_COLORS[kycCase.risk_level] || RISK_COLORS['LOW']

  return (
    <div style={{
      background: '#111111',
      border: '1px solid #242424',
      borderLeft: `3px solid ${riskStyle.border}`,
      borderRadius: 16,
      overflow: 'hidden',
      marginBottom: 8,
    }}>
      {/* Collapsed */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: '#FFFFFF', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {kycCase.name}
            </span>
            <span style={{
              padding: '2px 10px',
              borderRadius: 24,
              fontSize: 11,
              fontWeight: 700,
              background: riskStyle.badge,
              color: riskStyle.label,
              border: `1px solid ${riskStyle.border}`,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}>
              {kycCase.risk_level}
            </span>
          </div>
          <div style={{ fontSize: 12, color: '#888888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {kycCase.flag_text}
          </div>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 11, color: '#555555' }}>SLA</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: kycCase.sla_days <= 3 ? '#FF4D6A' : '#FFE135' }}>
            {kycCase.sla_days}d
          </div>
        </div>
        <span style={{ color: '#555555', fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
      </button>

      {/* Expanded */}
      {expanded && (
        <div style={{ padding: '0 18px 18px' }}>
          {/* AI Analysis */}
          <div style={{
            background: '#1A1A1A',
            border: '1px solid #242424',
            borderRadius: 12,
            padding: 14,
            marginBottom: 12,
          }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#FFE135', letterSpacing: '0.5px', marginBottom: 6, textTransform: 'uppercase' }}>
              ✦ Análisis AI
            </div>
            <div style={{ fontSize: 13, color: '#CCCCCC', lineHeight: 1.6 }}>
              {kycCase.ai_analysis}
            </div>
          </div>

          {/* Regulations */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
            {kycCase.applicable_regulations.map((reg, i) => (
              <span key={i} style={{
                background: 'rgba(255,225,53,0.08)',
                color: '#FFE135',
                border: '1px solid rgba(255,225,53,0.2)',
                borderRadius: 24,
                fontSize: 11,
                fontWeight: 500,
                padding: '3px 10px',
              }}>
                {reg}
              </span>
            ))}
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button style={{
              padding: '8px 18px',
              background: '#FFE135',
              color: '#0A0A0A',
              border: 'none',
              borderRadius: 12,
              fontWeight: 700,
              fontSize: 12,
              cursor: 'pointer',
            }}>
              APROBAR EDD
            </button>
            <button
              onClick={() => onGenerateRoF?.(kycCase)}
              style={{
                padding: '8px 18px',
                background: 'transparent',
                color: '#FF8C42',
                border: '1px solid #FF8C42',
                borderRadius: 12,
                fontWeight: 700,
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              GENERAR RoF
            </button>
            <button style={{
              padding: '8px 18px',
              background: '#242424',
              color: '#888888',
              border: 'none',
              borderRadius: 12,
              fontWeight: 700,
              fontSize: 12,
              cursor: 'pointer',
            }}>
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
