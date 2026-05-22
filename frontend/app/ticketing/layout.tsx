'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV_ITEMS = [
  { href: '/ticketing/dashboard',          label: 'Dashboard',           desc: 'Scores & alerts' },
  { href: '/ticketing/regulatory-matrix',  label: 'Regulatory Matrix',   desc: 'Obligations by country' },
  { href: '/ticketing/controls',           label: 'Controls Library',    desc: 'Compliance controls' },
  { href: '/ticketing/events',             label: 'Events',              desc: 'Event compliance tracker' },
  { href: '/ticketing/documents',          label: 'Documents',           desc: 'Generated policies' },
  { href: '/ticketing/ai-copilot',         label: 'AI Copilot',          desc: 'Compliance Q&A' },
  { href: '/ticketing/reports',            label: 'Reports',             desc: 'Event compliance reports' },
]

export default function TicketingLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <header className="border-b border-zinc-800 px-8 py-4">
        <div className="flex items-center justify-between max-w-screen-xl mx-auto">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-zinc-500 hover:text-zinc-300 text-sm">
              ← ComplianceOS
            </Link>
            <div className="h-4 w-px bg-zinc-700" />
            <div>
              <span className="text-sm font-semibold text-zinc-100">M9 Ticketing Compliance</span>
              <span className="ml-2 px-1.5 py-0.5 text-xs bg-violet-900 text-violet-300 border border-violet-800 rounded">
                Industry Module
              </span>
            </div>
          </div>
          <Link
            href="/ticketing/events/new"
            className="px-3 py-1.5 bg-zinc-100 text-zinc-900 rounded-md text-xs font-medium hover:bg-white"
          >
            + New Event
          </Link>
        </div>
      </header>

      <div className="max-w-screen-xl mx-auto px-8 py-8 flex gap-8">
        {/* Sidebar */}
        <aside className="w-56 shrink-0">
          <nav className="space-y-1">
            {NAV_ITEMS.map(item => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block p-3 rounded-md transition-colors ${
                    isActive
                      ? 'bg-zinc-800 border border-zinc-700'
                      : 'hover:bg-zinc-900'
                  }`}
                >
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className="text-xs text-zinc-500 mt-0.5">{item.desc}</div>
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  )
}
