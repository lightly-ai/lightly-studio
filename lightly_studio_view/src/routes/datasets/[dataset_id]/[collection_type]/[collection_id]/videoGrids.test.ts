import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { get, writable } from 'svelte/store';
import FramesPage from './frames/+page.svelte';
import VideosPage from './videos/+page.svelte';
import { useFramesFilter } from '$lib/hooks/useFramesFilter/useFramesFilter';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';

vi.mock('$app/state', () => ({ page: { params: { collection_id: 'collection' } } }));
vi.mock('$app/stores', () => ({
    page: writable({ params: { collection_id: 'collection' } })
}));

const data = writable<{ sample_id: string; file_name: string }[]>([]);
const selected = writable(new Set<string>());
const totalCount = writable(100);
const setfilteredSampleCount = vi.fn();
const queryResult = {
    data,
    totalCount,
    loadMore: vi.fn(),
    query: { isSuccess: true, isPending: false, isError: false, hasNextPage: false }
};
vi.mock('$lib/hooks/useVideos/useVideos.svelte', () => ({
    useVideos: () => queryResult
}));
vi.mock('$lib/hooks/useFrames/useFrames.svelte', () => ({
    useFrames: () => queryResult
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        sampleSize: writable({ width: 6 }),
        textEmbedding: writable(null),
        setfilteredSampleCount,
        getSelectedSampleIds: () => selected,
        toggleSampleSelection: (id: string) =>
            selected.update((ids) => {
                const next = new Set(ids);
                if (next.has(id)) next.delete(id);
                else next.add(id);
                return next;
            })
    })
}));
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', async (importOriginal) => ({
    ...(await importOriginal<object>()),
    useMetadataFilters: () => ({
        metadataValues: writable({}),
        categoricalMetadataValues: writable({})
    })
}));
vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({ tagsSelected: writable(new Set<string>()) })
}));
vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', () => ({
    useSelectedAnnotationsFilter: () => ({ selectedAnnotationFilterIdsArray: writable([]) })
}));
vi.mock('$lib/hooks/useVideosBounds/useVideosBounds', () => ({
    useVideoBounds: () => ({ videoBoundsValues: writable(null) })
}));
vi.mock('$lib/hooks/useVideoFramesBounds/useVideoFramesBounds', () => ({
    useVideoFramesBounds: () => ({ videoFramesBoundsValues: writable(null) })
}));
vi.mock('$lib/hooks', async () => ({
    ...(await import('$lib/hooks/useGlobalStorage')),
    ...(await import('$lib/hooks/useFrames/useFrames.svelte')),
    ...(await import('$lib/hooks/useTags/useTags')),
    ...(await import('$lib/hooks/useVideoFramesBounds/useVideoFramesBounds')),
    ...(await import('$lib/hooks/useMetadataFilters/useMetadataFilters')),
    ...(await import('$lib/hooks/useFramesFilter/useFramesFilter'))
}));
// Media decoding and authentication belong to the item components, not these page tests.
vi.mock('$lib/components', () => ({ VideoFrameItem: () => {} }));
vi.mock('$lib/components/VideoItem/VideoItem.svelte', () => ({ default: () => {} }));
vi.mock('$lib/hooks/useAuth/useAuth', () => ({ default: () => ({ user: null }) }));

describe.each([
    {
        name: 'frames',
        useFilter: useFramesFilter,
        Page: FramesPage,
        gridId: 'video-frames-grid',
        empty: 'No video frames found'
    },
    {
        name: 'videos',
        useFilter: useVideoFilters,
        Page: VideosPage,
        gridId: 'video-grid',
        empty: 'No videos found'
    }
])('$name page', ({ Page, gridId, empty, useFilter }) => {
    beforeEach(() => {
        data.set([]);
        selected.set(new Set());
        sessionStorage.clear();
        vi.clearAllMocks();
        useFramesFilter().updateFilterParams(null);
        useVideoFilters().filterParams.set(null);
        // jsdom has no layout; six 134px columns and a 600px viewport give five visible rows.
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);
        Element.prototype.scrollTo = vi.fn();
        vi.stubGlobal(
            'ResizeObserver',
            class {
                constructor(private callback: ResizeObserverCallback) {}
                observe(target: Element) {
                    this.callback(
                        [
                            {
                                target,
                                contentRect: { width: 800, height: 600 } as DOMRectReadOnly,
                                borderBoxSize: [],
                                contentBoxSize: [],
                                devicePixelContentBoxSize: []
                            }
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

    it('shows an empty collection message', () => {
        totalCount.set(0);
        render(Page);
        expect(screen.getByText(empty)).toBeInTheDocument();
        expect(setfilteredSampleCount).toHaveBeenCalledWith(0);
    });

    it('limits off-screen items and supports selection and scrolling', async () => {
        data.set(
            Array.from({ length: 100 }, (_, i) => ({
                sample_id: `sample-${i}`,
                file_name: `sample-${i}`
            }))
        );
        totalCount.set(100);
        const { filterParams, updateFilterParams } = useFilter();
        updateFilterParams({ collection_id: 'collection', filters: { sample_ids: ['sample-0'] } });
        render(Page);
        expect(get(filterParams)?.filters?.sample_ids).toEqual(['sample-0']);
        // Five visible rows plus two overscan rows, rather than all 100 items.
        await waitFor(() => expect(screen.getAllByRole('button')).toHaveLength(42));
        expect(setfilteredSampleCount).toHaveBeenCalledWith(100);
        await fireEvent.click(screen.getByRole('button', { name: 'View sample: sample-0' }));
        await fireEvent.click(screen.getByRole('button', { name: 'View sample: sample-2' }), {
            shiftKey: true
        });
        expect(screen.getAllByRole('checkbox', { checked: true })).toHaveLength(3);
        await fireEvent.scroll(screen.getByTestId(gridId), { target: { scrollTop: 300 } });
        expect(JSON.parse(sessionStorage.getItem('frames_scroll') ?? '{}').position).toBe(300);
    });
});
