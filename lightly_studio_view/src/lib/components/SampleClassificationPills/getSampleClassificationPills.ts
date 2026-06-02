import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

interface GetSampleClassificationPillsParams {
    annotations: AnnotationView[];
    selectedCollectionIds: string[];
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

export function getSampleClassificationPills({
    annotations,
    selectedCollectionIds,
    collectionIdToName
}: GetSampleClassificationPillsParams): SampleClassificationPill[] {
    const showSourceColors = selectedCollectionIds.length > 1;
    const visibleAnnotations = annotations.filter(
        (annotation) =>
            selectedCollectionIds.length === 0 ||
            selectedCollectionIds.includes(annotation.annotation_collection_id)
    );

    const pills = visibleAnnotations
        .filter((annotation) => annotation.annotation_type === AnnotationType.CLASSIFICATION)
        .map((annotation) => {
            const label = annotation.annotation_label.annotation_label_name;
            const sourceName = collectionIdToName[annotation.annotation_collection_id] ?? label;
            const displayLabel = truncateDisplayLabel(label);
            const title = showSourceColors ? `${sourceName}: ${label}` : label;

            return {
                id: `${annotation.annotation_collection_id}:${label}`,
                label,
                displayLabel,
                colorKey: showSourceColors ? sourceName : label,
                title
            };
        });

    return Array.from(new Map(pills.map((pill) => [pill.id, pill])).values()).sort((a, b) =>
        a.title.localeCompare(b.title)
    );
}
