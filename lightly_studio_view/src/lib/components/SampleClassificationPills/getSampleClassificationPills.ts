import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

interface GetSampleClassificationPillsParams {
    annotations: AnnotationView[];
    selectedCollectionIds: string[];
    collectionIdToName: Record<string, string>;
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

function isVisibleAnnotation(
    annotation: AnnotationView,
    selectedCollectionIds: string[]
): boolean {
    return (
        selectedCollectionIds.length === 0 ||
        selectedCollectionIds.includes(annotation.annotation_collection_id)
    );
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
    selectedCollectionIds,
    collectionIdToName
}: GetSampleClassificationPillsParams): SampleClassificationPill[] {
    const showSourceColors = selectedCollectionIds.length > 1;

    return dedupeAndSortPills(
        annotations
            .filter((annotation) => isVisibleAnnotation(annotation, selectedCollectionIds))
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
