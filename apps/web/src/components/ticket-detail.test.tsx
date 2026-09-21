import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { TicketDetail } from '@/components/ticket-detail'
import { ticket, triaged } from '@/lib/fixtures'

vi.mock('@/server/tickets', () => ({
  fetchTickets: vi.fn(),
  fetchMeta: vi.fn(),
  addTicket: vi.fn(),
  moveTicketTo: vi.fn(),
  retriage: vi.fn(),
  patchTicket: vi.fn(),
  removeTicket: vi.fn(),
}))

import { patchTicket, retriage } from '@/server/tickets'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const triagedTicket = ticket({
  id: 3,
  title: 'CSV export garbles names',
  status: 'triaged',
  triage: triaged,
  effective_department: 'technical',
})

describe('TicketDetail', () => {
  it('shows probabilities, confidence and the provider for a triaged ticket', () => {
    render(<TicketDetail ticket={triagedTicket} onClose={() => {}} />, { wrapper })
    expect(screen.getByRole('heading', { name: 'CSV export garbles names' })).toBeInTheDocument()
    expect(screen.getByText('Technical 91%')).toBeInTheDocument()
    expect(screen.getByText('Level 3 52%')).toBeInTheDocument()
    expect(screen.getByText(/refund requested/i)).toBeInTheDocument()
    expect(screen.getByText('3%')).toBeInTheDocument()
    expect(screen.getByText(/provider: seed/i)).toBeInTheDocument()
    expect(screen.getByText(/confidence/i)).toBeInTheDocument()
  })

  it('explains that an untriaged ticket has no result yet', () => {
    render(<TicketDetail ticket={ticket()} onClose={() => {}} />, { wrapper })
    expect(screen.getByText(/move this card to triaged/i)).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: /department/i })).not.toBeInTheDocument()
  })

  it('persists a department override through the select', async () => {
    vi.mocked(patchTicket).mockResolvedValue({
      ...triagedTicket,
      department_override: 'billing',
      effective_department: 'billing',
    })
    render(<TicketDetail ticket={triagedTicket} onClose={() => {}} />, { wrapper })
    const select = screen.getByRole('combobox', { name: /department/i })
    expect(select).toHaveValue('technical')
    fireEvent.change(select, { target: { value: 'billing' } })
    await waitFor(() =>
      expect(patchTicket).toHaveBeenCalledWith({
        data: { id: 3, department_override: 'billing' },
      }),
    )
  })

  it('re-triages on demand', async () => {
    vi.mocked(retriage).mockResolvedValue(triagedTicket)
    render(<TicketDetail ticket={triagedTicket} onClose={() => {}} />, { wrapper })
    fireEvent.click(screen.getByRole('button', { name: /re-triage/i }))
    await waitFor(() => expect(retriage).toHaveBeenCalledWith({ data: { id: 3 } }))
  })
})
