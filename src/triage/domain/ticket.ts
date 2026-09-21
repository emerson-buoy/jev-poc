export const TICKET_SOURCE = Symbol('TICKET_SOURCE');

export interface Ticket {
  readonly id: string;
  readonly label: string;
  readonly text: string;
}

export interface TicketSource {
  all(): readonly Ticket[];
  findById(id: string): Ticket | undefined;
}
