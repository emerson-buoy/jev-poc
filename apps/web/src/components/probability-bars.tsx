import { formatPercent } from '@/lib/board'

interface ProbabilityBarsProps {
  rows: { key: string; label: string; probability: number; highlight?: boolean }[]
}

export function ProbabilityBars({ rows }: ProbabilityBarsProps) {
  return (
    <ul className="space-y-1.5">
      {rows.map((row) => (
        <li key={row.key} className="text-xs">
          <span className={row.highlight ? 'font-semibold' : 'text-muted-foreground'}>
            {row.label} {formatPercent(row.probability)}
          </span>
          <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded bg-muted">
            <div
              className={row.highlight ? 'h-full bg-primary' : 'h-full bg-muted-foreground/40'}
              style={{ width: `${Math.round(row.probability * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  )
}
