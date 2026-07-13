import { describe, expect, it } from 'vitest';
import { distributionToCategoryCounts } from './useMetadataDistributionSeries';

describe('distributionToCategoryCounts', () => {
    it('maps categorical value/count pairs straight through', () => {
        const data = distributionToCategoryCounts({
            key: 'weather',
            type: 'string',
            kind: 'categorical',
            categorical: [
                { value: 'sunny', count: 12 },
                { value: '(none)', count: 3 }
            ]
        });

        expect(data).toEqual([
            { label: 'sunny', count: 12 },
            { label: '(none)', count: 3 }
        ]);
    });

    it('turns numeric bins into range labels and appends (none) when missing values exist', () => {
        const data = distributionToCategoryCounts({
            key: 'speed',
            type: 'float',
            kind: 'numeric',
            bin_edges: [0, 2.5, 5],
            counts: [4, 6],
            none_count: 2
        });

        expect(data).toEqual([
            { label: '0–2.5', count: 4 },
            { label: '2.5–5', count: 6 },
            { label: '(none)', count: 2 }
        ]);
    });

    it('omits the (none) bucket when no values are missing', () => {
        const data = distributionToCategoryCounts({
            key: 'speed',
            type: 'integer',
            kind: 'numeric',
            bin_edges: [0, 10, 20],
            counts: [3, 7],
            none_count: 0
        });

        expect(data).toEqual([
            { label: '0–10', count: 3 },
            { label: '10–20', count: 7 }
        ]);
    });
});
