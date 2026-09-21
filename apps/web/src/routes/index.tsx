import { createFileRoute } from '@tanstack/react-router'
import { TriageBoard } from '@/components/triage-board'
import { metaQuery, ticketsQuery } from '@/lib/queries'

export const Route = createFileRoute('/')({
  loader: ({ context }) =>
    Promise.all([
      context.queryClient.ensureQueryData(ticketsQuery),
      context.queryClient.ensureQueryData(metaQuery),
    ]),
  component: TriageBoard,
})
