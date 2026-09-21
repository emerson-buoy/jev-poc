import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ProbabilityBars } from '@/components/probability-bars'
import { TriageHistory } from '@/components/triage-history'
import type { TicketRead } from '@/lib/api/generated'
import {
  DEPARTMENTS,
  departmentLabel,
  formatPercent,
  statusLabel,
  urgencyLabel,
  type Department,
} from '@/lib/board'
import { useDeleteTicket, useRetriage, useUpdateTicket } from '@/lib/queries'

interface TicketDetailProps {
  ticket: TicketRead
  onClose: () => void
}

export function TicketDetail({ ticket, onClose }: TicketDetailProps) {
  const retriage = useRetriage()
  const update = useUpdateTicket()
  const remove = useDeleteTicket()
  const { triage } = ticket

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="flex w-full flex-col gap-0 overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{ticket.title}</SheetTitle>
          <SheetDescription>
            {statusLabel(ticket.status)} · created{' '}
            <span suppressHydrationWarning>{new Date(ticket.created_at).toLocaleString()}</span>
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-6 px-4 pb-4">
          <p className="text-sm whitespace-pre-wrap">{ticket.description}</p>

          {triage ? (
            <>
              <section className="space-y-2">
                <Label htmlFor="department">Department</Label>
                <NativeSelect
                  id="department"
                  value={ticket.effective_department ?? triage.department}
                  disabled={update.isPending}
                  onChange={(event) =>
                    update.mutate({
                      id: ticket.id,
                      department_override:
                        event.target.value === triage.department
                          ? null
                          : (event.target.value as Department),
                    })
                  }
                >
                  {DEPARTMENTS.map((d) => (
                    <NativeSelectOption key={d} value={d}>
                      {departmentLabel(d)}
                    </NativeSelectOption>
                  ))}
                </NativeSelect>
                <p className="text-xs text-muted-foreground">
                  {ticket.department_override
                    ? `Overridden. Jev suggested ${departmentLabel(triage.department)}.`
                    : "Jev's choice. Pick another department to override it."}
                </p>
                <ProbabilityBars
                  rows={DEPARTMENTS.map((d) => ({
                    key: d,
                    label: departmentLabel(d),
                    probability: triage.department_probabilities[d] ?? 0,
                    highlight: d === triage.department,
                  }))}
                />
              </section>

              <section className="space-y-2">
                <h3 className="text-sm font-medium">
                  Urgency {triage.urgency_level}/5 · {urgencyLabel(triage.urgency_level)}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    mean {triage.urgency_mean.toFixed(1)}
                  </span>
                </h3>
                <ProbabilityBars
                  rows={[1, 2, 3, 4, 5].map((level) => ({
                    key: String(level),
                    label: `Level ${level}`,
                    probability: triage.urgency_probabilities[String(level)] ?? 0,
                    highlight: level === triage.urgency_level,
                  }))}
                />
              </section>

              <section className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  Refund requested: {triage.refund_requested ? 'Yes' : 'No'}
                </span>
                <span className="text-muted-foreground">
                  {formatPercent(triage.refund_probability)}
                </span>
              </section>

              {triage.confidence && (
                <section className="space-y-1 text-xs text-muted-foreground">
                  <h3 className="font-medium text-foreground">Confidence</h3>
                  <ul className="flex flex-wrap gap-x-4">
                    {Object.entries(triage.confidence).map(([question, value]) => (
                      <li key={question}>
                        {question} {formatPercent(value)}
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              <p className="text-xs text-muted-foreground">
                Provider: {triage.provider} ·{' '}
                <span suppressHydrationWarning>
                  {new Date(triage.triaged_at).toLocaleString()}
                </span>
              </p>
            </>
          ) : (
            <p className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
              Not triaged yet. Move this card to Triaged to run Jev, or triage it now.
            </p>
          )}

          <TriageHistory records={ticket.history} />
        </div>

        <SheetFooter className="flex-row justify-between">
          <Button
            variant="destructive"
            size="sm"
            disabled={remove.isPending}
            onClick={() => remove.mutate({ id: ticket.id }, { onSuccess: onClose })}
          >
            Delete
          </Button>
          <Button
            size="sm"
            disabled={retriage.isPending}
            onClick={() => retriage.mutate({ id: ticket.id })}
          >
            {retriage.isPending ? 'Asking Jev...' : triage ? 'Re-triage' : 'Triage now'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
