import type { AnnotationCollectionView, AnnotationView } from '$lib/api/lightly_studio_local';

export const UNKNOWN_SOURCE_NAME = 'Unknown source';

interface AnnotationSourceGroup {
    id: string;
    name: string;
    annotations: AnnotationView[];
}

/**
 * Groups annotations by their annotation source.
 *
 * Groups are emitted in the order of `sources`. Sources without annotations are
 * skipped. Annotations whose source is not part of `sources` are appended last
 * under a fallback group per source.
 */
export const groupAnnotationsBySource = (
    annotations: AnnotationView[],
    sources: AnnotationCollectionView[]
): AnnotationSourceGroup[] => {
    const annotationsBySourceId = new Map<string, AnnotationView[]>();
    for (const annotation of annotations) {
        const sourceAnnotations = annotationsBySourceId.get(annotation.annotation_collection_id);
        if (sourceAnnotations) {
            sourceAnnotations.push(annotation);
        } else {
            annotationsBySourceId.set(annotation.annotation_collection_id, [annotation]);
        }
    }

    const groups: AnnotationSourceGroup[] = [];
    for (const source of sources) {
        const sourceAnnotations = annotationsBySourceId.get(source.collection_id);
        if (sourceAnnotations) {
            groups.push({
                id: source.collection_id,
                name: source.name,
                annotations: sourceAnnotations
            });
            annotationsBySourceId.delete(source.collection_id);
        }
    }

    for (const [sourceId, sourceAnnotations] of annotationsBySourceId) {
        groups.push({
            id: sourceId,
            name: UNKNOWN_SOURCE_NAME,
            annotations: sourceAnnotations
        });
    }

    return groups;
};

/** ID prefix of the group for a typed source that has no annotation, so no ID, yet. */
export const PENDING_SOURCE_ID_PREFIX = 'pending:';

/**
 * Lists a group for every source, so any source can be picked as the target, also one without
 * annotations on this sample. Groups keep the order of `sources`, then unknown sources, then
 * the target source when it is typed but not created yet.
 */
export const listAllSourceGroups = (
    groups: AnnotationSourceGroup[],
    sources: AnnotationCollectionView[],
    targetSource: string | null
): AnnotationSourceGroup[] => {
    const groupsById = new Map(groups.map((group) => [group.id, group]));
    const sourceIds = new Set(sources.map((source) => source.collection_id));
    const sourceGroups = sources.map(
        (source) =>
            groupsById.get(source.collection_id) ?? {
                id: source.collection_id,
                name: source.name,
                annotations: []
            }
    );
    const unknownGroups = groups.filter((group) => !sourceIds.has(group.id));
    const isTargetPending =
        targetSource !== null && !sources.some((source) => source.name === targetSource);
    const pendingGroups = isTargetPending
        ? [
              {
                  id: `${PENDING_SOURCE_ID_PREFIX}${targetSource}`,
                  name: targetSource,
                  annotations: []
              }
          ]
        : [];
    return [...sourceGroups, ...unknownGroups, ...pendingGroups];
};

/**
 * Returns the line shown above the source groups about where new annotations go, or null when
 * nothing needs saying.
 */
export const getTargetSourceHint = ({
    targetSource,
    isTargetHidden
}: {
    targetSource: string | null;
    isTargetHidden: boolean;
}): string | null => {
    if (targetSource === null) {
        return 'Click the pencil next to a source to choose where new annotations go.';
    }
    // Visibility and target sit in the same row, so hiding the target is easy to do by accident.
    if (isTargetHidden) {
        return `New annotations go to ${targetSource}, which is hidden.`;
    }
    return null;
};

/**
 * Whether every annotation in the list is hidden.
 */
export const areAllAnnotationsHidden = (
    annotations: AnnotationView[],
    hiddenAnnotationIds: Set<string>
): boolean =>
    annotations.length > 0 &&
    annotations.every((annotation) => hiddenAnnotationIds.has(annotation.sample_id));

/**
 * Whether a source group should start expanded: when the grid filter leaves at least one of
 * its annotations visible, or when it holds the annotation the user just created. The latter
 * keeps a brand-new source (absent from the grid selection, so seeded hidden) from appearing
 * collapsed right after adding the first annotation to it.
 * A collapse the user set on an earlier sample replaces the grid filter default.
 */
export const isSourceGroupInitiallyOpen = (
    annotations: AnnotationView[],
    seededHiddenIds: Set<string>,
    lastCreatedAnnotationId: string | null | undefined,
    storedOpen?: boolean
): boolean =>
    (storedOpen ?? !areAllAnnotationsHidden(annotations, seededHiddenIds)) ||
    (lastCreatedAnnotationId != null &&
        annotations.some((annotation) => annotation.sample_id === lastCreatedAnnotationId));

/**
 * Returns the next hidden set after toggling a source's visibility: hides all of the
 * source's annotations unless they are already all hidden, in which case it shows
 * them all. The given hidden set is not mutated.
 */
export const toggleSourceVisibility = (
    sourceAnnotations: AnnotationView[],
    hiddenAnnotationIds: Set<string>
): Set<string> => {
    const hideAll = !areAllAnnotationsHidden(sourceAnnotations, hiddenAnnotationIds);
    const next = new Set(hiddenAnnotationIds);
    for (const annotation of sourceAnnotations) {
        if (hideAll) {
            next.add(annotation.sample_id);
        } else {
            next.delete(annotation.sample_id);
        }
    }
    return next;
};

/**
 * Computes the initially hidden annotations when entering the details page:
 * annotations whose source is not selected in the grid's source filter start hidden.
 *
 * The selection always describes the collection on screen, because
 * useSeedAnnotationSourceFilter fills it for every collection route, so no intersection with
 * this dataset's sources is needed here.
 */
export const computeSeededHiddenIds = (
    annotations: AnnotationView[],
    isSourceVisible: (sourceId: string) => boolean
): Set<string> =>
    new Set(
        annotations
            .filter((annotation) => !isSourceVisible(annotation.annotation_collection_id))
            .map((annotation) => annotation.sample_id)
    );
