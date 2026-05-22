import type { Metadata } from 'next'
import { Plus_Jakarta_Sans } from 'next/font/google'

const font = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-pjs',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Lemon Cash — CCO Dashboard',
  description: 'Lemon Cash × ComplianceOS — Chief Compliance Officer Dashboard',
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div
      className={font.className}
      style={{
        background: '#0A0A0A',
        minHeight: '100vh',
        color: '#FFFFFF',
        paddingBottom: 80,
        fontFamily: 'var(--font-pjs), system-ui, sans-serif',
      }}
    >
      {children}
    </div>
  )
}
