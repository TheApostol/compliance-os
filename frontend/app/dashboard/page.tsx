'use client'

import { useState, useEffect } from 'react'
import { Nav } from './components/Nav'
import { Overview } from './tabs/Overview'
import { Workflows } from './tabs/Workflows'
import { KYCQueue } from './tabs/KYCQueue'
import { Copilot } from './tabs/Copilot'
import { RegFeed } from './tabs/RegFeed'

type TabId = 'overview' | 'workflows' | 'kyc' | 'copilot' | 'feed'

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    // Try to read token from localStorage (set by main app login)
    const stored = localStorage.getItem('cos_token')
    if (stored) {
      setToken(stored)
    }
  }, [])

  function renderTab() {
    switch (activeTab) {
      case 'overview':
        return <Overview token={token} onTabChange={(tab) => setActiveTab(tab as TabId)} />
      case 'workflows':
        return <Workflows token={token} />
      case 'kyc':
        return <KYCQueue token={token} />
      case 'copilot':
        return <Copilot token={token} />
      case 'feed':
        return <RegFeed token={token} />
      default:
        return <Overview token={token} onTabChange={(tab) => setActiveTab(tab as TabId)} />
    }
  }

  return (
    <>
      <Nav activeTab={activeTab} onTabChange={setActiveTab} />
      <main style={{
        maxWidth: 1280,
        margin: '0 auto',
        padding: '28px 24px',
      }}>
        {renderTab()}
      </main>
    </>
  )
}
