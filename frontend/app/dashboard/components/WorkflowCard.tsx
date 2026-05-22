'use client'

import { useState } from 'react'
import { AlertBadge } from './AlertBadge'

interface WorkflowStep {
  id: string
  name: string
  status: string
  owner: string
  requires_approval: boolean
}

interface WorkflowCardProps {
  workflow: {
    id: string
    title: string
    status: string
    severity: string
    steps_completed: number
    steps_total: number
    completion_pct: number
    steps: WorkflowStep[]
    due_date?: string | null
    created_at?: string | null
  }
  onApprove?: (workflowId: string, stepId: string) => void
  onEscalate?: (workflowId: string) => void
}

function StepCircle({ status }: { status: string }) {
  if (status === 'done' || status === 'approved' || status === 'completed') {
    return (
      <div style={{
        width: 20, height: 20, borderRadius: '50%',
        background: '#00D68F', display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <span style={{ color: '#0A0A0A', fontSize: 10, fontWeight: 700 }}>✓</span>
      </div>
    )
  }
  if (status === 'active' || status === 'running') {
    return (
      <div style={{
        width: 20, height: 20, borderRadius: '50%',
        background: 'rgba(255,225,53,0.15)', border: '2px solid #FFE135',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#FFE135' }} />
      </div>
    )
  }
  return (
    <div style={{
      width: 20, height: 20, borderRadius: '50%',
      border: '2px solid #2E2E2E', flexShrink: 0,
    }} />
  )
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
  } catch {
    return '—'
  }
}

export function WorkflowCard({ workflow, onApprove, onEscalate }: WorkflowCardProps) {
  const [expanded, setExpanded] = useState(false)
  const awaitingApproval = workflow.status === 'awaiting_approval' || workflow.status === 'approval_required'

  const pendingApprovalStep = workflow.steps.find(
    s => s.requires_approval && (s.status === 'active' || s.status === 'pending')
  )

  return (
    <div style={{
      background: '#111111',
      border: '1px solid #242424',
      borderRadius: 16,
      overflow: 'hidden',
      marginBottom: 8,
    }}>
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%',
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        {/* Main info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <span style={{ color: '#FFFFFF', fontWeight: 600, fontSize: 14, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {workflow.title}
            </span>
            <AlertBadge severity={workflow.severity} />
            {awaitingApproval && (
              <span style={{
                background: 'rgba(255,225,53,0.12)', color: '#FFE135',
                border: '1px solid rgba(255,225,53,0.3)',
                borderRadius: 24, fontSize: 10, fontWeight: 600, padding: '1px 8px', whiteSpace: 'nowrap',
              }}>
                PENDIENTE APROBACIÓN
              </span>
            )}
          </div>

          {/* Progress bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 5, background: '#2E2E2E', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${workflow.completion_pct}%`,
                background: '#FFE135',
                borderRadius: 3,
                transition: 'width 0.5s ease',
              }} />
            </div>
            <span style={{ fontSize: 11, color: '#888888', whiteSpace: 'nowrap' }}>
              Paso {workflow.steps_completed}/{workflow.steps_total} · vence {formatDate(workflow.due_date)}
            </span>
          </div>
        </div>

        {/* Percentage */}
        <div style={{
          fontSize: 20, fontWeight: 700,
          color: workflow.completion_pct >= 75 ? '#00D68F' : workflow.completion_pct >= 50 ? '#FFE135' : '#FF8C42',
          flexShrink: 0,
        }}>
          {workflow.completion_pct}%
        </div>

        {/* Chevron */}
        <span style={{ color: '#555555', fontSize: 12, flexShrink: 0 }}>
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div style={{ padding: '0 20px 16px' }}>
          {/* Step list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            {workflow.steps.map((step, idx) => (
              <div key={step.id || idx} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <StepCircle status={step.status} />
                <span style={{
                  fontSize: 13,
                  color: step.status === 'done' || step.status === 'approved' ? '#888888' : '#FFFFFF',
                  textDecoration: step.status === 'done' || step.status === 'approved' ? 'line-through' : 'none',
                }}>
                  {step.name}
                </span>
                <span style={{ fontSize: 11, color: '#555555', marginLeft: 'auto' }}>{step.owner}</span>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          {awaitingApproval && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => pendingApprovalStep && onApprove?.(workflow.id, pendingApprovalStep.id)}
                style={{
                  padding: '8px 20px',
                  background: '#FFE135',
                  color: '#0A0A0A',
                  border: 'none',
                  borderRadius: 12,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                APROBAR
              </button>
              <button
                onClick={() => onEscalate?.(workflow.id)}
                style={{
                  padding: '8px 20px',
                  background: 'transparent',
                  color: '#FF4D6A',
                  border: '1px solid #FF4D6A',
                  borderRadius: 12,
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                ESCALAR
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
