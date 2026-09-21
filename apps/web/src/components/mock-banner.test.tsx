import { render, screen } from '@testing-library/react'
import { MockBanner } from '@/components/mock-banner'
import { jevMeta, mockMeta, openCircuitMeta } from '@/lib/fixtures'

describe('MockBanner', () => {
  it('warns when the mock provider is active', () => {
    render(<MockBanner meta={mockMeta} />)
    expect(screen.getByRole('status')).toHaveTextContent(/mock triage: no ai key configured/i)
  })

  it('renders nothing with the real provider', () => {
    const { container } = render(<MockBanner meta={jevMeta} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('reports an open circuit as Jev unavailable', () => {
    render(<MockBanner meta={openCircuitMeta} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/jev unavailable/i)
    expect(screen.getByRole('alert')).toHaveTextContent(/triaged/i)
  })

  it('renders nothing while the circuit is half open', () => {
    const { container } = render(<MockBanner meta={{ ...jevMeta, circuit: 'half_open' }} />)
    expect(container).toBeEmptyDOMElement()
  })
})
