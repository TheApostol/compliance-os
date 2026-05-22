'use client'

import { ScoreRing } from '../components/ScoreRing'
import { Sparkline } from '../components/Sparkline'
import { AlertBadge } from '../components/AlertBadge'
import { WorkflowCard } from '../components/WorkflowCard'
import { useScore, useScoreHistory, useAlerts, useWorkflows, useKYCQueue, useCrawlerStatus } from '../hooks/useDashboard'

interface OverviewProps {
  token: string | null
  onTabChange: (tab: string) => void
}

const ENTITY_ID = 'lemon-cash'

function Card({ children, title, action }: { children: React.ReactNode; title?: string; action?: React.ReactNode }) {
  return (
    <div style={{
      background: '#111111',
      border: '1px solid #242424',
      borderRadius: 16,
      padding: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      {(title || action) && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {title && <div style={{ fontSize: 12, fontWeight: 600, color: '#888888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{title}</div>}
          {action}
        </div>
      )}
      {children}
    </div>
  )
}

export function Overview({ token, onTabChange }: OverviewProps) {
  const { data: scoreData } = useScore(token, ENTITY_ID)
  const { data: historyData } = useScoreHistory(token, ENTITY_ID)
  const { data: alertsData } = useAlerts(token)
  const { data: workflowsData } = useWorkflows(token)
  const { data: kycData } = useKYCQueue(token)
  const { data: crawlerData } = useCrawlerStatus(token)

  const score = scoreData?.score_pct ?? 78
  const history: { month: string; score: number }[] = historyData?.history ?? []
  const sparkData = history.map(h => h.score)

  const alerts: { id: string; severity: string; title: string; days_remaining?: number; deadline?: string }[] = alertsData?.alerts ?? []
  const workflows: unknown[] = workflowsData?.workflows ?? []
  const cases: unknown[] = kycData?.cases ?? []

  // Alert counts by severity
  const alertCounts = {
    CRITICAL: alerts.filter(a => a.severity?.toUpperCase() === 'CRITICAL').length,
    HIGH: alerts.filter(a => a.severity?.toUpperCase() === 'HIGH').length,
    MEDIUM: alerts.filter(a => a.severity?.toUpperCase() === 'MEDIUM').length,
    LOW: alerts.filter(a => a.severity?.toUpperCase() === 'LOW').length,
  }

  const upcomingDeadlines = [...alerts]
    .sort((a, b) => (a.days_remaining ?? 999) - (b.days_remaining ?? 999))
    .slice(0, 5)

  const SEVERITY_BORDER: Record<string, string> = {
    CRITICAL: '#FF4D6A', HIGH: '#FF8C42', MEDIUM: '#FFE135', LOW: '#888888',
    critical: '#FF4D6A', high: '#FF8C42', medium: '#FFE135', low: '#888888',
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>

      {/* Score Card */}
      <Card title="Score de Cumplimiento">
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <ScoreRing score={score} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, color: '#888888', marginBottom: 4 }}>
              {score >= 80 ? 'Cumplimiento satisfactorio' : score >= 60 ? 'Atención requerida' : 'Riesgo elevado'}
            </div>
            {sparkData.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <Sparkline data={sparkData} />
                <div style={{ fontSize: 11, color: '#555555', marginTop: 4 }}>
                  Últimos 6 meses
                </div>
              </div>
            )}
            {score < 70 && (
              <div style={{
                marginTop: 8, padding: '6px 10px',
                background: 'rgba(255,77,106,0.1)', border: '1px solid rgba(255,77,106,0.3)',
                borderRadius: 8, fontSize: 11, color: '#FF4D6A',
              }}>
                ⚠ Score por debajo del umbral mínimo
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Risk Alerts Summary */}
      <Card title="Alertas por Severidad">
        {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(sev => (
          <div key={sev} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1A1A1A' }}>
            <AlertBadge severity={sev} />
            <span style={{ fontSize: 20, fontWeight: 700, color: alertCounts[sev as keyof typeof alertCounts] > 0 ? SEVERITY_BORDER[sev] : '#333' }}>
              {alertCounts[sev as keyof typeof alertCounts]}
            </span>
          </div>
        ))}
        <button onClick={() => onTabChange('overview')} style={{ fontSize: 12, color: '#555555', background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left' }}>
          {alerts.length} alertas activas en total
        </button>
      </Card>

      {/* Upcoming Deadlines */}
      <Card title="Próximos Vencimientos" action={
        <span style={{ fontSize: 11, color: '#555555' }}>próximos 5</span>
      }>
        {upcomingDeadlines.length === 0 ? (
          <div style={{ fontSize: 13, color: '#555555' }}>Sin vencimientos próximos</div>
        ) : (
          upcomingDeadlines.map(alert => (
            <div key={alert.id} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 10px',
              borderLeft: `3px solid ${SEVERITY_BORDER[alert.severity] || '#555'}`,
              borderRadius: '0 8px 8px 0',
              background: '#1A1A1A',
            }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: '#CCCCCC', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {alert.title}
                </div>
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: (alert.days_remaining ?? 999) <= 7 ? '#FF4D6A' : '#888888', flexShrink: 0 }}>
                {alert.days_remaining ?? '?'}d
              </div>
            </div>
          ))
        )}
      </Card>

      {/* Active Workflows */}
      <Card title="Workflows Activos" action={
        <button onClick={() => onTabChange('workflows')} style={{ fontSize: 12, color: '#FFE135', background: 'transparent', border: 'none', cursor: 'pointer' }}>
          Ver todos →
        </button>
      }>
        {(workflows as Array<Parameters<typeof WorkflowCard>[0]['workflow']>
        ).slice(0, 4).map((wf, i) => (
          <WorkflowCard key={wf.id || String(i)} workflow={wf} />
        ))}
        {workflows.length === 0 && (
          <div style={{ fontSize: 13, color: '#555555' }}>Sin workflows activos</div>
        )}
      </Card>

      {/* KYC Queue Preview */}
      <Card title="Cola KYC / AML" action={
        <button onClick={() => onTabChange('kyc')} style={{ fontSize: 12, color: '#FFE135', background: 'transparent', border: 'none', cursor: 'pointer' }}>
          Ver →
        </button>
      }>
        {(cases as { id: string; name: string; risk_level: string; sla_days: number }[]).slice(0, 3).map((c, i) => (
          <div key={c.id || i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: '1px solid #1A1A1A' }}>
            <div style={{ flex: 1, fontSize: 13, color: '#CCCCCC', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {c.name}
            </div>
            <AlertBadge severity={c.risk_level} />
            <div style={{ fontSize: 11, color: '#555555', flexShrink: 0 }}>SLA {c.sla_days}d</div>
          </div>
        ))}
        {cases.length === 0 && (
          <div style={{ fontSize: 13, color: '#555555' }}>Cola vacía</div>
        )}
        <div style={{ fontSize: 11, color: '#555555' }}>{kycData?.total ?? 0} casos en cola</div>
      </Card>

      {/* Crawler Status */}
      <Card title="Regulatory Feed">
        {crawlerData ? (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <div style={{
                width: 8, height: 8, borderRadius: '50%',
                background: crawlerData.enabled ? '#00D68F' : '#555555',
              }} />
              <span style={{ fontSize: 13, color: '#CCCCCC' }}>
                Crawler {crawlerData.enabled ? 'activo' : 'inactivo'}
              </span>
              <button onClick={() => onTabChange('feed')} style={{ fontSize: 12, color: '#FFE135', background: 'transparent', border: 'none', cursor: 'pointer', marginLeft: 'auto' }}>
                Ver feed →
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {crawlerData.jobs && Object.entries(crawlerData.jobs).slice(0, 4).map(([name, info]: [string, unknown]) => (
                <div key={name} style={{
                  background: '#1A1A1A', borderRadius: 8, padding: '6px 10px',
                  fontSize: 11, color: '#888888',
                }}>
                  <span style={{ fontWeight: 700, color: '#CCCCCC', textTransform: 'uppercase' }}>{name}</span>
                  {' · '}{(info as { country?: string }).country ?? '?'}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 13, color: '#555555' }}>Cargando estado del crawler...</div>
        )}
      </Card>
    </div>
  )
}
