import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { monitorForElements } from '@atlaskit/pragmatic-drag-and-drop/element/adapter'
import { BoardColumn } from '@/components/board-column'
import { MockBanner } from '@/components/mock-banner'
import { NewTicketDialog } from '@/components/new-ticket-dialog'
import { TicketDetail } from '@/components/ticket-detail'
import type { TicketStatus } from '@/lib/api/generated'
import { COLUMNS, groupByStatus } from '@/lib/board'
import { metaQuery, ticketsQuery, useMoveTicket } from '@/lib/queries'

export function TriageBoard() {
  const tickets = useQuery(ticketsQuery)
  const meta = useQuery(metaQuery)
  const move = useMoveTicket()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  useEffect(
    () =>
      monitorForElements({
        onDrop: ({ source, location }) => {
          const target = location.current.dropTargets[0]
          if (!target) return
          const id = source.data.id as number
          const status = target.data.status as TicketStatus
          if (status !== source.data.status) move.mutate({ id, status })
        },
      }),
    [move],
  )

  const grouped = groupByStatus(tickets.data ?? [])
  const selected = tickets.data?.find((t) => t.id === selectedId) ?? null

  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Jev Triage Board</h1>
          <p className="text-sm text-muted-foreground">
            Support tickets triaged by TypeSafe AI's Jev: department, urgency and refund intent.
          </p>
        </div>
        <NewTicketDialog />
      </header>

      <MockBanner meta={meta.data} />

      {tickets.isError && (
        <p role="alert" className="text-sm text-destructive">
          Could not load tickets: {tickets.error.message}
        </p>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {COLUMNS.map((column) => (
          <BoardColumn
            key={column.status}
            {...column}
            tickets={grouped[column.status]}
            onOpen={setSelectedId}
          />
        ))}
      </div>

      {selected && <TicketDetail ticket={selected} onClose={() => setSelectedId(null)} />}
    </main>
  )
}
