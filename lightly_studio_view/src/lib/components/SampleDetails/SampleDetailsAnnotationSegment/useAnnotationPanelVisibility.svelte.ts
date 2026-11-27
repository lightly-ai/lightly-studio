import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationCollectionsFilter } from '$lib/hooks';
import { fromStore } from 'svelte/store';
import {
    areAllAnnotationsHidden,
    computeSeededHiddenIds,
    findGroupOfAnnotation,
    isSourceGroupInitiallyOpen,
    isSourceShown,
    toggleAnnotationVisibility,
    toggleAnnotationsVisibility
} from './SampleDetailsAnnotationSegment.helpers';
import { useAnnotationSourceGroupState } from './useAnnotationSourceGroupState';

interface SourceGroup {
    id: string;
    annotations: AnnotationView[];
}

interface UseAnnotationPanelVisibilityParams {
    getSampleId: () => string;
    /** The annotations listed in the panel. */
    getAnnotations: () => AnnotationView[];
    /** Whether the annotation sources have loaded. */
    getAreSourcesLoaded: () => boolean;
    /** One group per source, also for sources without annotations. */
    getGroups: () => SourceGroup[];
    getLastCreatedAnnotationId: () => string | null | undefined;
    getHiddenIds: () => Set<string>;
    setHiddenIds: (ids: Set<string>) => void;
}

/**
 * Which annotations of the Annotations panel are hidden and which source groups are open.
 * Seeds the hidden annotations once per sample from the grid source filter and the visibility
 * the user set on earlier samples, and remembers each change per source.
 */
export const useAnnotationPanelVisibility = (params: UseAnnotationPanelVisibilityParams) => {
    const { getAnnotations, getGroups, getHiddenIds, setHiddenIds } = params;
    const { sourceGroupStates, setSourceGroupState } = useAnnotationSourceGroupState();
    const storedStates = fromStore(sourceGroupStates);
    const gridVisibility = fromStore(useAnnotationCollectionsFilter().isSourceVisible);

    // The hidden set implied by the grid filter alone. A derived, so it's readable at mount,
    // unlike the hidden set the seeding effect writes. Drives the initial collapse.
    const gridHiddenIds = $derived(
        computeSeededHiddenIds(getAnnotations(), gridVisibility.current)
    );

    seedHiddenIdsPerSample(params, (sourceId) =>
        isSourceShown(storedStates.current[sourceId]?.hidden, gridVisibility.current(sourceId))
    );

    const rememberSourceVisibility = (group: SourceGroup) => {
        setSourceGroupState(group.id, {
            hidden: areAllAnnotationsHidden(group.annotations, getHiddenIds())
        });
    };

    return {
        isGroupHidden: (group: SourceGroup) =>
            areAllAnnotationsHidden(group.annotations, getHiddenIds()),
        isGroupInitiallyOpen: (group: SourceGroup) =>
            group.annotations.length > 0 &&
            isSourceGroupInitiallyOpen(
                group.annotations,
                gridHiddenIds,
                params.getLastCreatedAnnotationId(),
                storedStates.current[group.id]?.open
            ),
        setGroupOpen: (groupId: string, open: boolean) => setSourceGroupState(groupId, { open }),
        toggleAnnotation: (annotationId: string) => {
            setHiddenIds(toggleAnnotationVisibility(annotationId, getHiddenIds()));
            // A single source is listed without a group, so its visibility is not remembered.
            const groups = getGroups();
            const group =
                groups.length > 1 ? findGroupOfAnnotation(groups, annotationId) : undefined;
            if (group) rememberSourceVisibility(group);
        },
        toggleGroup: (group: SourceGroup) => {
            setHiddenIds(toggleAnnotationsVisibility(group.annotations, getHiddenIds()));
            rememberSourceVisibility(group);
        }
    };
};

// Seeds the hidden set once per sample. Annotations of sources that are not shown start hidden
// but stay re-showable here without touching the grid filter. Refetches of the same sample keep
// manual changes. Waits for the sources and the annotations, so an empty hidden set is never
// locked in too early.
const seedHiddenIdsPerSample = (
    params: UseAnnotationPanelVisibilityParams,
    isShown: (sourceId: string) => boolean
) => {
    // Not reactive on purpose: it must not re-trigger the effect.
    let seededSampleId: string | undefined = undefined;
    $effect(() => {
        const sampleId = params.getSampleId();
        const annotations = params.getAnnotations();
        if (seededSampleId === sampleId || !params.getAreSourcesLoaded() || !annotations.length) {
            return;
        }
        seededSampleId = sampleId;
        const nextHiddenIds = computeSeededHiddenIds(annotations, isShown);
        // Keep the annotation the user just drew visible, also when its source is hidden.
        nextHiddenIds.delete(params.getLastCreatedAnnotationId() ?? '');
        params.setHiddenIds(nextHiddenIds);
    });
};
