'use client'

import { useState } from 'react'
import { WorkflowCard } from '../components/WorkflowCard'
import { useWorkflows } from '../hooks/useDashboard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface WorkflowsProps {
  token: string | null
}

const STATUS_FILTERS = ['all', 'awaiting_approval', 'running', 'pending', 'completed', 'escalated']

export function Workflows({ token }: WorkflowsProps) {
  const { data, mutate } = useWorkflows(token)
  const [statusFilter, setStatusFilter] = useState('all')

  const workflows = data?.workflows ?? []

  const filtered = statusFilter === 'all'
    ? workflows
    : workflows.filter((w: { status: string }) => w.status === statusFilter)

  async function approveStep(workflowId: string, stepId: string) {
    try {
      const headers: Record<string, string> = { 'X-Tenant-Id': 'lemon-cash' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      await fetch(`${API_URL}/api/v1/workflow/${workflowId}/steps/${stepId}/approve`, {
        method: 'POST',
        headers,
      })
      mutate()
    } catch (e) {
      console.error('approve step failed', e)
    }
  }

  async function escalateWorkflow(workflowId: string) {
    try {
      const headers: Record<string, string> = { 'X-Tenant-Id': 'lemon-cash' }
      if (token) headers['Authorization'] = `Bearer ${token}`
      await fetch(`${API_URL}/api/v1/workflow/${workflowId}/escalate`, {
        method: 'POST',
        headers,
      })
      mutate()
    } catch (e) {
      console.error('escalate failed', e)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#FFFFFF', margin: 0 }}>Workflows de Remediación</h2>
        <p style={{ fontSize: 13, color: '#888888', margin: '4px 0 0' }}>
          {data?.total ?? 0} workflows · gestione aprobaciones y escaladas
        </p>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
        {STATUS_FILTERS.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            style={{
              padding: '6px 14px',
              borderRadius: 12,
              border: statusFilter === s ? '1px solid #FFE135' : '1px solid #242424',
              background: statusFilter === s ? 'rgba(255,225,53,0.12)' : '#111111',
              color: statusFilter === s ? '#FFE135' : '#888888',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {s === 'all' ? 'Todos' : s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Workflow list */}
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
          No hay workflows {statusFilter !== 'all' ? `con estado "${statusFilter}"` : ''}
        </div>
      ) : (
        (filtered as Array<Parameters<typeof WorkflowCard>[0]['workflow']>).map((wf, i) => (
          <WorkflowCard
            key={wf.id || String(i)}
            workflow={wf}
            onApprove={approveStep}
            onEscalate={escalateWorkflow}
          />
        ))
      )}
    </div>
  )
}
