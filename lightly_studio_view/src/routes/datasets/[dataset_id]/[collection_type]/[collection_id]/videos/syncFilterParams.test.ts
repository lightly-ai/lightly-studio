import { describe, expect, it } from 'vitest';
import { isEqual } from 'lodash-es';
import { buildVideoFilter } from '$lib/hooks';
import { mergeExternalFilters, paramsWithoutExternalFilters } from './syncFilterParams';

const embeddingRegion = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const baseParams = { collection_id: 'col-1', filters: { tag_ids: ['tag-1'] } };
const selectedParams = {
    ...baseParams,
    filters: { ...baseParams.filters, sample_ids: ['sample-1'], embedding_region: embeddingRegion }
};

describe('video filter synchronization', () => {
    it('ignores external selection changes when comparing filter controls', () => {
        expect(
            isEqual(
                paramsWithoutExternalFilters(baseParams),
                paramsWithoutExternalFilters(selectedParams)
            )
        ).toBe(true);
        const changedParams = { ...baseParams, filters: { tag_ids: ['tag-2'] } };
        expect(
            isEqual(
                paramsWithoutExternalFilters(changedParams),
                paramsWithoutExternalFilters(selectedParams)
            )
        ).toBe(false);
    });

    it('preserves both selections when filter controls change and forwards them to the query', () => {
        const changedParams = {
            ...baseParams,
            filters: { tag_ids: ['tag-2'], annotation_frames_label_ids: ['label-1'] },
            video_bounds: {
                width: { min: 100, max: 1920 },
                height: { min: 100, max: 1080 },
                fps: { min: 24, max: 60 },
                duration_s: { min: 10, max: 60 }
            }
        };
        const result = mergeExternalFilters(changedParams, selectedParams);

        expect(buildVideoFilter(result)).toEqual({
            filter_type: 'video',
            ...changedParams.video_bounds,
            frame_annotation_filter: {
                filter_type: 'annotations',
                annotation_label_ids: ['label-1']
            },
            sample_filter: {
                tag_ids: ['tag-2'],
                sample_ids: ['sample-1'],
                embedding_region: embeddingRegion
            }
        });
    });

    it('forwards a region without explicit sample IDs and removes it when cleared', () => {
        const base = { collection_id: 'col-1' };
        const current = { ...base, filters: { embedding_region: embeddingRegion } };

        expect(buildVideoFilter(mergeExternalFilters(base, current))).toEqual({
            filter_type: 'video',
            sample_filter: { embedding_region: embeddingRegion }
        });
        expect(
            buildVideoFilter(
                mergeExternalFilters(base, {
                    ...current,
                    filters: { embedding_region: undefined }
                })
            )
        ).toEqual({ filter_type: 'video' });
    });

    it('preserves explicit sample IDs when the region is cleared', () => {
        const current = {
            ...selectedParams,
            filters: { ...selectedParams.filters, embedding_region: undefined }
        };

        expect(buildVideoFilter(mergeExternalFilters(baseParams, current))?.sample_filter).toEqual({
            tag_ids: ['tag-1'],
            sample_ids: ['sample-1']
        });
    });

    it.each([null, { ...selectedParams, collection_id: 'col-2' }])(
        'does not carry selections from uninitialized filters or another collection (%s)',
        (current) => {
            expect(mergeExternalFilters(baseParams, current)).toEqual(baseParams);
        }
    );
});
