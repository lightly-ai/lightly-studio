import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useVideoFilters } from './useVideoFilters';
import { waitFor } from '@testing-library/svelte';
import { SortDirection } from '$lib/api/lightly_studio_local';

const embeddingRegion = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};

vi.mock('$lib/hooks', () => ({
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
                filter_type: 'video'
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
                    sample_ids: ['id-1', 'id-2']
                }
            });
        });

        it('includes frame_annotation_filter when labels are provided', () => {
            const { videoFilter, updateFilterParams } = useVideoFilters();

            updateFilterParams({
                collection_id: 'coll-1',
                filters: { annotation_frames_label_ids: ['label-1'] }
            });

            expect(get(videoFilter)).toMatchObject({
                frame_annotation_filter: {
                    annotation_label_ids: ['label-1']
                }
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
                    tag_ids: ['tag-1']
                }
            });
        });

        it('includes metadata_filters in sample_filter when createMetadataFilters returns filters', async () => {
            const { createMetadataFilters } = await import('$lib/hooks');
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

    describe('updateEmbeddingRegion', () => {
        it('stores and clears geometry while preserving all other filters', () => {
            const { filterParams, videoFilter, updateFilterParams, updateEmbeddingRegion } =
                useVideoFilters();
            const params = {
                collection_id: 'coll-1',
                video_bounds: {
                    width: { min: 100, max: 1920 },
                    height: { min: 100, max: 1080 },
                    fps: { min: 24, max: 60 },
                    duration_s: { min: 10, max: 60 }
                },
                filters: {
                    tag_ids: ['tag-1'],
                    annotation_frames_label_ids: ['label-1'],
                    metadata_values: { temp: { min: 10, max: 100 } },
                    categorical_metadata_values: { weather: ['sunny'] }
                }
            };
            updateFilterParams(params);
            const originalFilter = get(videoFilter);

            updateEmbeddingRegion(embeddingRegion);

            expect(get(filterParams)).toEqual({
                ...params,
                filters: { ...params.filters, embedding_region: embeddingRegion }
            });
            expect(get(videoFilter)).toEqual({
                ...originalFilter,
                sample_filter: { tag_ids: ['tag-1'], embedding_region: embeddingRegion }
            });

            updateEmbeddingRegion(null);

            expect(get(filterParams)).toEqual({
                ...params,
                filters: { ...params.filters, embedding_region: undefined }
            });
            expect(get(videoFilter)).toEqual(originalFilter);
        });

        it('preserves explicit sample IDs when geometry is set and cleared', () => {
            const { videoFilter, updateFilterParams, updateEmbeddingRegion } = useVideoFilters();
            updateFilterParams({
                collection_id: 'coll-1',
                filters: { sample_ids: ['sample-1', 'sample-2'] }
            });

            updateEmbeddingRegion(embeddingRegion);

            expect(get(videoFilter)?.sample_filter).toEqual({
                sample_ids: ['sample-1', 'sample-2'],
                embedding_region: embeddingRegion
            });

            updateEmbeddingRegion(null);

            expect(get(videoFilter)?.sample_filter).toEqual({
                sample_ids: ['sample-1', 'sample-2']
            });
        });

        it('preserves generated metadata filters when geometry is set and cleared', async () => {
            const { createMetadataFilters } = await import('$lib/hooks');
            const metadataFilters = [
                { key: 'temp', value: 10, op: '>=' as const },
                { key: 'weather', value: ['sunny'], op: 'in' as const }
            ];
            vi.mocked(createMetadataFilters)
                .mockReturnValueOnce(metadataFilters)
                .mockReturnValueOnce(metadataFilters);
            const { videoFilter, updateFilterParams, updateEmbeddingRegion } = useVideoFilters();
            updateFilterParams({
                collection_id: 'coll-1',
                filters: {
                    metadata_values: { temp: { min: 10, max: 100 } },
                    categorical_metadata_values: { weather: ['sunny'] }
                }
            });

            updateEmbeddingRegion(embeddingRegion);

            expect(get(videoFilter)?.sample_filter).toEqual({
                metadata_filters: metadataFilters,
                embedding_region: embeddingRegion
            });

            updateEmbeddingRegion(null);

            expect(get(videoFilter)?.sample_filter).toEqual({ metadata_filters: metadataFilters });
        });

        it('combines geometry with explicit sample IDs and preserves it when IDs change', () => {
            const { videoFilter, updateFilterParams, updateSampleIds } = useVideoFilters();
            updateFilterParams({
                collection_id: 'coll-1',
                filters: { embedding_region: embeddingRegion, sample_ids: ['old-id'] }
            });

            expect(get(videoFilter)?.sample_filter).toEqual({
                embedding_region: embeddingRegion,
                sample_ids: ['old-id']
            });

            updateSampleIds(['new-id']);

            expect(get(videoFilter)?.sample_filter).toEqual({
                embedding_region: embeddingRegion,
                sample_ids: ['new-id']
            });

            updateSampleIds([]);

            expect(get(videoFilter)?.sample_filter).toEqual({
                embedding_region: embeddingRegion
            });
        });

        it('builds a geometry-only sample filter and removes it when cleared', () => {
            const { videoFilter, updateFilterParams, updateEmbeddingRegion } = useVideoFilters();
            updateFilterParams({ collection_id: 'coll-1' });

            updateEmbeddingRegion(embeddingRegion);

            expect(get(videoFilter)).toEqual({
                filter_type: 'video',
                sample_filter: { embedding_region: embeddingRegion }
            });

            updateEmbeddingRegion(null);

            expect(get(videoFilter)).toEqual({ filter_type: 'video' });
        });

        it.each([null, { collection_id: '' }])(
            'leaves uninitialized filters unchanged (%s)',
            (params) => {
                const { filterParams, updateFilterParams, updateEmbeddingRegion } =
                    useVideoFilters();
                updateFilterParams(params as Parameters<typeof updateFilterParams>[0]);

                updateEmbeddingRegion(embeddingRegion);

                expect(get(filterParams)).toEqual(params);
            }
        );
    });

    describe('videoSortBy and updateSortBy', () => {
        it('defaults to ascending file_path_abs', () => {
            const { videoSortBy } = useVideoFilters();

            expect(get(videoSortBy)).toEqual([
                {
                    source: 'video',
                    field_name: 'file_path_abs',
                    direction: SortDirection.ASC
                }
            ]);
        });

        it('replaces the sort with the provided expression', () => {
            const { videoSortBy, updateSortBy } = useVideoFilters();

            updateSortBy([
                { source: 'video', field_name: 'duration_s', direction: SortDirection.DESC }
            ]);

            expect(get(videoSortBy)).toEqual([
                { source: 'video', field_name: 'duration_s', direction: SortDirection.DESC }
            ]);
        });

        it('clears the sort when given null', () => {
            const { videoSortBy, updateSortBy } = useVideoFilters();

            updateSortBy(null);

            expect(get(videoSortBy)).toBeNull();
        });
    });
});
