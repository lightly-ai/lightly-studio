import { buildImageFilter } from './buildImageFilter';

describe('buildImageFilter', () => {
    const baseArgs = {
        dimensionsValues: null,
        annotationFilter: undefined,
        metadataFilters: undefined
    } as const;

    test('returns undefined when no filters are provided', () => {
        const result = buildImageFilter(baseArgs);
        expect(result).toBeUndefined();
    });

    test('sets width and height when dimensions are provided', () => {
        const result = buildImageFilter({
            ...baseArgs,
            dimensionsValues: {
                min_width: 10,
                max_width: 20,
                min_height: 30,
                max_height: 40
            }
        });

        expect(result).toEqual({
            width: { min: 10, max: 20 },
            height: { min: 30, max: 40 }
        });
    });

    test('adds annotationFilter to sample_filter', () => {
        const result = buildImageFilter({
            ...baseArgs,
            annotationFilter: {
                annotation_label_ids: ['a', 'b']
            }
        });

        expect(result).toEqual({
            sample_filter: {
                annotations_filter: {
                    annotation_label_ids: ['a', 'b']
                }
            }
        });
    });

    test('adds metadataFilters to sample_filter', () => {
        const metadataFilters = [{ key: 'foo', operator: 'eq', value: 'bar' }] as never;

        const result = buildImageFilter({
            ...baseArgs,
            metadataFilters
        });

        expect(result).toEqual({
            sample_filter: {
                metadata_filters: metadataFilters
            }
        });
    });

    test('merges dimensions, annotationFilter and metadataFilters', () => {
        const metadataFilters = [{ key: 'foo', operator: 'eq', value: 'bar' }] as never;

        const result = buildImageFilter({
            dimensionsValues: {
                min_width: 1,
                max_width: 2,
                min_height: 3,
                max_height: 4
            },
            annotationFilter: {
                annotation_label_ids: ['x']
            },
            metadataFilters
        });

        expect(result).toEqual({
            width: { min: 1, max: 2 },
            height: { min: 3, max: 4 },
            sample_filter: {
                annotations_filter: {
                    annotation_label_ids: ['x']
                },
                metadata_filters: metadataFilters
            }
        });
    });
});
