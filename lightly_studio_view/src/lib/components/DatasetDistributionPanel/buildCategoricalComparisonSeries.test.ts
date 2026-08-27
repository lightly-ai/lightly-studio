import { describe, expect, it } from 'vitest';
import { buildCategoricalComparisonSeries } from './buildCategoricalComparisonSeries';

describe('buildCategoricalComparisonSeries', () => {
    it('keeps value, missing, and other labels consistent across tag series', () => {
        const series = buildCategoricalComparisonSeries(
            [
                {
                    id: 'tag-a',
                    label: 'Reviewed',
                    categorical: {
                        city: [
                            {
                                id: 'literal-missing',
                                kind: 'value',
                                value: 'Missing',
                                label: 'Missing',
                                count: 2
                            },
                            {
                                id: 'other',
                                kind: 'other',
                                label: 'Other',
                                count: 1
                            }
                        ]
                    }
                },
                {
                    id: 'tag-b',
                    label: 'Priority',
                    categorical: {
                        city: [
                            {
                                id: 'missing',
                                kind: 'missing',
                                value: null,
                                label: 'Missing',
                                count: 3
                            }
                        ]
                    }
                }
            ],
            'city'
        );

        expect(series).toMatchObject([
            {
                label: 'Reviewed',
                data: [
                    { label: 'Missing (value)', count: 2 },
                    { label: 'Other', count: 1 }
                ]
            },
            { label: 'Priority', data: [{ label: 'Missing (no value)', count: 3 }] }
        ]);
    });
});
