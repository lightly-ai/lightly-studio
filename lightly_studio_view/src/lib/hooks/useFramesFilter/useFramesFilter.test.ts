import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { waitFor } from '@testing-library/svelte';
import { useFramesFilter } from './useFramesFilter';

describe('useFramesFilter', () => {
    beforeEach(() => {
        const { updateFilterParams } = useFramesFilter();
        updateFilterParams(null);
    });

    describe('frameFilter store', () => {
        it('returns null when collection_id is missing', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({ collection_id: '' });

            expect(get(frameFilter)).toBeNull();
        });

        it('derives minimal filter when collection_id is set', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({ collection_id: 'coll-1' });

            expect(get(frameFilter)).toEqual({
                sample_filter: { collection_id: 'coll-1' },
                frame_number: {}
            });
        });

        it('reflects frame_bounds and video_id', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                frame_bounds: { frame_number: { min: 5, max: 10 } },
                video_id: 'vid-9'
            });

            expect(get(frameFilter)).toMatchObject({
                video_id: 'vid-9',
                frame_number: { min: 5, max: 10 }
            });
        });
    });

    describe('updateFilterParams', () => {
        it('stores provided params', () => {
            const { filterParams, updateFilterParams } = useFramesFilter();
            const params = { collection_id: 'coll-store', filters: { sample_ids: ['a'] } };

            updateFilterParams(params);

            expect(get(filterParams)).toEqual(params);
        });

        it('clears params when null is provided', () => {
            const { filterParams, updateFilterParams } = useFramesFilter();

            updateFilterParams({ collection_id: 'coll-to-clear' });
            updateFilterParams(null);

            expect(get(filterParams)).toBeNull();
        });
    });

    describe('updateSampleIds', () => {
        it('updates only sample_ids and preserves other params', async () => {
            const { filterParams, frameFilter, updateFilterParams, updateSampleIds } =
                useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { tag_ids: ['tag-1'] }
            });

            updateSampleIds(['sample-a', 'sample-b']);

            await waitFor(() => {
                const params = get(filterParams);
                expect(params?.filters?.sample_ids).toEqual(['sample-a', 'sample-b']);
                expect(params?.filters?.tag_ids).toEqual(['tag-1']);
            });

            expect(get(frameFilter)?.sample_filter).toMatchObject({
                collection_id: 'coll-1',
                sample_ids: ['sample-a', 'sample-b'],
                tag_ids: ['tag-1']
            });
        });

        it('clears sample_ids when given empty array', async () => {
            const { filterParams, updateFilterParams, updateSampleIds } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { sample_ids: ['old-id'] }
            });

            updateSampleIds([]);

            await waitFor(() => {
                const params = get(filterParams);
                expect(params?.filters?.sample_ids).toBeUndefined();
            });
        });

        it('does nothing when filterParams is null', () => {
            const { updateFilterParams, updateSampleIds } = useFramesFilter();
            updateFilterParams(null);

            expect(() => updateSampleIds(['id-1'])).not.toThrow();
        });

        it('does nothing when collection_id is missing', () => {
            const { filterParams, updateFilterParams, updateSampleIds } = useFramesFilter();
            updateFilterParams({
                collection_id: '',
                filters: { sample_ids: ['existing'] }
            });

            updateSampleIds(['new-id']);

            expect(get(filterParams)?.filters?.sample_ids).toEqual(['existing']);
        });
    });
});
