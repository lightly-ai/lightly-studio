import { render } from '@testing-library/svelte';
import { get, readable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks';
import Captions from './Captions.svelte';

const mocks = vi.hoisted(() => ({
    tagsSelected: new Set<string>(),
    getSamplesParams: undefined as
        | (() => { body: { filters: Record<string, unknown> } })
        | undefined,
    metadataFilters: [{ name: 'width', min: 1, max: 2 }],
    pages: [] as { total_count: number; total_caption_count: number }[]
}));

vi.mock('@tanstack/svelte-query', () => ({
    createQuery: () => ({
        data: { collection_id: 'captions-id', parent_collection_id: 'parent-id' }
    })
}));

vi.mock('$lib/hooks', async () => {
    const actual = await vi.importActual<typeof import('$lib/hooks')>('$lib/hooks');
    return {
        ...actual,
        useSamplesInfinite: (getParams: () => { body: { filters: Record<string, unknown> } }) => {
            mocks.getSamplesParams = getParams;
            return {
                data: readable([]),
                query: {
                    isPending: false,
                    isSuccess: mocks.pages.length > 0,
                    data: { pages: mocks.pages },
                    hasNextPage: false
                },
                loadMore: vi.fn(),
                refresh: vi.fn()
            };
        },
        useTags: () => ({ tagsSelected: readable(mocks.tagsSelected) }),
        useMetadataFilters: () => ({
            metadataValues: readable({}),
            categoricalMetadataValues: readable({})
        }),
        createMetadataFilters: () => mocks.metadataFilters
    };
});

const renderCaptions = () => {
    mocks.getSamplesParams = undefined;
    render(Captions, { props: { collectionId: 'captions-id' } });
    return mocks.getSamplesParams!().body.filters;
};

describe('Captions', () => {
    beforeEach(() => {
        mocks.tagsSelected = new Set();
        mocks.pages = [];
    });

    it('queries captions of the parent collection with the selected tags and metadata filters', () => {
        mocks.tagsSelected = new Set(['tag-1', 'tag-2']);

        const filters = renderCaptions();

        expect(filters).toEqual({
            has_captions: true,
            tag_ids: ['tag-1', 'tag-2'],
            metadata_filters: mocks.metadataFilters
        });
    });

    it('omits tag_ids when no tag is selected', () => {
        const filters = renderCaptions();

        expect(filters.tag_ids).toBeUndefined();
    });

    it('reports the samples and captions matched by the filters for the footer', () => {
        mocks.pages = [{ total_count: 2, total_caption_count: 3 }];

        renderCaptions();

        const { filteredSampleCount, filteredCaptionCount } = useGlobalStorage();
        expect(get(filteredSampleCount)).toBe(2);
        expect(get(filteredCaptionCount)).toBe(3);
    });
});
