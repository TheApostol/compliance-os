'use client'

import { useState } from 'react'
import { AssessmentPanel } from '../components/AssessmentPanel'
import { Badge, Card, variantForLevel } from '../components/ui'

export default function EntitiesPage() {
  const [tenantId, setTenantId] = useState('polkorp')
  const [entityId, setEntityId] = useState('')
  const [entityType, setEntityType] = useState('fintech')
  const [sectors, setSectors] = useState(['payments'])
  const [showAssessment, setShowAssessment] = useState(false)
  const [assessmentHistory, setAssessmentHistory] = useState<any[]>([])

  const handleStartAssessment = () => {
    if (!entityId.trim()) {
      alert('Please enter an entity ID')
      return
    }
    setShowAssessment(true)
  }

  const handleAssessmentComplete = (result: any) => {
    // Add to history
    setAssessmentHistory([
      {
        id: Math.random(),
        entityId,
        timestamp: new Date().toLocaleString(),
        result,
      },
      ...assessmentHistory,
    ])
  }

  const handleSectorToggle = (sector: string) => {
    setSectors((prev) => (prev.includes(sector) ? prev.filter((s) => s !== sector) : [...prev, sector]))
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Entity Compliance Assessment</h1>
          <p className="text-zinc-400 mt-2">
            Trigger AI-powered compliance assessment for any LATAM-regulated entity
          </p>
        </div>

        {/* Configuration Panel */}
        <Card className="border-zinc-700 space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Tenant ID</label>
            <input
              type="text"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-zinc-100 placeholder-zinc-500"
              placeholder="e.g., polkorp"
            />
            <p className="text-xs text-zinc-500 mt-1">Your organization's tenant identifier</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Entity ID</label>
            <input
              type="text"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-zinc-100 placeholder-zinc-500"
              placeholder="e.g., corp-123, entity-xyz"
            />
            <p className="text-xs text-zinc-500 mt-1">Unique identifier for the entity to assess</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Entity Type</label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-zinc-100"
            >
              <option value="company">Company</option>
              <option value="fintech">FinTech</option>
              <option value="bank">Bank</option>
              <option value="crypto">Crypto Exchange</option>
              <option value="payment_processor">Payment Processor</option>
              <option value="insurance">Insurance</option>
            </select>
            <p className="text-xs text-zinc-500 mt-1">Business entity type</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Business Sectors</label>
            <div className="space-y-2">
              {['payments', 'lending', 'crypto', 'trading', 'remittance', 'insurance'].map((sector) => (
                <label key={sector} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sectors.includes(sector)}
                    onChange={() => handleSectorToggle(sector)}
                    className="w-4 h-4 bg-zinc-900 border border-zinc-700 rounded cursor-pointer"
                  />
                  <span className="text-sm capitalize">{sector}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-zinc-500 mt-2">Selected sectors affect regulatory scope</p>
          </div>

          <button
            onClick={handleStartAssessment}
            className="w-full bg-blue-900 text-blue-100 hover:bg-blue-800 border border-blue-700 rounded py-2.5 font-medium transition-colors"
          >
            Run Full Assessment
          </button>
        </Card>

        {/* Assessment Panel */}
        {showAssessment && (
          <div>
            <h2 className="text-lg font-semibold text-zinc-200 mb-4">Assessment in Progress</h2>
            <AssessmentPanel
              tenantId={tenantId}
              entityId={entityId}
              entityType={entityType}
              sectors={sectors}
              onAssessmentComplete={handleAssessmentComplete}
            />
          </div>
        )}

        {/* Assessment History */}
        {assessmentHistory.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold text-zinc-200 mb-4">Assessment History</h2>
            <div className="space-y-4">
              {assessmentHistory.map((entry) => (
                <Card key={entry.id} className="border-zinc-700">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="font-medium text-zinc-300">{entry.entityId}</div>
                      <div className="text-xs text-zinc-500">{entry.timestamp}</div>
                    </div>
                    <Badge variant={variantForLevel(entry.result.risk_level)}>
                      {entry.result.risk_level || 'Unknown'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-zinc-500">Compliance Score</div>
                      <div className="text-lg font-semibold text-blue-300">
                        {entry.result.compliance_score?.toFixed(1)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Regulations</div>
                      <div className="text-lg font-semibold text-zinc-300">
                        {entry.result.applicable_regulations || 0}
                      </div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Gaps Found</div>
                      <div className="text-lg font-semibold text-orange-300">
                        {entry.result.gaps?.length || 0}
                      </div>
                    </div>
                  </div>

                  {entry.result.gaps && entry.result.gaps.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-zinc-800">
                      <div className="text-xs text-zinc-500 mb-1">Key Gaps:</div>
                      <div className="text-xs text-zinc-300">
                        {entry.result.gaps.slice(0, 2).join(' • ')}
                        {entry.result.gaps.length > 2 && ` ... +${entry.result.gaps.length - 2} more`}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!showAssessment && assessmentHistory.length === 0 && (
          <Card className="border-zinc-700 text-center py-8">
            <div className="text-zinc-400">
              <p>Enter entity details and click "Run Full Assessment" to begin</p>
              <p className="text-xs mt-2">Assessment will span 6 LATAM jurisdictions (AR/BR/CO/CL/MX/ANDEAN)</p>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
