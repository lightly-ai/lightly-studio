import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { get, type Readable } from 'svelte/store';
import {
    useMetadataFieldList,
    type UseMetadataFieldListParams
} from './useMetadataFieldList.svelte';
import { isFieldActive } from './metadataFields';
import { useDimensions, useGlobalStorage, useVideoBounds, useVideoFramesBounds } from '$lib/hooks';
import { getMetadataInfo } from '$lib/api/lightly_studio_local';

const trackEvent = vi.fn();
vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    usePostHog: () => ({ trackEvent })
}));
vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/api/lightly_studio_local')>()),
    getMetadataInfo: vi.fn(() => Promise.resolve({ data: undefined })),
    getFieldsBounds: vi.fn(() => Promise.resolve({ data: undefined })),
    getVideoFramesFieldsBounds: vi.fn(() => Promise.resolve({ data: undefined }))
}));
vi.mock('$lib/services/loadDimensionBounds', () => ({
    loadDimensionBounds: vi.fn(() => Promise.resolve({ data: undefined }))
}));

const COLLECTION_ID = 'collection-1';
const dimensionBounds = { min_width: 10, max_width: 100, min_height: 20, max_height: 200 };

let cleanup: (() => void) | undefined;

const setup = (overrides: Partial<UseMetadataFieldListParams> = {}) => {
    let list!: ReturnType<typeof useMetadataFieldList>;
    cleanup = $effect.root(() => {
        list = useMetadataFieldList({
            getCollectionId: () => COLLECTION_ID,
            getShowImageDimensions: () => true,
            getIsVideos: () => false,
            getIsVideoFrames: () => false,
            getCategoricalKeys: () => ['split'],
            ...overrides
        });
    });
    flushSync();
    return list;
};

const ids = (list: ReturnType<typeof useMetadataFieldList>) => list.fields.map((f) => f.id);

// Counts the writes to a store after subscribing, without the first call on subscribe.
const countWrites = (store: Readable<unknown>) => {
    let writes = -1;
    const unsubscribe = store.subscribe(() => writes++);
    return { count: () => writes, unsubscribe };
};

beforeEach(() => {
    trackEvent.mockClear();
    const storage = useGlobalStorage();
    storage.updateMetadataBounds({ score: { min: 0, max: 10 } });
    storage.updateMetadataValues({ score: { min: 0, max: 10 } });
    storage.updateCategoricalMetadataValues({});
    useDimensions().updateDimensionsBounds(dimensionBounds);
    useDimensions().updateDimensionsValues(dimensionBounds);
    const videoBounds = {
        width: { min: 1, max: 5 },
        height: { min: 2, max: 6 },
        duration_s: { min: 0, max: 9 },
        fps: { min: 30, max: 30 }
    };
    useVideoBounds().updateVideoBounds(videoBounds);
    useVideoBounds().updateVideoBoundsValues(videoBounds);
    const frameBounds = { frame_number: { min: 0, max: 50 } };
    useVideoFramesBounds().updateVideoFramesBounds(frameBounds);
    useVideoFramesBounds().updateVideoFramesBoundsValues(frameBounds);
});

afterEach(() => cleanup?.());

describe('useMetadataFieldList', () => {
    it('lists dimensions, numeric and categorical fields in default order', () => {
        const list = setup();
        expect(ids(list)).toEqual([
            'dimension:width',
            'dimension:height',
            'numeric:score',
            'categorical:split'
        ]);
    });

    it('lists no width and height when image dimensions are hidden', () => {
        const list = setup({ getShowImageDimensions: () => false });
        expect(ids(list)).toEqual(['numeric:score', 'categorical:split']);
    });

    it('lists video fields and omits fps with equal bounds', () => {
        const list = setup({
            getShowImageDimensions: () => false,
            getIsVideos: () => true,
            getCategoricalKeys: () => []
        });
        expect(ids(list)).toEqual([
            'video:width',
            'video:height',
            'video:duration_s',
            'numeric:score'
        ]);
    });

    it('lists fps when its bounds differ and the frame number for video frames', () => {
        const videoBounds = {
            width: { min: 1, max: 5 },
            height: { min: 2, max: 6 },
            duration_s: { min: 0, max: 9 },
            fps: { min: 24, max: 30 }
        };
        useVideoBounds().updateVideoBounds(videoBounds);
        useVideoBounds().updateVideoBoundsValues(videoBounds);
        const list = setup({
            getShowImageDimensions: () => false,
            getIsVideos: () => true,
            getIsVideoFrames: () => true,
            getCategoricalKeys: () => []
        });
        expect(ids(list)).toEqual([
            'video:width',
            'video:height',
            'video:fps',
            'video:duration_s',
            'frame:frame_number',
            'numeric:score'
        ]);
    });

    it('commitRange writes only the store of that field', () => {
        const onRangeCommitted = vi.fn();
        const storage = useGlobalStorage();
        storage.updateMetadataBounds({ width: { min: 0, max: 10 } });
        storage.updateMetadataValues({ width: { min: 0, max: 10 } });
        const list = setup({ onRangeCommitted, getCategoricalKeys: () => [] });

        list.commitRange('numeric:width', { min: 2, max: 3 });

        expect(get(storage.metadataValues).width).toEqual({ min: 2, max: 3 });
        expect(get(useDimensions().dimensionsValues)).toEqual(dimensionBounds);
        expect(onRangeCommitted).toHaveBeenCalledWith('width', 2, 3);
    });

    it('commitRange on a dimension keeps the other dimension', () => {
        const list = setup();
        list.commitRange('dimension:height', { min: 50, max: 60 });
        expect(get(useDimensions().dimensionsValues)).toEqual({
            ...dimensionBounds,
            min_height: 50,
            max_height: 60
        });
    });

    it('reset sets a range back to its bounds and tracks disabled', () => {
        const onRangeCommitted = vi.fn();
        const storage = useGlobalStorage();
        const list = setup({ onRangeCommitted });
        list.commitRange('numeric:score', { min: 2, max: 3 });
        onRangeCommitted.mockClear();

        list.reset('numeric:score');

        expect(get(storage.metadataValues).score).toEqual({ min: 0, max: 10 });
        expect(trackEvent).toHaveBeenCalledWith('metadata_filter_changed', {
            collection_id: COLLECTION_ID,
            field_name: 'score',
            source: 'numeric',
            action: 'disabled'
        });
        expect(onRangeCommitted).not.toHaveBeenCalled();
    });

    it('reset clears categorical values and tracks disabled', () => {
        const storage = useGlobalStorage();
        storage.updateCategoricalMetadataValues({ split: ['train'], other: ['a'] });
        const list = setup({ getCategoricalKeys: () => ['split', 'other'] });

        list.reset('categorical:split');

        expect(get(storage.categoricalMetadataValues)).toEqual({ other: ['a'] });
        expect(trackEvent).toHaveBeenCalledWith('metadata_filter_changed', {
            collection_id: COLLECTION_ID,
            field_name: 'split',
            source: 'categorical',
            action: 'disabled'
        });
    });

    it('resetAll resets every field and tracks each active one once', () => {
        const storage = useGlobalStorage();
        storage.updateCategoricalMetadataValues({ split: ['train'] });
        const list = setup();
        list.commitRange('numeric:score', { min: 2, max: 3 });
        list.commitRange('dimension:width', { min: 20, max: 30 });
        list.commitRange('dimension:height', { min: 50, max: 60 });
        trackEvent.mockClear();
        const writes = [
            countWrites(useDimensions().dimensionsValues),
            countWrites(storage.metadataValues),
            countWrites(storage.categoricalMetadataValues)
        ];

        list.resetAll();

        expect(writes.map((write) => write.count())).toEqual([1, 1, 1]);
        for (const write of writes) write.unsubscribe();

        expect(list.fields.some(isFieldActive)).toBe(false);
        expect(trackEvent).toHaveBeenCalledTimes(4);
        const names = trackEvent.mock.calls.map(([, props]) => props.field_name).sort();
        expect(names).toEqual(['height', 'score', 'split', 'width']);
        expect(trackEvent.mock.calls.map(([, props]) => props.source).sort()).toEqual([
            'categorical',
            'dimension',
            'dimension',
            'numeric'
        ]);
    });

    it('reset sets a dimension back to its bounds', () => {
        const list = setup();
        list.commitRange('dimension:width', { min: 20, max: 30 });

        list.reset('dimension:width');

        expect(get(useDimensions().dimensionsValues)).toEqual(dimensionBounds);
    });

    it('reset does nothing for a field that is not active', () => {
        const list = setup();
        const writes = countWrites(useGlobalStorage().metadataValues);

        list.reset('numeric:score');

        expect(writes.count()).toBe(0);
        expect(trackEvent).not.toHaveBeenCalled();
        writes.unsubscribe();
    });

    it('commitRange and reset ignore unknown ids and categorical fields', () => {
        const onRangeCommitted = vi.fn();
        const list = setup({ onRangeCommitted });
        const before = list.fields;

        list.commitRange('numeric:missing', { min: 1, max: 2 });
        list.commitRange('categorical:split', { min: 1, max: 2 });
        list.reset('numeric:missing');

        expect(list.fields).toEqual(before);
        expect(onRangeCommitted).not.toHaveBeenCalled();
        expect(trackEvent).not.toHaveBeenCalled();
    });

    it('loads the numeric fields of the collection', async () => {
        vi.mocked(getMetadataInfo).mockResolvedValueOnce({
            data: [
                { name: 'confidence', type: 'float', min: 0, max: 1 },
                { name: 'count', type: 'integer', min: 0, max: 5 },
                { name: 'split', type: 'string' }
            ]
        } as Awaited<ReturnType<typeof getMetadataInfo>>);
        const collectionId = '7f6a8c1e-3b4d-4e5f-9a0b-1c2d3e4f5a6b';
        const list = setup({ getCollectionId: () => collectionId, getCategoricalKeys: () => [] });

        await vi.waitFor(() =>
            expect(ids(list)).toEqual([
                'dimension:width',
                'dimension:height',
                'numeric:confidence',
                'numeric:count'
            ])
        );
        expect(getMetadataInfo).toHaveBeenCalledWith({ path: { collection_id: collectionId } });
    });

    it('a categorical key named like an object property is not active', () => {
        const list = setup({ getCategoricalKeys: () => ['constructor'] });
        expect(list.fields.find((f) => f.id === 'categorical:constructor')).toMatchObject({
            selected: []
        });
    });

    it('a store change from outside makes the field active', () => {
        const list = setup();
        expect(list.fields.find((f) => f.id === 'categorical:split')).toMatchObject({
            selected: []
        });

        useGlobalStorage().updateCategoricalMetadataValues({ split: ['train'] });

        const split = list.fields.find((f) => f.id === 'categorical:split');
        expect(split && isFieldActive(split)).toBe(true);
    });
});
