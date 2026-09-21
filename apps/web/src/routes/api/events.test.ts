import { Route } from '@/routes/api/events'

type Handler = (ctx: { request: Request }) => Promise<Response>
const { GET } = Route.options.server!.handlers as { GET: Handler }

describe('GET /api/events', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('pipes the API stream through with event-stream headers', async () => {
    fetchMock.mockResolvedValue(new Response('retry: 3000\n\n', { status: 200 }))
    const request = new Request('http://localhost:3000/api/events')
    const response = await GET({ request })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/events',
      expect.objectContaining({ signal: request.signal }),
    )
    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toBe('text/event-stream')
    expect(response.headers.get('cache-control')).toBe('no-cache')
    expect(response.headers.get('x-accel-buffering')).toBe('no')
    expect(await response.text()).toBe('retry: 3000\n\n')
  })

  it('returns 502 when the API is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'))
    const request = new Request('http://localhost:3000/api/events')
    const response = await GET({ request })
    expect(response.status).toBe(502)
  })
})
