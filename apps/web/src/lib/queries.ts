import { queryOptions, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import type { TicketCreate, TicketRead, TicketStatus, TicketUpdate } from '@/lib/api/generated'
import {
  addTicket,
  fetchMeta,
  fetchTickets,
  moveTicketTo,
  patchTicket,
  removeTicket,
  retriage,
} from '@/server/tickets'

export const ticketsQuery = queryOptions({
  queryKey: ['tickets'],
  queryFn: () => fetchTickets(),
})

export const metaQuery = queryOptions({
  queryKey: ['meta'],
  queryFn: () => fetchMeta(),
  staleTime: Infinity,
})

function useInvalidateTickets() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ticketsQuery.queryKey })
}

/** Optimistic column move. A rejected move (for example a failed triage) snaps the card back. */
export function useMoveTicket() {
  const queryClient = useQueryClient()
  const invalidate = useInvalidateTickets()
  return useMutation({
    mutationFn: (data: { id: number; status: TicketStatus }) => moveTicketTo({ data }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ticketsQuery.queryKey })
      const previous = queryClient.getQueryData(ticketsQuery.queryKey)
      queryClient.setQueryData(ticketsQuery.queryKey, (tickets) =>
        tickets?.map((t) => (t.id === id ? { ...t, status } : t)),
      )
      return { previous }
    },
    onError: (error, _vars, context) => {
      queryClient.setQueryData(ticketsQuery.queryKey, context?.previous)
      toast.error('Move rejected', { description: error.message })
    },
    onSuccess: (ticket) => {
      if (ticket.status === 'triaged' && ticket.triage) {
        toast.success(`Triaged by ${ticket.triage.provider}`, {
          description: `${ticket.triage.department}, urgency ${ticket.triage.urgency_level}/5`,
        })
      }
    },
    onSettled: invalidate,
  })
}

export function useRetriage() {
  const invalidate = useInvalidateTickets()
  return useMutation({
    mutationFn: (data: { id: number }) => retriage({ data }),
    onSuccess: (ticket: TicketRead) =>
      toast.success(`Triaged by ${ticket.triage?.provider ?? 'unknown'}`),
    onError: (error) => toast.error('Triage failed', { description: error.message }),
    onSettled: invalidate,
  })
}

export function useUpdateTicket() {
  const invalidate = useInvalidateTickets()
  return useMutation({
    mutationFn: (data: { id: number } & TicketUpdate) => patchTicket({ data }),
    onError: (error) => toast.error('Update failed', { description: error.message }),
    onSettled: invalidate,
  })
}

export function useCreateTicket() {
  const invalidate = useInvalidateTickets()
  return useMutation({
    mutationFn: (data: TicketCreate) => addTicket({ data }),
    onSuccess: () => toast.success('Ticket created in New'),
    onError: (error) => toast.error('Could not create ticket', { description: error.message }),
    onSettled: invalidate,
  })
}

export function useDeleteTicket() {
  const invalidate = useInvalidateTickets()
  return useMutation({
    mutationFn: (data: { id: number }) => removeTicket({ data }),
    onError: (error) => toast.error('Delete failed', { description: error.message }),
    onSettled: invalidate,
  })
}
