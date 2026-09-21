import { TriageService, REFUND_THRESHOLD } from './triage.service.js';
import type {
  TriageEvaluation,
  TriageEvaluator,
} from '../domain/triage-evaluator.js';

const baseEvaluation: TriageEvaluation = {
  department: {
    choice: 'billing',
    probabilities: { billing: 0.8, technical: 0.15, general: 0.05 },
  },
  urgency: {
    score: 3.2,
    probabilities: { '0': 0.05, '1': 0.05, '2': 0.1, '3': 0.3, '4': 0.5 },
  },
  refund: { probability: 0.9 },
};

function serviceWith(evaluation: TriageEvaluation) {
  const evaluator: TriageEvaluator = {
    evaluate: vi.fn().mockResolvedValue(evaluation),
  };
  return { service: new TriageService(evaluator), evaluator };
}

describe('TriageService', () => {
  it('passes the ticket text to the evaluator', async () => {
    const { service, evaluator } = serviceWith(baseEvaluation);
    await service.triage('some ticket');
    expect(evaluator.evaluate).toHaveBeenCalledWith('some ticket');
  });

  it('maps the department choice and its probabilities', async () => {
    const { service } = serviceWith(baseEvaluation);
    const result = await service.triage('t');
    expect(result.department).toBe('billing');
    expect(result.departmentProbabilities).toEqual({
      billing: 0.8,
      technical: 0.15,
      general: 0.05,
    });
  });

  it('keeps the raw 0-based score and derives a 1-based mean', async () => {
    const { service } = serviceWith(baseEvaluation);
    const result = await service.triage('t');
    expect(result.urgencyScore).toBe(3.2);
    expect(result.urgencyMean).toBeCloseTo(4.2);
  });

  it('picks the 1-based argmax level from the distribution', async () => {
    const { service } = serviceWith(baseEvaluation);
    const result = await service.triage('t');
    expect(result.urgencyLevel).toBe(5);
  });

  it('rounds the score for the level when no distribution is returned', async () => {
    const { service } = serviceWith({
      ...baseEvaluation,
      urgency: { score: 1.6 },
    });
    const result = await service.triage('t');
    expect(result.urgencyLevel).toBe(3);
    expect(result.urgencyProbabilities).toEqual({});
  });

  it('re-keys urgency probabilities to 1-based levels', async () => {
    const { service } = serviceWith(baseEvaluation);
    const result = await service.triage('t');
    expect(result.urgencyProbabilities).toEqual({
      '1': 0.05,
      '2': 0.05,
      '3': 0.1,
      '4': 0.3,
      '5': 0.5,
    });
  });

  it('flags a refund at or above the threshold', async () => {
    const { service } = serviceWith({
      ...baseEvaluation,
      refund: { probability: REFUND_THRESHOLD },
    });
    const result = await service.triage('t');
    expect(result.refundRequested).toBe(true);
    expect(result.refundProbability).toBe(REFUND_THRESHOLD);
  });

  it('does not flag a refund below the threshold', async () => {
    const { service } = serviceWith({
      ...baseEvaluation,
      refund: { probability: 0.49 },
    });
    const result = await service.triage('t');
    expect(result.refundRequested).toBe(false);
  });

  it('passes provider confidence through when present', async () => {
    const { service } = serviceWith({
      ...baseEvaluation,
      confidence: { department: 0.7 },
    });
    const result = await service.triage('t');
    expect(result.confidence).toEqual({ department: 0.7 });
  });

  it('leaves confidence undefined when absent', async () => {
    const { service } = serviceWith(baseEvaluation);
    const result = await service.triage('t');
    expect(result.confidence).toBeUndefined();
  });
});
