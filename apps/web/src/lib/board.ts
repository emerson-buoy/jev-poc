import type { DiscardReason, TicketRead, TicketStatus } from '@/lib/api/generated'

export type Department = NonNullable<TicketRead['effective_department']>

export const DEPARTMENTS: readonly Department[] = ['billing', 'technical', 'general']

export const COLUMNS: readonly { status: TicketStatus; label: string; hint: string }[] = [
  { status: 'new', label: 'New', hint: 'Drag a card to Triaged to ask Jev' },
  { status: 'triaged', label: 'Triaged', hint: 'Department, urgency and refund decided' },
  { status: 'in_progress', label: 'In progress', hint: 'Being worked on' },
  { status: 'done', label: 'Done', hint: 'Resolved' },
]

const URGENCY_LABELS = ['Low', 'Minor', 'Medium', 'High', 'Critical'] as const

export function urgencyLabel(level: number): string {
  return URGENCY_LABELS[Math.min(Math.max(level, 1), 5) - 1]
}

export function departmentLabel(department: string): string {
  return department.charAt(0).toUpperCase() + department.slice(1)
}

export function statusLabel(status: TicketStatus): string {
  return COLUMNS.find((c) => c.status === status)?.label ?? status
}

export function formatPercent(probability: number): string {
  return `${Math.round(probability * 100)}%`
}

export function groupByStatus(tickets: readonly TicketRead[]): Record<TicketStatus, TicketRead[]> {
  const grouped: Record<TicketStatus, TicketRead[]> = {
    new: [],
    triaged: [],
    in_progress: [],
    done: [],
  }
  for (const ticket of tickets) grouped[ticket.status].push(ticket)
  return grouped
}

export const DEPARTMENT_CLASSES: Record<Department, string> = {
  billing: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
  technical: 'bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100',
  general: 'bg-slate-200 text-slate-900 dark:bg-slate-700/60 dark:text-slate-100',
}

export function urgencyClasses(level: number): string {
  if (level >= 4) return 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100'
  if (level === 3) return 'bg-orange-100 text-orange-900 dark:bg-orange-900/40 dark:text-orange-100'
  return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100'
}

const DISCARD_REASONS: Record<DiscardReason, string> = {
  moved_to_new: 'moved back to New',
  retriaged: 'replaced by a re-triage',
}

export function discardReasonLabel(reason: DiscardReason): string {
  return DISCARD_REASONS[reason] ?? reason
}
