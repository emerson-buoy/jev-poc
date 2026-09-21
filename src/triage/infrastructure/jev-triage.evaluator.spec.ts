import { JevTriageEvaluator } from './jev-triage.evaluator.js';

const { evaluateMock } = vi.hoisted(() => ({ evaluateMock: vi.fn() }));

vi.mock('ai', () => ({ experimental_evaluate: evaluateMock }));

const gatewayResult = {
  answers: {
    department: {
      type: 'choice',
      choice: 'billing',
      probabilities: { billing: 0.9, technical: 0.05, general: 0.05 },
    },
    urgency: {
      type: 'score',
      score: 2.5,
      probabilities: { '0': 0, '1': 0, '2': 0.5, '3': 0.5, '4': 0 },
    },
    refund_requested: { type: 'boolean', probability: 0.95 },
  },
  providerMetadata: {
    typesafe: { confidence: { department: 0.8, urgency: 0.6 } },
  },
};

describe('JevTriageEvaluator', () => {
  const evaluator = new JevTriageEvaluator({
    aiGatewayApiKey: 'k',
    jevModelId: 'typesafe-ai/jev',
  });

  beforeEach(() => {
    evaluateMock.mockReset();
    evaluateMock.mockResolvedValue(gatewayResult);
  });

  it('calls experimental_evaluate with the configured model and the ticket as state', async () => {
    await evaluator.evaluate('ticket text');
    expect(evaluateMock).toHaveBeenCalledTimes(1);
    const call = evaluateMock.mock.calls[0][0];
    expect(call.model).toBe('typesafe-ai/jev');
    expect(call.state).toBe('ticket text');
  });

  it('asks a choice, a five-level score and a boolean question', async () => {
    await evaluator.evaluate('t');
    const { questions } = evaluateMock.mock.calls[0][0];
    expect(questions.department.type).toBe('choice');
    expect(Object.keys(questions.department.criteria)).toEqual([
      'billing',
      'technical',
      'general',
    ]);
    expect(questions.urgency.type).toBe('score');
    expect(questions.urgency.criteria).toHaveLength(5);
    expect(questions.refund_requested.type).toBe('boolean');
  });

  it('maps the gateway answers to a neutral evaluation', async () => {
    const evaluation = await evaluator.evaluate('t');
    expect(evaluation).toEqual({
      department: {
        choice: 'billing',
        probabilities: { billing: 0.9, technical: 0.05, general: 0.05 },
      },
      urgency: {
        score: 2.5,
        probabilities: { '0': 0, '1': 0, '2': 0.5, '3': 0.5, '4': 0 },
      },
      refund: { probability: 0.95 },
      confidence: { department: 0.8, urgency: 0.6 },
    });
  });

  it('omits confidence when the provider does not return it', async () => {
    evaluateMock.mockResolvedValue({ ...gatewayResult, providerMetadata: {} });
    const evaluation = await evaluator.evaluate('t');
    expect(evaluation.confidence).toBeUndefined();
  });
});
