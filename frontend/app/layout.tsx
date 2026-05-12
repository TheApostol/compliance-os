import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'ComplianceOS',
  description: 'AI-native Compliance Operating System for LATAM',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es">
      <body className="bg-zinc-950 text-zinc-100 antialiased">
        {children}
      </body>
    </html>
  )
}
