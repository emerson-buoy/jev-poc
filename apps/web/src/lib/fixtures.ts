import type { MetaRead, TicketRead, TriageRecordRead, TriageResult } from '@/lib/api/generated'

export const triaged: TriageResult = {
  department: 'technical',
  department_probabilities: { billing: 0.03, technical: 0.91, general: 0.06 },
  urgency_score: 2.05,
  urgency_level: 3,
  urgency_mean: 3.05,
  urgency_probabilities: { '1': 0.04, '2': 0.18, '3': 0.52, '4': 0.21, '5': 0.05 },
  refund_requested: false,
  refund_probability: 0.03,
  confidence: { department: 0.91, urgency: 0.52, refund_requested: 0.94 },
  provider: 'seed',
  triaged_at: '2026-09-21T09:00:00+00:00',
}

export const discardedRecord: TriageRecordRead = {
  id: 7,
  result: { ...triaged, department: 'billing', urgency_level: 2, provider: 'mock' },
  department_override: 'general',
  reason: 'moved_to_new',
  discarded_at: '2026-09-21T10:00:00+00:00',
}

export function ticket(overrides: Partial<TicketRead> = {}): TicketRead {
  return {
    id: 1,
    title: 'Checkout returning 500 errors',
    description: 'Our checkout page has been throwing a 500 error for the last 20 minutes.',
    status: 'new',
    department_override: null,
    triage: null,
    effective_department: null,
    history: [],
    created_at: '2026-09-21T08:00:00+00:00',
    updated_at: '2026-09-21T08:00:00+00:00',
    ...overrides,
  }
}

export const tickets: TicketRead[] = [
  ticket({ id: 1 }),
  ticket({ id: 2, title: 'Charged twice for October', description: 'Refund the duplicate.' }),
  ticket({
    id: 3,
    title: 'CSV export garbles names',
    description: 'Garbled characters since the update.',
    status: 'triaged',
    triage: triaged,
    effective_department: 'technical',
  }),
  ticket({
    id: 4,
    title: 'Webhooks delayed',
    description: 'Arriving hours late.',
    status: 'in_progress',
    triage: { ...triaged, urgency_level: 4, refund_requested: true, refund_probability: 0.8 },
    department_override: 'billing',
    effective_department: 'billing',
  }),
  ticket({
    id: 5,
    title: 'Dark mode?',
    description: 'Any plans?',
    status: 'done',
    triage: { ...triaged, department: 'general', urgency_level: 1 },
    effective_department: 'general',
  }),
]

export const mockMeta: MetaRead = { provider: 'mock', mock: true, circuit: 'closed' }
export const jevMeta: MetaRead = { provider: 'typesafe', mock: false, circuit: 'closed' }
export const openCircuitMeta: MetaRead = { provider: 'typesafe', mock: false, circuit: 'open' }
