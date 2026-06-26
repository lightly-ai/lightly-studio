import { get, type Writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// `ids` controls the IDs the stubbed fetch modules return. `gate`, when set, holds the image fetch
// in flight until it resolves — letting a test interleave a store mutation with an unfinished fetch.
const fetchState = vi.hoisted(() => ({
    ids: ['s1', 's2', 's3'] as string[],
    gate: null as Promise<void> | null
}));

vi.mock('svelte-sonner', () => ({
    toast: { loading: vi.fn(), success: vi.fn(), error: vi.fn() }
}));
vi.mock('./fetchSampleIdsForImages', () => ({
    fetchSampleIdsForImages: vi.fn(async () => {
        if (fetchState.gate) await fetchState.gate;
        return fetchState.ids;
    })
}));
vi.mock('./fetchSampleIdsForVideos', () => ({
    fetchSampleIdsForVideos: vi.fn(() => Promise.resolve(fetchState.ids))
}));
vi.mock('./fetchSampleIdsForVideoFrames', () => ({
    fetchSampleIdsForVideoFrames: vi.fn(() => Promise.resolve(fetchState.ids))
}));
vi.mock('./fetchSampleIdsForAnnotations', () => ({
    fetchSampleIdsForAnnotations: vi.fn(() => Promise.resolve(fetchState.ids))
}));

// Filter hooks are mocked with writable stores the tests drive directly; `buildVideoFilter` /
// `getFrameFilter` are identity so the store value is the filter.
vi.mock('$lib/hooks/useImageFilters/useImageFilters', async () => {
    const { writable } = await import('svelte/store');
    const imageFilter = writable<unknown>(null);
    const filterParams = writable<{ mode?: string }>({ mode: 'normal' });
    return { useImageFilters: () => ({ imageFilter, filterParams }) };
});
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', async () => {
    const { writable } = await import('svelte/store');
    const filterParams = writable<unknown>(null);
    return {
        useVideoFilters: () => ({ filterParams }),
        buildVideoFilter: (params: unknown) => params
    };
});
vi.mock('$lib/hooks/useFramesFilter/useFramesFilter', async () => {
    const { writable } = await import('svelte/store');
    const filterParams = writable<unknown>(null);
    return { useFramesFilter: () => ({ filterParams }) };
});
vi.mock('$lib/hooks/useFramesFilter/frameFilter', () => ({
    getFrameFilter: (params: unknown) => params
}));
vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', async () => {
    const { writable } = await import('svelte/store');
    const annotationFilter = writable<unknown>(undefined);
    return { useSelectedAnnotationsFilter: () => ({ annotationFilter }) };
});

import { useSelectAll } from './useSelectAll';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useImageFilters } from '$lib/hooks/useImageFilters/useImageFilters';
import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import { useFramesFilter } from '$lib/hooks/useFramesFilter/useFramesFilter';
import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';

const collectionId = 'collection-1';

// The mocks are writable, but the real (read-only) signatures hide `.set`; these casts reach it.
const imageFilterStore = () => useImageFilters().imageFilter as unknown as Writable<unknown>;
const imageParamsStore = () =>
    useImageFilters().filterParams as unknown as Writable<{ mode: string }>;
const videoParamsStore = () => useVideoFilters().filterParams as unknown as Writable<unknown>;
const frameParamsStore = () => useFramesFilter().filterParams as unknown as Writable<unknown>;
const annotationFilterStore = () =>
    useSelectedAnnotationsFilter().annotationFilter as unknown as Writable<unknown>;

describe('useSelectAll', () => {
    let storage: ReturnType<typeof useGlobalStorage>;
    const sampleSnapshot = () => get(storage.getSelectAllSnapshot(collectionId));
    const annotationSnapshot = () => get(storage.getSelectAllAnnotationSnapshot(collectionId));

    beforeEach(() => {
        storage = useGlobalStorage();
        // Reset the module singletons.
        storage.clearSelectedSamples(collectionId);
        storage.clearSelectedSampleAnnotationCrops(collectionId);

        fetchState.ids = ['s1', 's2', 's3'];
        fetchState.gate = null;
        imageParamsStore().set({ mode: 'normal' });
        imageFilterStore().set(null);
        videoParamsStore().set(null);
        frameParamsStore().set(null);
        annotationFilterStore().set(undefined);
    });

    it('records the captured filter and size into the sample store (images)', async () => {
        const activeFilter = {
            filter_type: 'image',
            sample_filter: { tag_ids: ['t1'] }
        };
        imageFilterStore().set(activeFilter);

        await useSelectAll(collectionId, 'images').handleSelectAll();

        expect(sampleSnapshot()).toEqual({ filter: activeFilter, size: 3 });
        expect(annotationSnapshot()).toBeNull();
    });

    it('normalizes a no-filter select-all to a conditionless typed filter (videos)', async () => {
        videoParamsStore().set(null); // builder yields null → must normalize, not store null

        await useSelectAll(collectionId, 'videos').handleSelectAll();

        expect(sampleSnapshot()).toEqual({ filter: { filter_type: 'video' }, size: 3 });
    });

    it('captures the video_frame filter with its discriminator', async () => {
        const frameFilter = { filter_type: 'video_frame', frame_number: {} };
        frameParamsStore().set(frameFilter);

        await useSelectAll(collectionId, 'video_frames').handleSelectAll();

        expect(sampleSnapshot()).toEqual({ filter: frameFilter, size: 3 });
    });

    it('records the snapshot into the annotation store for the annotations grid', async () => {
        const annotationFilter = {
            filter_type: 'annotations',
            annotation_label_ids: ['a1']
        };
        annotationFilterStore().set(annotationFilter);

        await useSelectAll(collectionId, 'annotations').handleSelectAll();

        expect(annotationSnapshot()).toEqual({ filter: annotationFilter, size: 3 });
        expect(sampleSnapshot()).toBeNull();
    });

    it('normalizes an empty annotations select-all to a conditionless typed filter', async () => {
        annotationFilterStore().set(undefined);

        await useSelectAll(collectionId, 'annotations').handleSelectAll();

        expect(annotationSnapshot()).toEqual({
            filter: { filter_type: 'annotations' },
            size: 3
        });
    });

    it('snapshots the filter captured at call time, not one changed mid-fetch', async () => {
        const originalFilter = {
            filter_type: 'image',
            sample_filter: { tag_ids: ['original'] }
        };
        imageFilterStore().set(originalFilter);

        // Hold the fetch open so the store can be mutated while it is still in flight.
        let releaseFetch!: () => void;
        fetchState.gate = new Promise<void>((resolve) => {
            releaseFetch = resolve;
        });

        const pending = useSelectAll(collectionId, 'images').handleSelectAll();

        // The user switches to a different filter before the fetch completes.
        imageFilterStore().set({ filter_type: 'image', sample_filter: { tag_ids: ['changed'] } });

        releaseFetch();
        await pending;

        // `resolveGrid` captured the filter synchronously, so the snapshot reflects the original
        // filter — not the value set mid-fetch.
        expect(sampleSnapshot()).toEqual({ filter: originalFilter, size: 3 });
    });

    it('writes no snapshot for classifier-mode images, clearing any prior one', async () => {
        // Normal-mode select-all writes a snapshot...
        imageFilterStore().set({ filter_type: 'image' });
        await useSelectAll(collectionId, 'images').handleSelectAll();
        expect(sampleSnapshot()).not.toBeNull();

        // ...a following classifier-mode select-all yields a null filter and must clear the prior
        // snapshot rather than leave it stale (`setAllSelectedSampleIds` doesn't invalidate it).
        imageParamsStore().set({ mode: 'classifier' });
        imageFilterStore().set(null);
        await useSelectAll(collectionId, 'images').handleSelectAll();

        expect(sampleSnapshot()).toBeNull();
    });
});
