import { createServerFn } from '@tanstack/react-start'
import {
  createTicket,
  deleteTicket,
  listTickets,
  moveTicket,
  readMeta,
  retriageTicket,
  updateTicket,
  type MetaRead,
  type TicketCreate,
  type TicketRead,
  type TicketStatus,
  type TicketUpdate,
} from '@/lib/api/generated'
import { unwrap } from '@/server/api-client'

export const fetchTickets = createServerFn().handler(
  async (): Promise<TicketRead[]> => unwrap(await listTickets()),
)

export const fetchMeta = createServerFn().handler(
  async (): Promise<MetaRead> => unwrap(await readMeta()),
)

export const addTicket = createServerFn({ method: 'POST' })
  .validator((data: TicketCreate) => data)
  .handler(async ({ data }): Promise<TicketRead> => unwrap(await createTicket({ body: data })))

export const moveTicketTo = createServerFn({ method: 'POST' })
  .validator((data: { id: number; status: TicketStatus }) => data)
  .handler(
    async ({ data }): Promise<TicketRead> =>
      unwrap(await moveTicket({ path: { ticket_id: data.id }, body: { status: data.status } })),
  )

export const retriage = createServerFn({ method: 'POST' })
  .validator((data: { id: number }) => data)
  .handler(
    async ({ data }): Promise<TicketRead> =>
      unwrap(await retriageTicket({ path: { ticket_id: data.id } })),
  )

export const patchTicket = createServerFn({ method: 'POST' })
  .validator((data: { id: number } & TicketUpdate) => data)
  .handler(async ({ data: { id, ...body } }): Promise<TicketRead> =>
    unwrap(await updateTicket({ path: { ticket_id: id }, body })),
  )

export const removeTicket = createServerFn({ method: 'POST' })
  .validator((data: { id: number }) => data)
  .handler(async ({ data }): Promise<void> => {
    unwrap(await deleteTicket({ path: { ticket_id: data.id } }))
  })
