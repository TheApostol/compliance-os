'use client'

type TabId = 'overview' | 'workflows' | 'kyc' | 'copilot' | 'feed'

interface NavProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
}

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'overview', label: 'Resumen', icon: '▦' },
  { id: 'workflows', label: 'Workflows', icon: '⟳' },
  { id: 'kyc', label: 'KYC / AML', icon: '⚑' },
  { id: 'copilot', label: 'Copilot', icon: '✦' },
  { id: 'feed', label: 'RegFeed', icon: '◉' },
]

export function Nav({ activeTab, onTabChange }: NavProps) {
  return (
    <>
      {/* Top bar */}
      <header style={{
        background: '#111111',
        borderBottom: '1px solid #242424',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{
          maxWidth: 1280,
          margin: '0 auto',
          padding: '0 24px',
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 24 }}>🍋</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#FFFFFF', letterSpacing: '-0.3px' }}>
                Lemon Cash × ComplianceOS
              </div>
              <div style={{ fontSize: 11, color: '#888888' }}>CCO Dashboard</div>
            </div>
            <span style={{
              background: 'rgba(0,214,143,0.12)',
              color: '#00D68F',
              border: '1px solid rgba(0,214,143,0.3)',
              borderRadius: 24,
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 10px',
              marginLeft: 8,
            }}>
              VASP · AR
            </span>
          </div>

          {/* Desktop tabs */}
          <nav style={{ display: 'flex', gap: 4, alignItems: 'center' }} className="desktop-nav">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 12,
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500,
                  transition: 'all 0.15s',
                  background: activeTab === tab.id ? '#FFE135' : 'transparent',
                  color: activeTab === tab.id ? '#0A0A0A' : '#888888',
                }}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Avatar */}
          <div style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            background: '#FFE135',
            color: '#0A0A0A',
            fontWeight: 700,
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            flexShrink: 0,
          }}>
            MG
          </div>
        </div>
      </header>

      {/* Mobile bottom bar */}
      <nav
        className="mobile-nav"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#111111',
          borderTop: '1px solid #242424',
          display: 'flex',
          zIndex: 100,
          paddingBottom: 'env(safe-area-inset-bottom)',
        }}
      >
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              padding: '10px 4px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              color: activeTab === tab.id ? '#FFE135' : '#555555',
            }}
          >
            <span style={{ fontSize: 18 }}>{tab.icon}</span>
            <span style={{ fontSize: 10, fontWeight: 500 }}>{tab.label}</span>
          </button>
        ))}
      </nav>

      <style>{`
        @media (min-width: 768px) {
          .mobile-nav { display: none !important; }
          .desktop-nav { display: flex !important; }
        }
        @media (max-width: 767px) {
          .desktop-nav { display: none !important; }
          .mobile-nav { display: flex !important; }
        }
      `}</style>
    </>
  )
}
