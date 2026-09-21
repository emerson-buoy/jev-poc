import { useEffect, useRef, useState } from 'react'
import { draggable } from '@atlaskit/pragmatic-drag-and-drop/element/adapter'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { TicketRead } from '@/lib/api/generated'
import { DEPARTMENT_CLASSES, departmentLabel, urgencyClasses } from '@/lib/board'

interface TicketCardProps {
  ticket: TicketRead
  onOpen: (id: number) => void
}

export function TicketCard({ ticket, onOpen }: TicketCardProps) {
  const ref = useRef<HTMLButtonElement>(null)
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    return draggable({
      element,
      getInitialData: () => ({ id: ticket.id, status: ticket.status }),
      onDragStart: () => setDragging(true),
      onDrop: () => setDragging(false),
    })
  }, [ticket.id, ticket.status])

  const { triage, effective_department: department, department_override: override } = ticket

  return (
    <button
      ref={ref}
      type="button"
      onClick={() => onOpen(ticket.id)}
      className={cn(
        'w-full cursor-grab rounded-lg border bg-card p-3 text-left shadow-xs transition hover:border-primary/40 hover:shadow-sm focus-visible:ring-2 focus-visible:ring-ring',
        dragging && 'opacity-40',
      )}
    >
      <div className="text-sm font-medium leading-snug">{ticket.title}</div>
      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{ticket.description}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {triage && department ? (
          <>
            <Badge className={cn('border-transparent', DEPARTMENT_CLASSES[department])}>
              {departmentLabel(department)}
              {override && (
                <span title="Department overridden by a person" aria-label="overridden">
                  *
                </span>
              )}
            </Badge>
            <Badge className={cn('border-transparent', urgencyClasses(triage.urgency_level))}>
              Urgency {triage.urgency_level}/5
            </Badge>
            {triage.refund_requested && <Badge variant="destructive">Refund</Badge>}
          </>
        ) : (
          <Badge variant="outline" className="text-muted-foreground">
            {ticket.history.length > 0
              ? `Not triaged, ${ticket.history.length} discarded`
              : 'Not triaged'}
          </Badge>
        )}
      </div>
    </button>
  )
}
