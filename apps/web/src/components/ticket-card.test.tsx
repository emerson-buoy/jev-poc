import { render, screen, fireEvent } from '@testing-library/react'
import { TicketCard } from '@/components/ticket-card'
import { ticket, triaged } from '@/lib/fixtures'

describe('TicketCard', () => {
  it('shows title and a truncated description without badges when untriaged', () => {
    render(<TicketCard ticket={ticket()} onOpen={() => {}} />)
    expect(screen.getByText('Checkout returning 500 errors')).toBeInTheDocument()
    expect(screen.getByText(/checkout page has been throwing/)).toBeInTheDocument()
    expect(screen.queryByText(/urgency/i)).not.toBeInTheDocument()
    expect(screen.getByText('Not triaged')).toBeInTheDocument()
  })

  it('shows department, urgency and refund badges when triaged', () => {
    const t = ticket({
      status: 'triaged',
      triage: { ...triaged, refund_requested: true },
      effective_department: 'technical',
    })
    render(<TicketCard ticket={t} onOpen={() => {}} />)
    expect(screen.getByText('Technical')).toBeInTheDocument()
    expect(screen.getByText('Urgency 3/5')).toBeInTheDocument()
    expect(screen.getByText('Refund')).toBeInTheDocument()
  })

  it('marks a human override', () => {
    const t = ticket({
      status: 'triaged',
      triage: triaged,
      department_override: 'billing',
      effective_department: 'billing',
    })
    render(<TicketCard ticket={t} onOpen={() => {}} />)
    expect(screen.getByText('Billing')).toBeInTheDocument()
    expect(screen.getByTitle(/overridden/i)).toBeInTheDocument()
  })

  it('opens on click', () => {
    const onOpen = vi.fn()
    render(<TicketCard ticket={ticket()} onOpen={onOpen} />)
    fireEvent.click(screen.getByRole('button', { name: /checkout returning/i }))
    expect(onOpen).toHaveBeenCalledWith(1)
  })
})
