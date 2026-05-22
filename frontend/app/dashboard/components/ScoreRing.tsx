'use client'

interface ScoreRingProps {
  score: number
  size?: number
}

export function ScoreRing({ score, size = 104 }: ScoreRingProps) {
  const r = 42
  const cx = 52
  const cy = 52
  const strokeWidth = 8
  const circumference = 2 * Math.PI * r
  const clampedScore = Math.max(0, Math.min(100, score))
  const offset = circumference - (clampedScore / 100) * circumference

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 104 104"
      style={{ transform: 'rotate(-90deg)' }}
    >
      {/* Track */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#242424"
        strokeWidth={strokeWidth}
      />
      {/* Progress */}
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        stroke="#FFE135"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        style={{ transition: 'stroke-dashoffset 0.6s ease' }}
      />
      {/* Center text — counter-rotate so it's upright */}
      <g style={{ transform: `rotate(90deg)`, transformOrigin: `${cx}px ${cy}px` }}>
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill="#FFE135"
          fontSize="22"
          fontWeight="700"
          style={{ fontFamily: 'inherit' }}
        >
          {Math.round(clampedScore)}
        </text>
        <text
          x={cx}
          y={cy + 14}
          textAnchor="middle"
          fill="#888888"
          fontSize="10"
          style={{ fontFamily: 'inherit' }}
        >
          /100
        </text>
      </g>
    </svg>
  )
}
