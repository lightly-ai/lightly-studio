import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { getAllVideos, type QueryExpr } from '$lib/api/lightly_studio_local';
import { useVideoFilters } from '$lib/hooks';
import VideoPageTestWrapper from './VideoPageTestWrapper.test.svelte';

const { collectionId } = await vi.hoisted(async () => {
    const { writable } = await import('svelte/store');
    return { collectionId: writable('videos') };
});
vi.mock('$app/state', async () => {
    const { fromStore } = await import('svelte/store');
    const route = fromStore(collectionId);
    return {
        page: {
            get params() {
                return { collection_id: route.current };
            }
        }
    };
});
vi.mock('$lib/api/lightly_studio_local/sdk.gen', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local/sdk.gen')>()),
    getAllVideos: vi.fn(async () => ({
        data: { data: [{ sample_id: 'clip', file_name: 'clip.mp4' }], total_count: 1 }
    }))
}));
vi.mock('$lib/hooks/useTags/useTags', async () => {
    const { writable } = await import('svelte/store');
    return { useTags: () => ({ tagsSelected: writable(new Set(['reviewed'])) }) };
});
vi.mock('$lib/hooks/useVideosBounds/useVideosBounds', async () => {
    const { writable } = await import('svelte/store');
    return { useVideoBounds: () => ({ videoBoundsValues: writable(null) }) };
});
vi.mock('$lib/components/VideoItem/VideoItem.svelte', () => ({ default: vi.fn() }));

const queryExpr: QueryExpr = {
    match_expr: {
        type: 'ordinal_float_expr',
        field: { table: 'video', name: 'duration_s' },
        operator: '>',
        value: 10
    }
};
const expression = { query_expr: queryExpr, query_expr_str: 'duration_s > 10' };
const filters = useVideoFilters();

beforeEach(() => {
    vi.clearAllMocks();
    collectionId.set('videos');
    filters.filterParams.set(null);
    filters.updateQueryExpr();
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
    Element.prototype.scrollTo = vi.fn();
    vi.stubGlobal(
        'ResizeObserver',
        class {
            observe: ResizeObserver['observe'];
            constructor(callback: ResizeObserverCallback) {
                this.observe = (target) =>
                    callback(
                        [
                            {
                                target,
                                contentRect: { width: 800, height: 600 }
                            } as ResizeObserverEntry
                        ],
                        this
                    );
            }
            unobserve() {}
            disconnect() {}
        }
    );
});
afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe('video grid queries', () => {
    it('applies and clears the query without losing tags, and resets scrolling', async () => {
        render(VideoPageTestWrapper);
        await screen.findByTestId('video-grid-item');
        vi.mocked(Element.prototype.scrollTo).mockClear();

        await act(() => filters.updateQueryExpr(expression));
        await waitFor(() =>
            expect(lastVideoRequest()?.body?.filter?.sample_filter).toEqual({
                tag_ids: ['reviewed'],
                query_expr: queryExpr
            })
        );
        expect(Element.prototype.scrollTo).toHaveBeenCalledWith(
            expect.objectContaining({ top: 0 })
        );

        await act(() => filters.updateQueryExpr());
        await waitFor(() =>
            expect(lastVideoRequest()?.body?.filter?.sample_filter).toEqual({
                tag_ids: ['reviewed']
            })
        );
    });

    it('never sends the previous collection query to a new collection', async () => {
        filters.updateFilterParams({ collection_id: 'videos' });
        filters.updateQueryExpr(expression);
        render(VideoPageTestWrapper);
        await waitFor(() =>
            expect(lastVideoRequest()?.body?.filter?.sample_filter?.query_expr).toEqual(queryExpr)
        );

        await act(() => collectionId.set('other-videos'));
        await waitFor(() => expect(lastVideoRequest()?.path.collection_id).toBe('other-videos'));
        const nextRequests = vi
            .mocked(getAllVideos)
            .mock.calls.filter(([request]) => request.path.collection_id === 'other-videos');
        for (const [request] of nextRequests) {
            expect(request.body?.filter?.sample_filter?.query_expr).toBeUndefined();
        }
    });
});

function lastVideoRequest() {
    return vi.mocked(getAllVideos).mock.calls.at(-1)?.[0];
}
