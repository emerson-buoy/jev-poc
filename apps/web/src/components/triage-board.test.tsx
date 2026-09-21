import { render, screen, waitFor, within } from '@testing-library/react'
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

type Listener = (event: MessageEvent) => void

class FakeEventSource {
  static instances: FakeEventSource[] = []
  closed = false
  private listeners = new Map<string, Set<Listener>>()

  constructor(public url: string) {
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: Listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set())
    this.listeners.get(type)!.add(listener)
  }

  removeEventListener(type: string, listener: Listener) {
    this.listeners.get(type)?.delete(listener)
  }

  emit(type: string, data?: string) {
    this.listeners.get(type)?.forEach((listener) => listener(new MessageEvent(type, { data })))
  }

  close() {
    this.closed = true
  }
}

describe('TriageBoard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchTickets).mockResolvedValue(tickets)
    vi.mocked(fetchMeta).mockResolvedValue(mockMeta)
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
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

  it('listens for ticket changes and refetches on each one', async () => {
    render(<TriageBoard />, { wrapper })
    await screen.findByText('Checkout returning 500 errors')
    expect(fetchTickets).toHaveBeenCalledTimes(1)
    const [source] = FakeEventSource.instances
    expect(source.url).toBe('/api/events')
    source.emit('tickets.changed', JSON.stringify({ id: 1, action: 'moved' }))
    await waitFor(() => expect(fetchTickets).toHaveBeenCalledTimes(2))
  })

  it('refetches when the stream (re)opens', async () => {
    render(<TriageBoard />, { wrapper })
    await screen.findByText('Checkout returning 500 errors')
    FakeEventSource.instances[0].emit('open')
    await waitFor(() => expect(fetchTickets).toHaveBeenCalledTimes(2))
  })

  it('closes the stream on unmount', async () => {
    const { unmount } = render(<TriageBoard />, { wrapper })
    await screen.findByText('Checkout returning 500 errors')
    unmount()
    expect(FakeEventSource.instances[0].closed).toBe(true)
  })
})
