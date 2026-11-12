import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import type { AnnotationsFilter, ImageFilter, SampleFilter } from '$lib/api/lightly_studio_local';
import { imageDimensionRanges, withFilterOverrides } from '$lib/utils';

interface ImageAnnotationCountsFilter extends ImageFilter {
    filter_type: 'image';
}

interface BuildImageAnnotationCountsFilterParams {
    imageFilter: ImageFilter | null | undefined;
    isAnnotations: boolean;
    dimensionsValues: DimensionBounds | null | undefined;
    annotationFilter: AnnotationsFilter | undefined;
    metadataFilters: SampleFilter['metadata_filters'] | undefined;
}

/**
 * Builds the image filter for class counts. Starts from the shared image filter so the plot
 * selection, tags, query and confusion cell carry over. Dimensions, annotation filter and
 * metadata filters come from the passed parts. The annotations route ignores the shared filter.
 */
export function buildImageAnnotationCountsFilter({
    imageFilter,
    isAnnotations,
    dimensionsValues,
    annotationFilter,
    metadataFilters
}: BuildImageAnnotationCountsFilterParams): ImageAnnotationCountsFilter | undefined {
    return withFilterOverrides('image', isAnnotations ? null : imageFilter, {
        ...imageDimensionRanges(dimensionsValues),
        sample_filter: {
            annotations_filter: annotationFilter,
            metadata_filters: metadataFilters
        }
    });
}
