import { Injectable } from '@nestjs/common';
import type { Ticket, TicketSource } from '../domain/ticket.js';

const SAMPLE_TICKETS: readonly Ticket[] = [
  {
    id: 't1',
    label: 'Outage, high urgency',
    text: "Our checkout page has been throwing a 500 error for the last 20 minutes. We're losing sales every minute this stays down. Please escalate immediately.",
  },
  {
    id: 't2',
    label: 'Refund request, billing',
    text: "I was charged twice for my October invoice. I'd like a refund for the duplicate charge as soon as possible.",
  },
  {
    id: 't3',
    label: 'Low urgency, general question',
    text: "Hi, just wondering if there's a way to change the display name on my account? No rush, whenever you get a chance.",
  },
  {
    id: 't4',
    label: 'Technical bug, medium urgency',
    text: "The CSV export feature has been generating files with garbled characters for non-English names since yesterday's update. Not blocking us yet but it's affecting a few customers.",
  },
  {
    id: 't5',
    label: 'Billing dispute, no refund requested',
    text: 'I noticed my plan renewed at a higher price than I expected. Can someone explain the pricing change? I just want clarity, not necessarily a refund.',
  },
  {
    id: 't6',
    label: 'Angry customer, refund + urgent',
    text: 'This is the third time your app has crashed and lost my work. I want a full refund immediately and I want this fixed today.',
  },
];

@Injectable()
export class InMemoryTicketSource implements TicketSource {
  all(): readonly Ticket[] {
    return SAMPLE_TICKETS;
  }

  findById(id: string): Ticket | undefined {
    return SAMPLE_TICKETS.find((ticket) => ticket.id === id);
  }
}
