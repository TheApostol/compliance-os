'use client'

import { FeedItem } from '../components/FeedItem'
import { useSSE } from '../hooks/useSSE'
import { useCrawlerStatus } from '../hooks/useDashboard'

interface RegFeedProps {
  token: string | null
}

const MOCK_FEED = [
  { id: '1', regulator: 'UIF', title: 'Resolución 156/2024 — Nuevas obligaciones para VASPs', timestamp: new Date(Date.now() - 2 * 3_600_000).toISOString(), country: 'AR' },
  { id: '2', regulator: 'BCRA', title: 'Comunicación A 7825 — Requisitos Travel Rule 2024', timestamp: new Date(Date.now() - 5 * 3_600_000).toISOString(), country: 'AR' },
  { id: '3', regulator: 'FATF', title: 'Updated Guidance on Virtual Assets — June 2024', timestamp: new Date(Date.now() - 24 * 3_600_000).toISOString(), country: 'INTL' },
  { id: '4', regulator: 'OFAC', title: 'SDN List Update — 12 new cryptocurrency addresses', timestamp: new Date(Date.now() - 30 * 3_600_000).toISOString(), country: 'US' },
  { id: '5', regulator: 'CNV', title: 'Resolución General 940 — Tokenización de activos', timestamp: new Date(Date.now() - 48 * 3_600_000).toISOString(), country: 'AR' },
]

export function RegFeed({ token }: RegFeedProps) {
  const { events, connected } = useSSE()
  const { data: crawlerData } = useCrawlerStatus(token)

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Regulatory Feed</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: connected ? '#00D68F' : '#555555',
              animation: connected ? 'pulse 2s ease-in-out infinite' : 'none',
            }} />
            <span style={{
              fontSize: 11, fontWeight: 700,
              color: connected ? '#00D68F' : '#555555',
              letterSpacing: '0.5px',
            }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
        <p style={{ fontSize: 13, color: '#888888', margin: '4px 0 0' }}>
          Feed en tiempo real de actualizaciones regulatorias — BCRA, UIF, FATF, OFAC
        </p>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Crawler status grid */}
      {crawlerData?.jobs && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: '#555555', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Estado de crawlers
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
            {Object.entries(crawlerData.jobs).map(([name, info]: [string, unknown]) => (
              <div key={name} style={{
                background: '#111111',
                border: '1px solid #242424',
                borderRadius: 10,
                padding: '8px 12px',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#CCCCCC', textTransform: 'uppercase' }}>{name}</div>
                <div style={{ fontSize: 10, color: '#555555' }}>
                  cada {(info as { interval_hours?: number }).interval_hours ?? '?'}h · {(info as { country?: string }).country ?? '?'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SSE live events */}
      {events.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: '#00D68F', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#00D68F' }} />
            Eventos en vivo
          </div>
          {events.map(evt => (
            <FeedItem
              key={evt.id}
              regulator={(evt.data as Record<string, string>)?.regulator || 'SYSTEM'}
              title={(evt.data as Record<string, string>)?.title || JSON.stringify(evt.data)}
              timestamp={evt.timestamp}
            />
          ))}
        </div>
      )}

      {/* Static/mock feed */}
      <div>
        <div style={{ fontSize: 11, color: '#555555', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Últimas actualizaciones
        </div>
        {MOCK_FEED.map(item => (
          <FeedItem
            key={item.id}
            regulator={item.regulator}
            title={item.title}
            timestamp={item.timestamp}
            onAnalyze={() => {
              // Navigate to copilot with context
            }}
          />
        ))}
      </div>
    </div>
  )
}
