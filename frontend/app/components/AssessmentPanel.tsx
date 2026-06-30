'use client'

import { useState } from 'react'
import { Badge, Card, variantForLevel } from './ui'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface EntityAssessmentResult {
  success: boolean
  compliance_score?: number
  jurisdictions_assessed?: string[]
  applicable_regulations?: number
  gaps?: string[]
  deadlines_upcoming?: number
  risk_level?: string
  error?: string
}

interface AssessmentPanelProps {
  tenantId: string
  entityId: string
  entityType?: string
  sectors?: string[]
  onAssessmentComplete?: (result: EntityAssessmentResult) => void
}

export function AssessmentPanel({
  tenantId,
  entityId,
  entityType = 'company',
  sectors = [],
  onAssessmentComplete,
}: AssessmentPanelProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EntityAssessmentResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleAssess = async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(`${API_URL}/api/v1/agents/assess`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'X-Tenant-Id': tenantId,
        },
        body: JSON.stringify({
          tenant_id: tenantId,
          entity_id: entityId,
          entity_type: entityType,
          sectors: sectors || [],
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Assessment failed with status ${response.status}`)
      }

      const assessmentResult: EntityAssessmentResult = await response.json()
      setResult(assessmentResult)

      if (onAssessmentComplete) {
        onAssessmentComplete(assessmentResult)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <button
          onClick={handleAssess}
          disabled={loading}
          className={`px-4 py-2 rounded font-medium transition-colors ${
            loading
              ? 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
              : 'bg-blue-900 text-blue-100 hover:bg-blue-800 border border-blue-700'
          }`}
        >
          {loading ? 'Assessing...' : 'Start Assessment'}
        </button>
        <div className="text-sm text-zinc-400 flex items-center">
          Entity: {entityId} • Type: {entityType}
        </div>
      </div>

      {error && (
        <Card className="border-red-900 bg-red-950/20">
          <div className="text-red-300 text-sm">{error}</div>
        </Card>
      )}

      {result && result.success && (
        <div className="space-y-4">
          {/* Compliance Score */}
          <Card className="border-blue-900 bg-blue-950/20">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-zinc-400 text-sm">Compliance Score</div>
                <div className="text-3xl font-bold text-blue-300 mt-1">
                  {result.compliance_score?.toFixed(1) || 'N/A'}%
                </div>
              </div>
              <Badge variant={variantForLevel(result.risk_level)}>
                {result.risk_level || 'Unknown'}
              </Badge>
            </div>
          </Card>

          {/* Jurisdictions & Regulations */}
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <div className="text-zinc-400 text-sm mb-2">Jurisdictions Assessed</div>
              <div className="flex flex-wrap gap-2">
                {result.jurisdictions_assessed && result.jurisdictions_assessed.length > 0 ? (
                  result.jurisdictions_assessed.map((jurisdiction) => (
                    <Badge key={jurisdiction} variant="neutral" size="sm">
                      {jurisdiction}
                    </Badge>
                  ))
                ) : (
                  <span className="text-zinc-500 text-sm">None</span>
                )}
              </div>
            </Card>

            <Card>
              <div className="text-zinc-400 text-sm mb-2">Applicable Regulations</div>
              <div className="text-2xl font-bold text-zinc-300">
                {result.applicable_regulations || 0}
              </div>
            </Card>
          </div>

          {/* Deadlines */}
          {result.deadlines_upcoming !== undefined && result.deadlines_upcoming > 0 && (
            <Card className="border-yellow-900 bg-yellow-950/20">
              <div className="flex items-center justify-between">
                <div className="text-yellow-300 font-medium">
                  {result.deadlines_upcoming} Upcoming Deadline{result.deadlines_upcoming !== 1 ? 's' : ''}
                </div>
                <Badge variant="medium" size="sm">
                  Action Required
                </Badge>
              </div>
            </Card>
          )}

          {/* Compliance Gaps */}
          {result.gaps && result.gaps.length > 0 && (
            <Card className="border-orange-900 bg-orange-950/20">
              <div className="text-orange-300 font-medium mb-3">Compliance Gaps ({result.gaps.length})</div>
              <ul className="space-y-2">
                {result.gaps.map((gap, idx) => (
                  <li key={idx} className="text-orange-200 text-sm flex gap-2">
                    <span className="text-orange-400 font-bold">•</span>
                    <span>{gap}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* No Gaps Success State */}
          {(!result.gaps || result.gaps.length === 0) && (
            <Card className="border-green-900 bg-green-950/20">
              <div className="text-green-300 font-medium">✓ No compliance gaps identified</div>
            </Card>
          )}
        </div>
      )}

      {result && !result.success && (
        <Card className="border-red-900 bg-red-950/20">
          <div className="text-red-300 text-sm">
            Assessment failed: {result.error || 'Unknown error'}
          </div>
        </Card>
      )}
    </div>
  )
}
