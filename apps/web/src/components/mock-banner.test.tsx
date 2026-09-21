import { render, screen } from '@testing-library/react'
import { MockBanner } from '@/components/mock-banner'
import { jevMeta, mockMeta } from '@/lib/fixtures'

describe('MockBanner', () => {
  it('warns when the mock provider is active', () => {
    render(<MockBanner meta={mockMeta} />)
    expect(screen.getByRole('status')).toHaveTextContent(/mock triage: no ai key configured/i)
  })

  it('renders nothing with the real provider', () => {
    const { container } = render(<MockBanner meta={jevMeta} />)
    expect(container).toBeEmptyDOMElement()
  })
})
