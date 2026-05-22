'use client'

import useSWR from 'swr'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const TENANT_ID = 'lemon-cash'

function makeFetcher(token: string | null) {
  return async (url: string) => {
    const headers: Record<string, string> = {
      'X-Tenant-Id': TENANT_ID,
    }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(url, { headers })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json()
  }
}

export function useScore(token: string | null, tenantId: string) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/compliance/score/${tenantId}`,
    fetcher,
    { refreshInterval: 300_000, revalidateOnFocus: false }
  )
}

export function useScoreHistory(token: string | null, tenantId: string) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/compliance/score/${tenantId}/history`,
    fetcher,
    { refreshInterval: 300_000, revalidateOnFocus: false }
  )
}

export function useAlerts(token: string | null) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/alerts?acknowledged=false&limit=50`,
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  )
}

export function useWorkflows(token: string | null) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/workflow/`,
    fetcher,
    { refreshInterval: 30_000, revalidateOnFocus: false }
  )
}

export function useKYCQueue(token: string | null) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/kyc/queue`,
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  )
}

export function useCrawlerStatus(token: string | null) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/crawler/status`,
    fetcher,
    { refreshInterval: 30_000, revalidateOnFocus: false }
  )
}

export function useCannedQuestions(token: string | null, vertical: string) {
  const fetcher = makeFetcher(token)
  return useSWR(
    `${API_URL}/api/v1/copilot/canned-questions?vertical=${encodeURIComponent(vertical)}`,
    fetcher,
    { revalidateOnFocus: false }
  )
}
