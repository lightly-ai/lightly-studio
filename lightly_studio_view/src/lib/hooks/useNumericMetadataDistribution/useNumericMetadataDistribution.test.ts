import { describe, expect, it } from 'vitest';
import type { MetadataInfo } from '$lib/services/types';
import { selectDistributions } from './useNumericMetadataDistribution';

const metadataInfo: MetadataInfo[] = [
    {
        name: 'temperature',
        type: 'float',
        min: 0,
        max: 100,
        histogram: { bin_edges: [0, 50, 100], counts: [3, 7] }
    },
    {
        name: 'count',
        type: 'integer',
        min: 1,
        max: 10,
        histogram: { bin_edges: [1, 5.5, 10], counts: [4, 2] }
    },
    { name: 'location', type: 'string' },
    { name: 'score_without_histogram', type: 'float', min: 0, max: 1, histogram: null }
];

describe('selectDistributions', () => {
    it('maps numeric fields with histograms to bin data', () => {
        const distributions = selectDistributions(metadataInfo);

        expect(distributions.temperature).toEqual({ binEdges: [0, 50, 100], counts: [3, 7] });
        expect(distributions.count).toEqual({ binEdges: [1, 5.5, 10], counts: [4, 2] });
    });

    it('omits fields without a histogram', () => {
        const distributions = selectDistributions(metadataInfo);

        expect(distributions).not.toHaveProperty('location');
        expect(distributions).not.toHaveProperty('score_without_histogram');
    });

    it('returns an empty record for empty metadata info', () => {
        expect(selectDistributions([])).toEqual({});
    });
});
