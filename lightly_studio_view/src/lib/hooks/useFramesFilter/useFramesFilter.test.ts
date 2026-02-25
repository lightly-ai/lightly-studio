import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { waitFor } from '@testing-library/svelte';
import { useFramesFilter } from './useFramesFilter';

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useFramesFilter', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams } = useFramesFilter();
        updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);
    });

    describe('updateFilterParams and frameFilter', () => {
        it('returns null frameFilter when collection_id is missing', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: ''
            });

            expect(get(frameFilter)).toBeNull();
        });

        it('returns null frameFilter when filterParams is null', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();
            updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);

            expect(get(frameFilter)).toBeNull();
        });

        it('derives frameFilter with sample_filter when collection_id is set', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1'
            });

            expect(get(frameFilter)).toEqual({
                sample_filter: { collection_id: 'coll-1' },
                frame_number: {}
            });
        });

        it('includes frame_bounds (frame_number) in frameFilter', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                frame_bounds: {
                    frame_number: { min: 10, max: 100 }
                }
            });

            expect(get(frameFilter)).toMatchObject({
                frame_number: { min: 10, max: 100 }
            });
        });

        it('includes video_id when provided', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                video_id: 'video-1'
            });

            expect(get(frameFilter)).toMatchObject({
                video_id: 'video-1'
            });
        });

        it('includes sample_ids in sample_filter when provided', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { sample_ids: ['id-1', 'id-2'] }
            });

            expect(get(frameFilter)).toMatchObject({
                sample_filter: {
                    collection_id: 'coll-1',
                    sample_ids: ['id-1', 'id-2']
                }
            });
        });

        it('includes annotation_label_ids when provided', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { annotation_label_ids: ['label-1'] }
            });

            expect(get(frameFilter)).toMatchObject({
                sample_filter: {
                    annotation_label_ids: ['label-1']
                }
            });
        });

        it('includes tag_ids in sample_filter when provided', () => {
            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { tag_ids: ['tag-1'] }
            });

            expect(get(frameFilter)).toMatchObject({
                sample_filter: {
                    collection_id: 'coll-1',
                    tag_ids: ['tag-1']
                }
            });
        });

        it('includes metadata_filters in sample_filter when createMetadataFilters returns filters', async () => {
            const { createMetadataFilters } = await import(
                '../useMetadataFilters/useMetadataFilters'
            );
            vi.mocked(createMetadataFilters).mockReturnValueOnce([
                { key: 'temp', value: 10, op: '>=' as const }
            ]);

            const { frameFilter, updateFilterParams } = useFramesFilter();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: {
                    metadata_values: { temp: { min: 10, max: 100 } }
                }
            });

            expect(get(frameFilter)?.sample_filter?.metadata_filters).toEqual([
                { key: 'temp', value: 10, op: '>=' }
            ]);
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
            updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);

            expect(() => updateSampleIds(['id-1'])).not.toThrow();
        });

        it('does nothing when collection_id is missing', () => {
            const { updateFilterParams, updateSampleIds } = useFramesFilter();
            updateFilterParams({
                collection_id: '',
                filters: { sample_ids: ['existing'] }
            });

            updateSampleIds(['new-id']);

            const { filterParams } = useFramesFilter();
            expect(get(filterParams)?.filters?.sample_ids).toEqual(['existing']);
        });
    });
});
