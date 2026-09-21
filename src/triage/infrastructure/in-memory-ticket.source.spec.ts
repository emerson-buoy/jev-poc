import { InMemoryTicketSource } from './in-memory-ticket.source.js';

describe('InMemoryTicketSource', () => {
  const source = new InMemoryTicketSource();

  it('holds the six sample tickets with unique ids', () => {
    const tickets = source.all();
    expect(tickets).toHaveLength(6);
    expect(new Set(tickets.map((t) => t.id)).size).toBe(6);
  });

  it('finds a ticket by id', () => {
    expect(source.findById('t2')?.label).toMatch(/refund/i);
  });

  it('returns undefined for an unknown id', () => {
    expect(source.findById('nope')).toBeUndefined();
  });

  it('contains no em-dash characters', () => {
    for (const ticket of source.all()) {
      expect(ticket.text).not.toContain(String.fromCharCode(0x2014));
    }
  });
});
