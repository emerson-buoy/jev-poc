import { useEffect, useRef, useState } from 'react'
import { dropTargetForElements } from '@atlaskit/pragmatic-drag-and-drop/element/adapter'
import { TicketCard } from '@/components/ticket-card'
import { cn } from '@/lib/utils'
import type { TicketRead, TicketStatus } from '@/lib/api/generated'

interface BoardColumnProps {
  status: TicketStatus
  label: string
  hint: string
  tickets: TicketRead[]
  onOpen: (id: number) => void
}

export function BoardColumn({ status, label, hint, tickets, onOpen }: BoardColumnProps) {
  const ref = useRef<HTMLElement>(null)
  const [over, setOver] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    return dropTargetForElements({
      element,
      getData: () => ({ status }),
      onDragEnter: () => setOver(true),
      onDragLeave: () => setOver(false),
      onDrop: () => setOver(false),
    })
  }, [status])

  return (
    <section
      ref={ref}
      aria-label={label}
      className={cn(
        'flex min-h-64 flex-col rounded-xl border bg-muted/40 p-3 transition-colors',
        over && 'border-primary bg-primary/5',
      )}
    >
      <header className="mb-3 flex items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">{label}</h2>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </div>
        <span className="rounded-full bg-background px-2 py-0.5 text-xs font-medium tabular-nums">
          {tickets.length}
        </span>
      </header>
      <div className="flex flex-1 flex-col gap-2">
        {tickets.map((ticket) => (
          <TicketCard key={ticket.id} ticket={ticket} onOpen={onOpen} />
        ))}
      </div>
    </section>
  )
}
