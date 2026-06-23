'use client'

// Shared UI primitives for the ComplianceOS console — extracted from the
// repeated zinc/Tailwind patterns in app/page.tsx and app/premortem/page.tsx
// so severity/risk colors and card chrome stay consistent across tabs.

export type BadgeVariant = 'critical' | 'high' | 'medium' | 'low' | 'neutral' | 'success'

const BADGE_COLORS: Record<BadgeVariant, string> = {
  critical: 'bg-red-950 text-red-300 border border-red-900',
  high: 'bg-orange-950 text-orange-300 border border-orange-900',
  medium: 'bg-yellow-950 text-yellow-300 border border-yellow-900',
  low: 'bg-green-950 text-green-300 border border-green-900',
  neutral: 'bg-zinc-800 text-zinc-300 border border-zinc-700',
  success: 'bg-green-950 text-green-400 border border-green-800',
}

const BADGE_SIZES: Record<'sm' | 'md' | 'lg', string> = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-xs px-2.5 py-1',
  lg: 'text-sm px-2.5 py-1',
}

const LEVEL_TO_VARIANT: Record<string, BadgeVariant> = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
}

/** Maps a severity/risk-level string (CRITICAL|HIGH|MEDIUM|LOW, any case) to a Badge variant. */
export function variantForLevel(level?: string | null): BadgeVariant {
  if (!level) return 'neutral'
  return LEVEL_TO_VARIANT[level.toUpperCase()] ?? 'neutral'
}

export function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
}: {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  return (
    <span className={`inline-block rounded font-medium ${BADGE_COLORS[variant]} ${BADGE_SIZES[size]} ${className}`}>
      {children}
    </span>
  )
}

export function Card({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return <div className={`border border-zinc-800 rounded-lg p-4 ${className}`}>{children}</div>
}

export function StatusPill({
  active,
  activeLabel,
  inactiveLabel,
}: {
  active: boolean
  activeLabel: string
  inactiveLabel: string
}) {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        active
          ? 'bg-green-900/50 text-green-400 border border-green-800'
          : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-green-400' : 'bg-zinc-500'}`} />
      {active ? activeLabel : inactiveLabel}
    </div>
  )
}
