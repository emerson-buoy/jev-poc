import { createFileRoute } from '@tanstack/react-router'
import { env } from '@/server/env'

const STREAM_HEADERS = {
  'Content-Type': 'text/event-stream',
  'Cache-Control': 'no-cache',
  Connection: 'keep-alive',
  'X-Accel-Buffering': 'no',
}

export const Route = createFileRoute('/api/events')({
  server: {
    handlers: {
      GET: async ({ request }) => {
        let upstream: Response
        try {
          upstream = await fetch(`${env.apiUrl}/events`, {
            signal: request.signal,
            headers: { Accept: 'text/event-stream' },
          })
        } catch {
          return new Response('Event stream unavailable', { status: 502 })
        }
        if (!upstream.ok || !upstream.body) {
          return new Response('Event stream unavailable', { status: 502 })
        }
        return new Response(upstream.body, { status: 200, headers: STREAM_HEADERS })
      },
    },
  },
})
