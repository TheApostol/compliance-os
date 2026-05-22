'use client'

const REGULATOR_COLORS: Record<string, string> = {
  BCRA: '#4A9FD4',
  UIF: '#A78BFA',
  CNV: '#FF8C42',
  FATF: '#00D68F',
  OFAC: '#FF4D6A',
  BACEN: '#FFE135',
  CMF: '#4A9FD4',
  SFC: '#A78BFA',
}

interface FeedItemProps {
  regulator: string
  title: string
  timestamp?: string
  country?: string
  onAnalyze?: () => void
}

function timeAgo(timestamp?: string): string {
  if (!timestamp) return 'reciente'
  try {
    const diff = Date.now() - new Date(timestamp).getTime()
    const hours = Math.floor(diff / 3_600_000)
    if (hours < 1) return 'hace < 1h'
    if (hours < 24) return `hace ${hours}h`
    const days = Math.floor(hours / 24)
    return `hace ${days}d`
  } catch {
    return 'reciente'
  }
}

export function FeedItem({ regulator, title, timestamp, onAnalyze }: FeedItemProps) {
  const color = REGULATOR_COLORS[regulator.toUpperCase()] || '#888888'

  return (
    <div style={{
      background: '#111111',
      border: '1px solid #242424',
      borderLeft: `3px solid ${color}`,
      borderRadius: 12,
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 6,
    }}>
      <span style={{
        background: `${color}20`,
        color,
        border: `1px solid ${color}40`,
        borderRadius: 8,
        fontSize: 11,
        fontWeight: 700,
        padding: '2px 8px',
        whiteSpace: 'nowrap',
        flexShrink: 0,
      }}>
        {regulator.toUpperCase()}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: '#CCCCCC', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {title}
        </div>
        <div style={{ fontSize: 11, color: '#555555', marginTop: 2 }}>
          {timeAgo(timestamp)}
        </div>
      </div>
      {onAnalyze && (
        <button
          onClick={onAnalyze}
          style={{
            background: 'transparent',
            color: '#FFE135',
            border: 'none',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            padding: '4px 8px',
          }}
        >
          Analizar →
        </button>
      )}
    </div>
  )
}
