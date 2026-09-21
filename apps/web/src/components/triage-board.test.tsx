import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { TriageBoard } from '@/components/triage-board'
import { mockMeta, tickets } from '@/lib/fixtures'

vi.mock('@/server/tickets', () => ({
  fetchTickets: vi.fn(),
  fetchMeta: vi.fn(),
  addTicket: vi.fn(),
  moveTicketTo: vi.fn(),
  retriage: vi.fn(),
  patchTicket: vi.fn(),
  removeTicket: vi.fn(),
}))

import { fetchMeta, fetchTickets } from '@/server/tickets'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('TriageBoard', () => {
  beforeEach(() => {
    vi.mocked(fetchTickets).mockResolvedValue(tickets)
    vi.mocked(fetchMeta).mockResolvedValue(mockMeta)
  })

  it('renders four columns with the right cards and counts', async () => {
    render(<TriageBoard />, { wrapper })
    await screen.findByText('Checkout returning 500 errors')
    const newColumn = screen.getByRole('region', { name: 'New' })
    expect(within(newColumn).getAllByRole('button')).toHaveLength(2)
    expect(within(newColumn).getByText('2')).toBeInTheDocument()
    const done = screen.getByRole('region', { name: 'Done' })
    expect(within(done).getByText('Dark mode?')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Triaged' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'In progress' })).toBeInTheDocument()
  })

  it('shows the mock banner when the API runs the mock provider', async () => {
    render(<TriageBoard />, { wrapper })
    expect(await screen.findByRole('status')).toHaveTextContent(/mock triage/i)
  })
})
