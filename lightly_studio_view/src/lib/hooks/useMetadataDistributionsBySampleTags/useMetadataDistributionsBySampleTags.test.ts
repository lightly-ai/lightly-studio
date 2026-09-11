import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    useMetadataDistributionsBySampleTags,
    withSampleTagFilter
} from './useMetadataDistributionsBySampleTags.svelte';

interface QueryResult {
    data?: unknown;
    isFetching: boolean;
    error: Error | null;
}

interface CapturedOptions {
    queries: { queryKey: readonly unknown[] }[];
    combine?: (results: QueryResult[]) => unknown;
}

const createQueriesMock = vi.hoisted(() => vi.fn<(getOptions: () => CapturedOptions) => unknown>());

vi.mock('@tanstack/svelte-query', async (importOriginal) => ({
    ...(await importOriginal<typeof import('@tanstack/svelte-query')>()),
    createQueries: createQueriesMock
}));

describe('withSampleTagFilter', () => {
    it('preserves exploration filters and scopes the request to one comparison tag', () => {
        expect(
            withSampleTagFilter(
                {
                    width: { min: 100 },
                    sample_filter: { sample_ids: ['sample-1'], tag_ids: ['grid-tag'] }
                },
                'comparison-tag'
            )
        ).toEqual({
            width: { min: 100 },
            sample_filter: { sample_ids: ['sample-1'], tag_ids: ['comparison-tag'] }
        });
    });
});

describe('useMetadataDistributionsBySampleTags', () => {
    let capturedOptions: CapturedOptions;

    beforeEach(() => {
        createQueriesMock.mockImplementation((getOptions) => {
            capturedOptions = getOptions();
            return {};
        });
    });

    it('creates one numeric query per selected tag for the active field', () => {
        useMetadataDistributionsBySampleTags(() => ({
            collectionId: 'collection-1',
            field: { name: 'score', type: 'numeric' },
            sampleTags: [
                { id: 'tag-a', label: 'Reviewed' },
                { id: 'tag-b', label: 'Priority' }
            ],
            binCount: 50
        }));

        expect(capturedOptions.queries).toHaveLength(2);
        expect(capturedOptions.queries[0].queryKey).toContainEqual(
            expect.objectContaining({
                body: expect.objectContaining({
                    bin_count: 50,
                    fields: ['score'],
                    filters: expect.objectContaining({
                        sample_filter: expect.objectContaining({ tag_ids: ['tag-a'] })
                    })
                })
            })
        );
        expect(capturedOptions.queries[1].queryKey).toContainEqual(
            expect.objectContaining({
                body: expect.objectContaining({
                    filters: expect.objectContaining({
                        sample_filter: expect.objectContaining({ tag_ids: ['tag-b'] })
                    })
                })
            })
        );
    });

    it('creates and combines one categorical query per selected tag', () => {
        useMetadataDistributionsBySampleTags(() => ({
            collectionId: 'collection-1',
            field: { name: 'city', type: 'categorical' },
            sampleTags: [{ id: 'tag-a', label: 'Reviewed' }]
        }));

        expect(capturedOptions.queries).toHaveLength(1);
        expect(capturedOptions.queries[0].queryKey).toContainEqual(
            expect.objectContaining({ body: expect.objectContaining({ fields: ['city'] }) })
        );

        const result = capturedOptions.combine?.([
            {
                data: { city: { value_counts: [{ value: 'Zurich', count: 4 }] } },
                isFetching: false,
                error: null
            }
        ]);

        expect(result).toMatchObject({
            data: [{ id: 'tag-a', categorical: { city: [{ label: 'Zurich', count: 4 }] } }],
            isFetching: false,
            error: null
        });
    });

    it('combines available categorical and numeric results without hiding partial data', () => {
        useMetadataDistributionsBySampleTags(() => ({
            collectionId: 'collection-1',
            field: { name: 'score', type: 'numeric' },
            sampleTags: [
                { id: 'tag-a', label: 'Reviewed' },
                { id: 'tag-b', label: 'Priority' }
            ]
        }));

        const result = capturedOptions.combine?.([
            {
                data: { score: { bin_edges: [0, 1, 2], counts: [3, 1] } },
                isFetching: false,
                error: null
            },
            { data: undefined, isFetching: false, error: new Error('numeric failed') }
        ]);

        expect(result).toMatchObject({
            data: [
                {
                    id: 'tag-a',
                    label: 'Reviewed',
                    histograms: { score: { binEdges: [0, 1, 2], counts: [3, 1] } },
                    categorical: {}
                }
            ],
            error: new Error('numeric failed')
        });
    });
});
