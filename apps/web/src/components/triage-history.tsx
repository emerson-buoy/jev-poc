import type { TriageRecordRead } from '@/lib/api/generated'
import { departmentLabel, discardReasonLabel, formatPercent } from '@/lib/board'

/** Discarded results, collapsed by default. Shown for the record, never used by the board. */
export function TriageHistory({ records }: { records: TriageRecordRead[] }) {
  if (records.length === 0) return null
  return (
    <details className="rounded-lg border text-sm">
      <summary className="cursor-pointer px-3 py-2 font-medium select-none">
        Previous triages ({records.length})
      </summary>
      <ul className="divide-y border-t">
        {records.map(({ id, result, department_override, reason, discarded_at }) => (
          <li key={id} className="space-y-1 px-3 py-2 text-xs text-muted-foreground">
            <div className="text-foreground">
              {departmentLabel(result.department)}
              {department_override && ` (overridden to ${departmentLabel(department_override)})`}
              {' · '}urgency {result.urgency_level}/5 · refund{' '}
              {result.refund_requested ? 'yes' : 'no'} ({formatPercent(result.refund_probability)})
            </div>
            <div>
              {result.provider} · {discardReasonLabel(reason)} ·{' '}
              <span suppressHydrationWarning>{new Date(discarded_at).toLocaleString()}</span>
            </div>
          </li>
        ))}
      </ul>
    </details>
  )
}
