import { Test } from '@nestjs/testing';
import { TriageCli } from './triage.cli.js';
import { TriageModule } from '../triage.module.js';
import {
  TRIAGE_EVALUATOR,
  type TriageEvaluation,
  type TriageEvaluator,
} from '../domain/triage-evaluator.js';
import {
  TRIAGE_PRESENTER,
  type TriagePresenter,
} from '../domain/triage-presenter.js';

const evaluation: TriageEvaluation = {
  department: { choice: 'general' },
  urgency: { score: 0.2 },
  refund: { probability: 0.1 },
};

describe('TriageCli', () => {
  let cli: TriageCli;
  let evaluator: TriageEvaluator;
  let presenter: TriagePresenter;

  beforeAll(() => vi.stubEnv('AI_GATEWAY_API_KEY', 'test-key'));
  afterAll(() => vi.unstubAllEnvs());

  beforeEach(async () => {
    evaluator = { evaluate: vi.fn().mockResolvedValue(evaluation) };
    presenter = {
      presentResult: vi.fn(),
      presentSummary: vi.fn(),
      presentError: vi.fn(),
    };
    const moduleRef = await Test.createTestingModule({
      imports: [TriageModule],
    })
      .overrideProvider(TRIAGE_EVALUATOR)
      .useValue(evaluator)
      .overrideProvider(TRIAGE_PRESENTER)
      .useValue(presenter)
      .compile();
    cli = moduleRef.get(TriageCli);
  });

  it('runs every sample ticket and prints a summary when given no args', async () => {
    const code = await cli.run([]);
    expect(code).toBe(0);
    expect(evaluator.evaluate).toHaveBeenCalledTimes(6);
    expect(presenter.presentResult).toHaveBeenCalledTimes(6);
    expect(presenter.presentSummary).toHaveBeenCalledTimes(1);
    const rows = vi.mocked(presenter.presentSummary).mock.calls[0][0];
    expect(rows).toHaveLength(6);
  });

  it('runs a single sample ticket with --id', async () => {
    const code = await cli.run(['--id', 't2']);
    expect(code).toBe(0);
    expect(evaluator.evaluate).toHaveBeenCalledTimes(1);
    expect(presenter.presentResult).toHaveBeenCalledWith(
      expect.stringMatching(/refund/i),
      expect.any(String),
      expect.objectContaining({ department: 'general' }),
    );
    expect(presenter.presentSummary).not.toHaveBeenCalled();
  });

  it('fails with exit code 1 on an unknown --id', async () => {
    const code = await cli.run(['--id', 'nope']);
    expect(code).toBe(1);
    expect(evaluator.evaluate).not.toHaveBeenCalled();
    expect(presenter.presentError).toHaveBeenCalledWith(
      expect.stringContaining('nope'),
    );
  });

  it('triages positional text as a custom ticket', async () => {
    const code = await cli.run(['my', 'custom ticket']);
    expect(code).toBe(0);
    expect(evaluator.evaluate).toHaveBeenCalledWith('my custom ticket');
    expect(presenter.presentResult).toHaveBeenCalledWith(
      'Custom ticket',
      'my custom ticket',
      expect.anything(),
    );
  });

  it('reports evaluator failures through the presenter', async () => {
    vi.mocked(evaluator.evaluate).mockRejectedValue(new Error('gateway down'));
    const code = await cli.run(['--id', 't1']);
    expect(code).toBe(1);
    expect(presenter.presentError).toHaveBeenCalledWith(
      expect.stringContaining('gateway down'),
    );
  });
});
