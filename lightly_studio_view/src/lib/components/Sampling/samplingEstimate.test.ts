import { describe, expect, it } from 'vitest';
import { estimateFinish, estimateSampling, formatDuration, formatRange } from './samplingEstimate';

describe('estimateSampling', () => {
    it('uses the fitted 512-dimensional MobileCLIP constants', () => {
        const estimate = estimateSampling({
            candidateCount: 10_000,
            selectionCount: 5_000,
            strategyCount: 1,
            embeddingDimension: 512
        });

        expect(estimate?.runtimeSeconds.base).toBeCloseTo(4.750923, 5);
    });

    it('scales with candidate count, selection count, and strategy count', () => {
        const base = estimateSampling({
            candidateCount: 1_000,
            selectionCount: 100,
            strategyCount: 1,
            embeddingDimension: 512
        })!;
        const moreCandidates = estimateSampling({
            candidateCount: 2_000,
            selectionCount: 100,
            strategyCount: 1,
            embeddingDimension: 512
        })!;
        const moreSelections = estimateSampling({
            candidateCount: 1_000,
            selectionCount: 200,
            strategyCount: 1,
            embeddingDimension: 512
        })!;
        const moreStrategies = estimateSampling({
            candidateCount: 1_000,
            selectionCount: 100,
            strategyCount: 3,
            embeddingDimension: 512
        })!;

        expect(moreCandidates.runtimeSeconds.base).toBeCloseTo(base.runtimeSeconds.base * 2);
        expect(moreSelections.runtimeSeconds.base).toBeGreaterThan(base.runtimeSeconds.base);
        expect(moreStrategies.runtimeSeconds.base).toBeCloseTo(base.runtimeSeconds.base * 3);
    });

    it('adds a 50 percent premium to the runtime upper bound', () => {
        const estimate = estimateSampling({
            candidateCount: 1_000,
            selectionCount: 100,
            strategyCount: 1,
            embeddingDimension: 512
        })!;

        expect(estimate.runtimeSeconds.premium).toBeCloseTo(estimate.runtimeSeconds.base * 1.5);
    });

    it.each([
        [0, 10, 1, 512],
        [-1, 10, 1, 512],
        [100, 0, 1, 512],
        [100, -1, 1, 512],
        [100, 10, 0, 512],
        [100, 10, -1, 512],
        [100, 10, 1, 0],
        [100, 10, 1, -1],
        [100, 101, 1, 512],
        [Number.NaN, 10, 1, 512]
    ])(
        'returns null for invalid input',
        (candidateCount, selectionCount, strategyCount, dimension) => {
            expect(
                estimateSampling({
                    candidateCount,
                    selectionCount,
                    strategyCount,
                    embeddingDimension: dimension
                })
            ).toBeNull();
        }
    );
});

describe('sampling estimate formatting', () => {
    it('rounds durations for readability', () => {
        expect(formatDuration(0.9)).toBe('<1 sec');
        expect(formatDuration(1.1)).toBe('2 sec');
        expect(formatDuration(61)).toBe('2 min');
        expect(formatDuration(3_601)).toBe('1 hr 1 min');
    });

    it('collapses ranges with equal formatted durations', () => {
        expect(formatRange({ base: 0.2, premium: 0.3 }, formatDuration)).toBe('<1 sec');
    });

    it('uses the premium runtime for the finish time', () => {
        const startedAt = new Date('2026-07-24T12:00:00.000Z');
        const estimate = estimateSampling({
            candidateCount: 10_000,
            selectionCount: 5_000,
            strategyCount: 1,
            embeddingDimension: 512
        })!;

        expect(estimateFinish({ startedAt, estimate }).getTime()).toBe(
            Math.trunc(startedAt.getTime() + estimate.runtimeSeconds.premium * 1_000)
        );
    });
});
