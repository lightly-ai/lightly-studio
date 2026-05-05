import { derived, get, readonly, writable, type Readable } from 'svelte/store';
import type { AnnotationsFilter } from '$lib/api/lightly_studio_local';
import type { Annotation } from '$lib/types';
import type { AnnotationLabel } from '$lib/services/types';
import { useGlobalStorage } from '../useGlobalStorage';
import { useTags } from '../useTags/useTags';

/**
 * Low-level hook: manages selected annotation label IDs and produces an AnnotationsFilter.
 *
 * Optionally accepts a collectionId to include tag_ids from useTags.
 */
export function useSelectedAnnotationsFilter(collectionId?: string) {
    const {
        selectedAnnotationFilterIds,
        setSelectedAnnotationFilterIds: toggleSelectedAnnotationFilterId,
        clearSelectedAnnotationFilterIds
    } = useGlobalStorage();

    const selectedAnnotationFilterIdsArray: Readable<string[]> = derived(
        selectedAnnotationFilterIds,
        ($set) => Array.from($set)
    );

    let tagsSelected: Readable<Set<string>> | undefined;
    if (collectionId) {
        const tagsHook = useTags({ collection_id: collectionId, kind: ['annotation'] });
        tagsSelected = tagsHook.tagsSelected;
    }

    const annotationLabelIds: Readable<string[] | undefined> = derived(
        selectedAnnotationFilterIds,
        ($set) => ($set.size > 0 ? Array.from($set) : undefined)
    );

    const annotationFilter: Readable<AnnotationsFilter | undefined> = derived(
        tagsSelected ? [selectedAnnotationFilterIds, tagsSelected] : [selectedAnnotationFilterIds],
        (stores) => {
            const $set = stores[0] as Set<string>;
            const $tags = stores[1] as Set<string> | undefined;

            if ($set.size === 0 && (!$tags || $tags.size === 0)) {
                return undefined;
            }

            const filter: AnnotationsFilter = {
                filter_type: 'annotations'
            };
            if ($set.size > 0) {
                filter.annotation_label_ids = Array.from($set);
            }

            if ($tags && $tags.size > 0) {
                filter.tag_ids = Array.from($tags);
            }

            return filter;
        }
    );

    return {
        selectedAnnotationFilterIds: readonly(selectedAnnotationFilterIds),
        selectedAnnotationFilterIdsArray: readonly(selectedAnnotationFilterIdsArray),
        annotationLabelIds: readonly(annotationLabelIds),
        annotationFilter: readonly(annotationFilter),
        toggleSelectedAnnotationFilterId,
        clearSelectedAnnotationFilterIds
    };
}

interface AnnotationCount {
    label_name: string;
    total_count: number;
    current_count?: number;
}

/**
 * High-level hook: returns UI-ready annotation filter rows and a toggle-by-label-name function.
 *
 * Takes annotation labels (from useAnnotationLabels). Annotation counts are fed in via
 * setAnnotationCounts to avoid circular init-order issues in Svelte components.
 */
export function useAnnotationsFilter({
    annotationLabels,
    collectionId
}: {
    annotationLabels: Readable<AnnotationLabel[] | undefined>;
    collectionId?: string;
}) {
    const {
        selectedAnnotationFilterIds,
        selectedAnnotationFilterIdsArray,
        annotationLabelIds,
        annotationFilter,
        toggleSelectedAnnotationFilterId,
        clearSelectedAnnotationFilterIds
    } = useSelectedAnnotationsFilter(collectionId);

    // Internal writable for annotation counts, set via setAnnotationCounts
    const annotationCountsStore = writable<AnnotationCount[] | undefined>(undefined);

    const setAnnotationCounts = (counts: AnnotationCount[] | undefined) => {
        annotationCountsStore.set(counts);
    };

    // Name -> ID mapping
    const annotationFilterLabels: Readable<Record<string, string>> = derived(
        annotationLabels,
        ($labels) => {
            if (!$labels) return {};
            return $labels.reduce(
                (nameToIdMap: Record<string, string>, label: AnnotationLabel) => ({
                    ...nameToIdMap,
                    [label.annotation_label_name!]: label.annotation_label_id!
                }),
                {}
            );
        }
    );

    // Selected label names (reverse lookup)
    const selectedAnnotationFilterNames: Readable<string[]> = derived(
        [annotationFilterLabels, selectedAnnotationFilterIds],
        ([$labelsMap, $selectedIds]) => {
            const idsArray = Array.from($selectedIds);
            return Object.entries($labelsMap)
                .filter(([, id]) => idsArray.includes(id))
                .map(([name]) => name);
        }
    );

    // UI-ready rows for LabelsMenu
    const annotationFilterRows: Readable<Annotation[]> = derived(
        [annotationCountsStore, selectedAnnotationFilterNames],
        ([$counts, $selectedNames]) => {
            if (!$counts) return [];
            return $counts.map((annotation) => ({
                ...annotation,
                selected: $selectedNames.includes(annotation.label_name)
            }));
        }
    );

    // Toggle by label name
    const toggleAnnotationFilterSelection = (labelName: string) => {
        const labelsMap = get(annotationFilterLabels);
        const labelId = labelsMap[labelName];
        if (labelId) {
            toggleSelectedAnnotationFilterId(labelId);
        }
    };

    return {
        selectedAnnotationFilterIds,
        selectedAnnotationFilterIdsArray,
        annotationLabelIds,
        annotationFilter,
        annotationFilterRows,
        annotationFilterLabels,
        selectedAnnotationFilterNames,
        setAnnotationCounts,
        toggleAnnotationFilterSelection,
        toggleSelectedAnnotationFilterId,
        clearSelectedAnnotationFilterIds
    };
}
