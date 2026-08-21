import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';
import { resolveEffectiveColorBySource } from '$lib/utils';

interface GetSampleClassificationPillsParams {
    annotations: AnnotationView[];
    /** Whether annotations from a given source should be shown. */
    isSourceVisible: (sourceId: string) => boolean;
    /** Whether more than one source is visible, which switches pill colors to per-source. */
    multipleSourcesVisible: boolean;
    collectionIdToName: Record<string, string>;
    enforceColoringByClass: boolean;
}

interface CreateSampleClassificationPillParams {
    annotation: AnnotationView;
    showSourceColors: boolean;
    collectionIdToName: Record<string, string>;
}

const MAX_DISPLAY_LABEL_LENGTH = 11;

function truncateDisplayLabel(label: string): string {
    if (label.length <= MAX_DISPLAY_LABEL_LENGTH) {
        return label;
    }

    return `${label.slice(0, MAX_DISPLAY_LABEL_LENGTH - 4)}....`;
}

export interface SampleClassificationPill {
    id: string;
    label: string;
    displayLabel: string;
    colorKey: string;
    title: string;
}

function isClassificationAnnotation(annotation: AnnotationView): boolean {
    return annotation.annotation_type === AnnotationType.CLASSIFICATION;
}

function getSourceName(
    annotationCollectionId: string,
    collectionIdToName: Record<string, string>
): string {
    return collectionIdToName[annotationCollectionId] ?? `Collection ${annotationCollectionId}`;
}

function createSampleClassificationPill({
    annotation,
    showSourceColors,
    collectionIdToName
}: CreateSampleClassificationPillParams): SampleClassificationPill {
    const label = annotation.annotation_label.annotation_label_name;
    const sourceName = getSourceName(annotation.annotation_collection_id, collectionIdToName);
    const colorKey = showSourceColors ? sourceName : label;
    const title = showSourceColors ? `${sourceName}: ${label}` : label;

    return {
        id: showSourceColors ? `${annotation.annotation_collection_id}:${label}` : label,
        label,
        displayLabel: truncateDisplayLabel(label),
        colorKey,
        title
    };
}

function dedupeAndSortPills(pills: SampleClassificationPill[]): SampleClassificationPill[] {
    return Array.from(new Map(pills.map((pill) => [pill.id, pill])).values()).sort((a, b) =>
        a.id.localeCompare(b.id)
    );
}

export function getSampleClassificationPills({
    annotations,
    isSourceVisible,
    multipleSourcesVisible,
    collectionIdToName,
    enforceColoringByClass
}: GetSampleClassificationPillsParams): SampleClassificationPill[] {
    const showSourceColors = resolveEffectiveColorBySource({
        multipleSourcesVisible,
        enforceColoringByClass
    });

    return dedupeAndSortPills(
        annotations
            .filter((annotation) => isSourceVisible(annotation.annotation_collection_id))
            .filter(isClassificationAnnotation)
            .map((annotation) =>
                createSampleClassificationPill({
                    annotation,
                    showSourceColors,
                    collectionIdToName
                })
            )
    );
}
