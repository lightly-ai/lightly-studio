import { describe, expect, it } from 'vitest';
import {
    buildCategoricalComparisonBuckets,
    buildCategoricalComparisonSeries
} from './buildCategoricalComparisonSeries';
import { truncatedCategoricalBuckets } from './sourceFixtures';

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

    it('counts the other and missing aggregates towards the denominator', () => {
        // The backend caps concrete values and reports the rest as aggregates, so
        // a truncated field's shares stay relative to every sample of the tag.
        const series = buildCategoricalComparisonSeries(
            [
                {
                    id: 'tag-a',
                    label: 'Reviewed',
                    categorical: { city: truncatedCategoricalBuckets }
                }
            ],
            'city'
        );

        expect(series[0].totalCount).toBe(14000);
    });

    it("carries each tag's own bucket total as the percentage denominator", () => {
        const series = buildCategoricalComparisonSeries(
            [
                {
                    id: 'tag-a',
                    label: 'Reviewed',
                    categorical: {
                        city: [
                            {
                                id: 'value-bern',
                                kind: 'value',
                                value: 'Bern',
                                label: 'Bern',
                                count: 2
                            },
                            {
                                id: 'value-zurich',
                                kind: 'value',
                                value: 'Zurich',
                                label: 'Zurich',
                                count: 8
                            }
                        ]
                    }
                },
                { id: 'tag-b', label: 'Priority', categorical: {} }
            ],
            'city'
        );

        expect(series.map(({ totalCount }) => totalCount)).toEqual([10, 0]);
    });
});

describe('buildCategoricalComparisonBuckets', () => {
    const comparisons = [
        {
            id: 'tag-a',
            label: 'Reviewed',
            categorical: {
                city: [
                    {
                        id: 'value-bern',
                        kind: 'value' as const,
                        value: 'Bern',
                        label: 'Bern',
                        count: 2
                    },
                    { id: 'other', kind: 'other' as const, label: 'Other', count: 1 }
                ]
            }
        },
        {
            id: 'tag-b',
            label: 'Priority',
            categorical: {
                city: [
                    {
                        id: 'value-bern',
                        kind: 'value' as const,
                        value: 'Bern',
                        label: 'Bern',
                        count: 5
                    },
                    {
                        id: 'value-zurich',
                        kind: 'value' as const,
                        value: 'Zurich',
                        label: 'Zurich',
                        count: 4
                    }
                ]
            }
        }
    ];

    it('keeps the filterable value of every bucket the tags contribute', () => {
        expect(buildCategoricalComparisonBuckets(comparisons, 'city')).toMatchObject([
            { id: 'value-bern', kind: 'value', value: 'Bern' },
            { id: 'other', kind: 'other' },
            { id: 'value-zurich', kind: 'value', value: 'Zurich' }
        ]);
    });

    it('sums the counts of a value several tags share', () => {
        const buckets = buildCategoricalComparisonBuckets(comparisons, 'city');
        expect(buckets.find(({ id }) => id === 'value-bern')?.count).toBe(7);
    });

    it('does not mutate the buckets it was given', () => {
        buildCategoricalComparisonBuckets(comparisons, 'city');
        expect(comparisons[0].categorical.city[0].count).toBe(2);
    });

    it('disambiguates a literal "Missing" from the missing bucket', () => {
        expect(
            buildCategoricalComparisonBuckets(
                [
                    {
                        id: 'tag-a',
                        label: 'Reviewed',
                        categorical: {
                            city: [
                                {
                                    id: 'literal-missing',
                                    kind: 'value' as const,
                                    value: 'Missing',
                                    label: 'Missing',
                                    count: 2
                                },
                                {
                                    id: 'missing',
                                    kind: 'missing' as const,
                                    value: null,
                                    label: 'Missing',
                                    count: 3
                                }
                            ]
                        }
                    }
                ],
                'city'
            ).map(({ label }) => label)
        ).toEqual(['Missing (value)', 'Missing (no value)']);
    });

    it('returns nothing for a key none of the tags reported', () => {
        expect(buildCategoricalComparisonBuckets(comparisons, 'country')).toEqual([]);
    });
});
