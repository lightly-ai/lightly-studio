import { describe, expect, it } from 'vitest';
import type { HistogramView } from '$lib/api/lightly_studio_local';
import { selectDistributions } from './useNumericMetadataDistribution';

const histograms: Record<string, HistogramView> = {
    temperature: { bin_edges: [0, 50, 100], counts: [3, 7] },
    count: { bin_edges: [1, 5.5, 10], counts: [4, 2] }
};

describe('selectDistributions', () => {
    it('maps the response to the Histogram component shape', () => {
        const distributions = selectDistributions(histograms);

        expect(distributions.temperature).toEqual({ binEdges: [0, 50, 100], counts: [3, 7] });
        expect(distributions.count).toEqual({ binEdges: [1, 5.5, 10], counts: [4, 2] });
    });

    it('returns an empty record while the query has no data yet', () => {
        expect(selectDistributions(undefined)).toEqual({});
    });

    it('returns an empty record for an empty response', () => {
        expect(selectDistributions({})).toEqual({});
    });
});
