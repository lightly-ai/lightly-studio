import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { buildImageFilter } from '$lib/utils/buildImageFilter';

/** The backend default source new annotations land in when no name is sent. */
export const DEFAULT_ANNOTATION_SOURCE_NAME = 'annotation';

interface SelectionClassCount {
    className: string;
    sampleCount: number;
}

/**
 * Pick the annotation source the new annotations are written to.
 *
 * Mirrors the annotation source pill: the remembered choice wins, then the conventional
 * default source, then the first existing source, then the default name.
 */
export function resolveAnnotationSource({
    lastSource,
    sourceNames
}: {
    lastSource: string | undefined;
    sourceNames: string[];
}): string {
    return (
        lastSource ??
        sourceNames.find((name) => name === DEFAULT_ANNOTATION_SOURCE_NAME) ??
        sourceNames[0] ??
        DEFAULT_ANNOTATION_SOURCE_NAME
    );
}

/**
 * Filter restricting the annotation counts to the selected samples and the target source.
 *
 * The annotation type is not part of the filter; the counts endpoint takes it separately.
 */
export function buildSelectionCountsFilter({
    sampleIds,
    annotationSourceId
}: {
    sampleIds: string[];
    annotationSourceId: string;
}): ImageFilter | undefined {
    return buildImageFilter({
        dimensionsValues: null,
        annotationFilter: { collection_ids: [annotationSourceId] },
        metadataFilters: undefined,
        sampleIds
    });
}

/**
 * Map the annotation counts response to the panel's per-class sample counts.
 *
 * `current_count` respects the request filter, so it is the count within the selection;
 * `total_count` deliberately ignores the filter and must not be used here.
 */
export function toSelectionClassCounts(
    rows: Array<{ [key: string]: string | number }> | undefined
): SelectionClassCount[] {
    return (rows ?? []).map((row) => ({
        className: String(row.label_name ?? ''),
        sampleCount: Number(row.current_count ?? 0)
    }));
}

/** Map annotation labels to the picker's options; the name is what gets sent. */
export function toAnnotationClassOptions(
    labels: Array<{ annotation_label_id?: string; annotation_label_name: string }> | undefined
): Array<{ id: string; name: string }> {
    return (labels ?? []).map((label) => ({
        id: label.annotation_label_id ?? label.annotation_label_name,
        name: label.annotation_label_name
    }));
}

/** Report what an apply changed, naming the images it left untouched. */
export function formatApplyResult({
    createdCount,
    skippedCount
}: {
    createdCount: number;
    skippedCount: number;
}): string {
    const totalCount = createdCount + skippedCount;
    if (createdCount === 0) {
        return `No images changed; all ${totalCount} already had this annotation class.`;
    }
    if (skippedCount === 0) {
        return `Added the annotation class to ${createdCount} ${createdCount === 1 ? 'image' : 'images'}.`;
    }
    return `Added to ${createdCount} of ${totalCount} images; ${skippedCount} already had this annotation class.`;
}
