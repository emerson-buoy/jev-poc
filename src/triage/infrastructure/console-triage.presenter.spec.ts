import { ConsoleTriagePresenter } from './console-triage.presenter.js';
import type { TriageResult } from '../domain/triage-result.js';

const result: TriageResult = {
  department: 'technical',
  departmentProbabilities: { billing: 0.1, technical: 0.85, general: 0.05 },
  urgencyScore: 3.4,
  urgencyLevel: 5,
  urgencyMean: 4.4,
  urgencyProbabilities: { '1': 0, '2': 0.1, '3': 0.1, '4': 0.2, '5': 0.6 },
  refundRequested: false,
  refundProbability: 0.12,
  confidence: { department: 0.9 },
};

describe('ConsoleTriagePresenter', () => {
  let lines: string[];
  let tables: unknown[];
  let presenter: ConsoleTriagePresenter;

  beforeEach(() => {
    lines = [];
    tables = [];
    vi.spyOn(console, 'log').mockImplementation((...args: unknown[]) => {
      lines.push(args.join(' '));
    });
    vi.spyOn(console, 'table').mockImplementation((data: unknown) => {
      tables.push(data);
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    presenter = new ConsoleTriagePresenter();
  });

  afterEach(() => vi.restoreAllMocks());

  it('prints the label, department, urgency and refund lines', () => {
    presenter.presentResult('Outage', 'Checkout is down', result);
    const output = lines.join('\n');
    expect(output).toContain('--- Outage ---');
    expect(output).toContain('Ticket: Checkout is down');
    expect(output).toContain('Department: technical');
    expect(output).toContain('Urgency: 5/5');
    expect(output).toContain('4.4/5');
    expect(output).toContain('Refund requested: no');
    expect(output).toContain('0.12');
  });

  it('prints one probability line per question and the confidence', () => {
    presenter.presentResult('Outage', 'x', result);
    const output = lines.join('\n');
    expect(output).toMatch(/billing 0\.10 \/ technical 0\.85 \/ general 0\.05/);
    expect(output).toMatch(
      /1 0\.00 \/ 2 0\.10 \/ 3 0\.10 \/ 4 0\.20 \/ 5 0\.60/,
    );
    expect(output).toMatch(/Confidence:.*department 0\.90/);
  });

  it('skips the confidence line when absent', () => {
    presenter.presentResult('Outage', 'x', {
      ...result,
      confidence: undefined,
    });
    expect(lines.join('\n')).not.toContain('Confidence');
  });

  it('truncates long ticket text at 80 characters', () => {
    const text = 'a'.repeat(100);
    presenter.presentResult('Long', text, result);
    const ticketLine = lines.find((l) => l.startsWith('Ticket:'))!;
    expect(ticketLine).toBe(`Ticket: ${'a'.repeat(80)}...`);
  });

  it('prints a summary table with one row per result', () => {
    presenter.presentSummary([
      { label: 'A', result },
      { label: 'B', result: { ...result, refundRequested: true } },
    ]);
    expect(tables).toHaveLength(1);
    expect(tables[0]).toEqual([
      { ticket: 'A', department: 'technical', urgency: '5/5', refund: 'no' },
      { ticket: 'B', department: 'technical', urgency: '5/5', refund: 'yes' },
    ]);
  });

  it('prints errors to stderr', () => {
    presenter.presentError('boom');
    expect(console.error).toHaveBeenCalledWith('boom');
  });
});
