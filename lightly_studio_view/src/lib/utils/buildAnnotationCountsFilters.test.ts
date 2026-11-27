import { buildVideoFrameAnnotationCountsFilter } from './buildAnnotationCountsFilters';

describe('buildAnnotationCountsFilters', () => {
    test('buildVideoFrameAnnotationCountsFilter builds sample_filter and merges bounds', () => {
        const result = buildVideoFrameAnnotationCountsFilter({
            metadataFilters: [{ key: 'foo', operator: 'eq', value: 'bar' }] as never,
            annotationFilter: { annotation_label_ids: ['a'] },
            videoFramesBoundsValues: { frame_indices: { min: 1, max: 10 } } as never
        });

        expect(result).toEqual({
            sample_filter: {
                metadata_filters: [{ key: 'foo', operator: 'eq', value: 'bar' }],
                annotations_filter: { annotation_label_ids: ['a'] }
            },
            frame_indices: { min: 1, max: 10 }
        });
    });

    test('buildVideoFrameAnnotationCountsFilter omits annotations_filter when undefined', () => {
        const result = buildVideoFrameAnnotationCountsFilter({
            metadataFilters: undefined,
            annotationFilter: undefined,
            videoFramesBoundsValues: null
        });

        expect(result).toEqual({
            sample_filter: {
                metadata_filters: undefined
            }
        });
    });
});
