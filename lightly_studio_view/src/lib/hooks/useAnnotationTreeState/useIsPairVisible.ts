import { derived, type Readable } from 'svelte/store';
import type { AnnotationLabelTable, AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationTreeState } from './useAnnotationTreeState';

type IsPairVisible = (sourceId: string, labelId: string) => boolean;

/** Whether the tree eye of an (annotation source, annotation class) pair is on. */
export const useIsPairVisible = (collectionId: string): Readable<IsPairVisible> =>
    derived(useAnnotationTreeState(collectionId).hiddenPairs, ($hiddenPairs) => {
        const hidden = new Set(
            $hiddenPairs.map((pair) => pairId(pair.collection_id, pair.annotation_label_id))
        );
        return (sourceId: string, labelId: string) => !hidden.has(pairId(sourceId, labelId));
    });

/**
 * Whether an annotation is drawn, by the eye of its pair. Annotations name their class but not
 * its id, so the id comes from the labels. A class without an id stays visible.
 */
export const toIsAnnotationVisible = (
    isPairVisible: IsPairVisible,
    labels: Pick<AnnotationLabelTable, 'annotation_label_id' | 'annotation_label_name'>[]
) => {
    const labelIds = new Map(
        labels.map((label) => [label.annotation_label_name, label.annotation_label_id])
    );
    return (annotation: Pick<AnnotationView, 'annotation_collection_id' | 'annotation_label'>) => {
        const labelId = labelIds.get(annotation.annotation_label.annotation_label_name);
        return !labelId || isPairVisible(annotation.annotation_collection_id, labelId);
    };
};

const pairId = (sourceId: string, labelId: string) => `${sourceId}:${labelId}`;
