import type { DistributionSource } from '$lib/components/DatasetDistributionPanel';
import { AnnotationType, type VideoFilter } from '$lib/api/lightly_studio_local';
import { useVideoAnnotationCounts } from '$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js';
import { toCategoryCounts } from '../distributionHandlers';

interface UseVideoClassDistributionSourceParams {
    collectionId: string;
    filter: VideoFilter | undefined;
    /** Labels selected in the sidebar's LabelsMenu. */
    selectedClassNames: string[];
    /** True when every annotation source is unchecked. */
    allSourcesHidden: boolean;
}

// One count query per group. The "All types" group counts every annotation type.
const CLASS_COUNT_GROUPS = [
    { id: 'all', label: 'All types', annotationType: undefined },
    {
        id: AnnotationType.CLASSIFICATION,
        label: 'Classification',
        annotationType: AnnotationType.CLASSIFICATION
    },
    {
        id: AnnotationType.OBJECT_DETECTION,
        label: 'Object detection',
        annotationType: AnnotationType.OBJECT_DETECTION
    },
    {
        id: AnnotationType.SEGMENTATION_MASK,
        label: 'Segmentation',
        annotationType: AnnotationType.SEGMENTATION_MASK
    }
];

/**
 * Builds the annotation class source of the video distribution panel. The counts are
 * videos, not annotations: a video counts once for each class that it or its frames contain.
 */
export function useVideoClassDistributionSource(
    getParams: () => UseVideoClassDistributionSourceParams
) {
    const classCountGroups = CLASS_COUNT_GROUPS.map(({ id, label, annotationType }) => ({
        id,
        label,
        query: useVideoAnnotationCounts(() => {
            const { collectionId, filter, allSourcesHidden } = getParams();
            return { collectionId, filter, annotationType, enabled: !allSourcesHidden };
        })
    }));

    const source = $derived.by<DistributionSource>(() => {
        const { selectedClassNames, allSourcesHidden } = getParams();
        const base = {
            id: 'classes',
            label: 'Annotation classes',
            groupLabel: 'Annotation type',
            valueNoun: 'videos'
        };
        const [allTypesGroup, ...perTypeGroups] = classCountGroups.map(({ id, label, query }) => ({
            id,
            label,
            loading: query.isFetching,
            // With every annotation source unchecked, the class distribution has nothing to show.
            data: allSourcesHidden ? [] : toCategoryCounts(query.data, selectedClassNames)
        }));
        // Skip types with no matches in the current view so the picker stays clean.
        const typeGroups = perTypeGroups.filter((group) => group.data.length > 0);
        // With zero or one populated type, "All types" would just duplicate it —
        // drop the group picker entirely.
        if (typeGroups.length <= 1) {
            return { ...base, loading: allTypesGroup.loading, data: allTypesGroup.data };
        }
        return { ...base, groups: [allTypesGroup, ...typeGroups] };
    });

    return {
        get source() {
            return source;
        }
    };
}
