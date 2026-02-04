import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useVideoFilters } from './useVideoFilters';
import { waitFor } from '@testing-library/svelte';

vi.mock('../useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [])
}));

describe('useVideoFilters', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        const { updateFilterParams } = useVideoFilters();
        updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);
    });

    describe('updateFilterParams and videoFilter derivation', () => {
        it('returns null videoFilter when collection_id is missing', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: ''
            });

            expect(get(videoFilter)).toBeNull();
        });

        it('returns null videoFilter when filterParams is null', () => {
            const { videoFilter } = useVideoFilters();
            const { updateFilterParams } = useVideoFilters();
            updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);

            expect(get(videoFilter)).toBeNull();
        });

        it('derives videoFilter with sample_filter when collection_id is set', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1'
            });

            expect(get(videoFilter)).toEqual({
                sample_filter: { collection_id: 'coll-1' }
            });
        });

        it('includes video_bounds (width, height, fps, duration_s) in videoFilter', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                video_bounds: {
                    width: { min: 100, max: 1920 },
                    height: { min: 100, max: 1080 },
                    fps: { min: 24, max: 60 },
                    duration_s: { min: 0, max: 120 }
                }
            });

            expect(get(videoFilter)).toMatchObject({
                width: { min: 100, max: 1920 },
                height: { min: 100, max: 1080 },
                fps: { min: 24, max: 60 },
                duration_s: { min: 0, max: 120 }
            });
        });

        it('includes sample_ids in sample_filter when provided', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { sample_ids: ['id-1', 'id-2'] }
            });

            expect(get(videoFilter)).toMatchObject({
                sample_filter: {
                    collection_id: 'coll-1',
                    sample_ids: ['id-1', 'id-2']
                }
            });
        });

        it('includes annotation_frames_label_ids when provided', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { annotation_frames_label_ids: ['label-1'] }
            });

            expect(get(videoFilter)).toMatchObject({
                annotation_frames_label_ids: ['label-1']
            });
        });

        it('includes tag_ids in sample_filter when provided', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { tag_ids: ['tag-1'] }
            });

            expect(get(videoFilter)).toMatchObject({
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

            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: {
                    metadata_values: { temp: { min: 10, max: 100 } }
                }
            });

            expect(get(videoFilter)?.sample_filter?.metadata_filters).toEqual([
                { key: 'temp', value: 10, op: '>=' }
            ]);
        });
    });

    describe('updateSampleIds', () => {
        it('updates only sample_ids and preserves other params', async () => {
            const { filterParams, videoFilter, updateFilterParams, updateSampleIds } =
                useVideoFilters();

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

            expect(get(videoFilter)?.sample_filter).toMatchObject({
                collection_id: 'coll-1',
                sample_ids: ['sample-a', 'sample-b'],
                tag_ids: ['tag-1']
            });
        });

        it('clears sample_ids when given empty array', async () => {
            const { filterParams, updateFilterParams, updateSampleIds } = useVideoFilters();

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
            const { updateFilterParams, updateSampleIds } = useVideoFilters();
            updateFilterParams(null as unknown as Parameters<typeof updateFilterParams>[0]);

            expect(() => updateSampleIds(['id-1'])).not.toThrow();
        });

        it('does nothing when collection_id is missing', () => {
            const { updateFilterParams, updateSampleIds } = useVideoFilters();
            updateFilterParams({
                collection_id: '',
                filters: { sample_ids: ['existing'] }
            });

            updateSampleIds(['new-id']);

            const { filterParams } = useVideoFilters();
            expect(get(filterParams)?.filters?.sample_ids).toEqual(['existing']);
        });
    });
});
