'use client'

import { useEffect, useRef, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface SSEEvent {
  id: string
  type: string
  data: Record<string, unknown>
  timestamp: string
}

export function useSSE() {
  const [events, setEvents] = useState<SSEEvent[]>([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    function connect() {
      if (esRef.current) {
        esRef.current.close()
      }

      try {
        const es = new EventSource(`${API_URL}/api/v1/crawler/events`)
        esRef.current = es

        es.addEventListener('connected', () => {
          setConnected(true)
        })

        es.addEventListener('crawl_complete', (e: MessageEvent) => {
          try {
            const data = typeof e.data === 'string' ? JSON.parse(e.data) : e.data
            const event: SSEEvent = {
              id: `evt-${Date.now()}`,
              type: 'crawl_complete',
              data,
              timestamp: new Date().toISOString(),
            }
            setEvents(prev => [event, ...prev].slice(0, 20))
          } catch {
            // ignore malformed events
          }
        })

        es.onerror = () => {
          setConnected(false)
          es.close()
          esRef.current = null
          // Retry after 10 seconds
          setTimeout(connect, 10_000)
        }
      } catch {
        setConnected(false)
      }
    }

    connect()

    return () => {
      if (esRef.current) {
        esRef.current.close()
        esRef.current = null
      }
    }
  }, [])

  return { events, connected }
}
