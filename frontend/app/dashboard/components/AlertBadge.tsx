'use client'

interface AlertBadgeProps {
  severity: string
  label?: string
}

const SEVERITY_STYLES: Record<string, { bg: string; color: string; border: string }> = {
  CRITICAL: { bg: '#FF4D6A', color: '#FFFFFF', border: '#FF4D6A' },
  HIGH:     { bg: 'rgba(255,140,66,0.15)', color: '#FF8C42', border: '#FF8C42' },
  MEDIUM:   { bg: 'rgba(255,225,53,0.12)', color: '#0A0A0A', border: '#FFE135' },
  LOW:      { bg: 'rgba(136,136,136,0.15)', color: '#888888', border: '#555555' },
  critical: { bg: '#FF4D6A', color: '#FFFFFF', border: '#FF4D6A' },
  high:     { bg: 'rgba(255,140,66,0.15)', color: '#FF8C42', border: '#FF8C42' },
  medium:   { bg: 'rgba(255,225,53,0.12)', color: '#0A0A0A', border: '#FFE135' },
  low:      { bg: 'rgba(136,136,136,0.15)', color: '#888888', border: '#555555' },
}

export function AlertBadge({ severity, label }: AlertBadgeProps) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES['LOW']
  const text = label || severity.toUpperCase()

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 10px',
      borderRadius: 24,
      fontSize: 11,
      fontWeight: 600,
      background: style.bg,
      color: style.color,
      border: `1px solid ${style.border}`,
      letterSpacing: '0.3px',
      whiteSpace: 'nowrap',
    }}>
      {text}
    </span>
  )
}
