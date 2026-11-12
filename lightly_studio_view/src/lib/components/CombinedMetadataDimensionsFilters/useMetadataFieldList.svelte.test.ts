import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { get } from 'svelte/store';
import {
    useMetadataFieldList,
    type UseMetadataFieldListParams
} from './useMetadataFieldList.svelte';
import { isFieldActive } from './metadataFields';
import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const trackEvent = vi.fn();
vi.mock('$lib/hooks', () => ({ usePostHog: () => ({ trackEvent }) }));
vi.mock('$lib/api/lightly_studio_local', () => ({
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
        trackEvent.mockClear();
        const writes = [
            vi.spyOn(useDimensions(), 'updateDimensionsValues'),
            vi.spyOn(storage, 'updateMetadataValues'),
            vi.spyOn(storage, 'updateCategoricalMetadataValues')
        ];

        list.resetAll();

        for (const write of writes) expect(write.mock.calls.length).toBeLessThanOrEqual(1);

        expect(list.fields.some(isFieldActive)).toBe(false);
        expect(trackEvent).toHaveBeenCalledTimes(3);
        const names = trackEvent.mock.calls.map(([, props]) => props.field_name).sort();
        expect(names).toEqual(['score', 'split', 'width']);
        expect(trackEvent.mock.calls.map(([, props]) => props.source).sort()).toEqual([
            'categorical',
            'dimension',
            'numeric'
        ]);
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
