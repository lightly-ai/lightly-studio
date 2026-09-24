import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import Page from './+page.svelte';
import type { PageData } from './$types';
import { goto } from '$app/navigation';

// The route param dataset_id intentionally differs from the collection's dataset_id
// to prove navigation uses the collection's dataset_id (the regression this page fixes).
const ROUTE_DATASET_ID = 'route-dataset-id';
const COLLECTION_DATASET_ID = 'collection-dataset-id';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'route-dataset-id',
            collection_type: 'mcap',
            collection_id: 'collection-1'
        }
    }
}));

vi.mock('$lib/hooks', () => ({
    useGlobalStorage: () => ({
        setfilteredSampleCount: vi.fn(),
        sampleSize: writable({ width: 6, height: 200 })
    }),
    useMcapSequencesInfinite: () => ({
        data: writable([{ sample_id: 'sequence-1', sample_count: 5 }]),
        query: {
            isPending: false,
            isSuccess: true,
            isError: false,
            hasNextPage: false,
            isFetchingNextPage: false
        },
        loadMore: vi.fn(),
        totalCount: writable(1)
    })
}));

const mockPageData = {
    collection: { dataset_id: COLLECTION_DATASET_ID }
} as unknown as PageData;

class MockResizeObserver {
    constructor(private callback: ResizeObserverCallback) {}

    observe(target: Element) {
        this.callback(
            [{ target, contentRect: { width: 2000, height: 1000 } } as ResizeObserverEntry],
            this
        );
    }

    unobserve() {}
    disconnect() {}
}

class MockIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() {
        return [];
    }
    root = null;
    rootMargin = '';
    thresholds = [];
}

describe('point-clouds/+page.svelte', () => {
    beforeEach(() => {
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
        global.IntersectionObserver =
            MockIntersectionObserver as unknown as typeof IntersectionObserver;
        Element.prototype.scrollTo = vi.fn();
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(1000);
    });

    afterEach(() => vi.restoreAllMocks());

    it("navigates using the collection's dataset_id, not the route param", async () => {
        render(Page, { props: { data: mockPageData } });

        await fireEvent.click(screen.getByRole('button', { name: 'View MCAP sequence 1' }));

        expect(goto).toHaveBeenCalledOnce();
        const destination = vi.mocked(goto).mock.calls[0][0] as string;
        expect(destination).toContain(COLLECTION_DATASET_ID);
        expect(destination).not.toContain(ROUTE_DATASET_ID);
    });
});
