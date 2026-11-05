import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

/**
 * The names of the sources whose annotations on the sample are all hidden. Classifications are
 * left out, like in the Annotations panel, and a source without annotations is never hidden.
 */
export const listHiddenSources = (
    sources: { collection_id: string; name: string }[],
    annotations: AnnotationView[],
    hiddenIds: Set<string>
): string[] =>
    sources
        .filter((source) => {
            const shown = annotations.filter(
                (annotation) =>
                    annotation.annotation_collection_id === source.collection_id &&
                    annotation.annotation_type !== AnnotationType.CLASSIFICATION
            );
            return shown.length > 0 && shown.every(({ sample_id }) => hiddenIds.has(sample_id));
        })
        .map((source) => source.name);
