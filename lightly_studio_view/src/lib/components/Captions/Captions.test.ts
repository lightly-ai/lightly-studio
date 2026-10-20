import { render } from '@testing-library/svelte';
import { get, readable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { useGlobalStorage } from '$lib/hooks';
import Captions from './Captions.svelte';

const mocks = vi.hoisted(() => ({
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
        useSamplesInfinite: () => ({
            data: readable([]),
            query: {
                isPending: false,
                isSuccess: mocks.pages.length > 0,
                data: { pages: mocks.pages },
                hasNextPage: false
            },
            loadMore: vi.fn(),
            refresh: vi.fn()
        })
    };
});

describe('Captions', () => {
    it('reports the samples and captions matched by the filters for the footer', () => {
        mocks.pages = [{ total_count: 2, total_caption_count: 3 }];

        render(Captions, { props: { collectionId: 'captions-id' } });

        const { filteredSampleCount, filteredCaptionCount } = useGlobalStorage();
        expect(get(filteredSampleCount)).toBe(2);
        expect(get(filteredCaptionCount)).toBe(3);
    });
});
