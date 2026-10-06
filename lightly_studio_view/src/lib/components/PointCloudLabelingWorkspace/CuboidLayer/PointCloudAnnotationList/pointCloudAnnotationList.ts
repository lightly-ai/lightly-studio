import type {
    AnnotationClass,
    AnnotationSource,
    CuboidAnnotation
} from '$lib/components/PointCloudLabelingWorkspace/domain';

export const UNKNOWN_SOURCE_NAME = 'Unknown source';

interface AnnotationGroup {
    readonly sourceId: string;
    readonly sourceName: string;
    readonly cuboids: readonly CuboidAnnotation[];
}

interface GroupAnnotationsBySourceParams {
    cuboids: readonly CuboidAnnotation[];
    sources: readonly AnnotationSource[];
}

interface ResolveAnnotationClassNameParams {
    annotationClasses: readonly AnnotationClass[];
    annotationClassId: string;
}

interface SortByParentAndTrackNumberParams {
    cuboids: CuboidAnnotation[];
}

function byTrackNumber(a: CuboidAnnotation, b: CuboidAnnotation): number {
    if (a.trackNumber === null && b.trackNumber === null) return 0;
    if (a.trackNumber === null) return 1;
    if (b.trackNumber === null) return -1;
    return a.trackNumber - b.trackNumber;
}

/**
 * Orders cuboids so each parent appears immediately before its children.
 *
 * Top-level cuboids (parentTrackNumber === null) are sorted by trackNumber.
 * Their children follow directly, also sorted by trackNumber.
 * Cuboids whose parent is not present in the list are appended last.
 */
function sortByParentAndTrackNumber({
    cuboids
}: SortByParentAndTrackNumberParams): CuboidAnnotation[] {
    const parents: CuboidAnnotation[] = [];
    const childrenByParent = new Map<number, CuboidAnnotation[]>();

    for (const cuboid of cuboids) {
        if (cuboid.parentTrackNumber === null) {
            parents.push(cuboid);
        } else {
            const siblings = childrenByParent.get(cuboid.parentTrackNumber);
            if (siblings) {
                siblings.push(cuboid);
            } else {
                childrenByParent.set(cuboid.parentTrackNumber, [cuboid]);
            }
        }
    }

    parents.sort(byTrackNumber);
    for (const children of childrenByParent.values()) {
        children.sort(byTrackNumber);
    }

    const result: CuboidAnnotation[] = [];
    for (const parent of parents) {
        result.push(parent);
        if (parent.trackNumber !== null) {
            const children = childrenByParent.get(parent.trackNumber);
            if (children) {
                result.push(...children);
                childrenByParent.delete(parent.trackNumber);
            }
        }
    }

    for (const orphans of childrenByParent.values()) {
        result.push(...orphans);
    }

    return result;
}

/**
 * Groups cuboids by their annotation source.
 *
 * Groups are ordered by the `sources` array. Sources with no cuboids are
 * skipped. Cuboids whose source is absent from `sources` are appended last
 * under a per-source fallback group named {@link UNKNOWN_SOURCE_NAME}.
 */
export function groupAnnotationsBySource({
    cuboids,
    sources
}: GroupAnnotationsBySourceParams): AnnotationGroup[] {
    const bySourceId = new Map<string, CuboidAnnotation[]>();
    for (const cuboid of cuboids) {
        const group = bySourceId.get(cuboid.annotationSourceId);
        if (group) {
            group.push(cuboid);
        } else {
            bySourceId.set(cuboid.annotationSourceId, [cuboid]);
        }
    }

    const groups: AnnotationGroup[] = [];
    for (const source of sources) {
        const sourceCuboids = bySourceId.get(source.id);
        if (sourceCuboids) {
            groups.push({
                sourceId: source.id,
                sourceName: source.name,
                cuboids: sortByParentAndTrackNumber({ cuboids: sourceCuboids })
            });
            bySourceId.delete(source.id);
        }
    }

    for (const [sourceId, sourceCuboids] of bySourceId) {
        groups.push({
            sourceId,
            sourceName: UNKNOWN_SOURCE_NAME,
            cuboids: sortByParentAndTrackNumber({ cuboids: sourceCuboids })
        });
    }

    return groups;
}

/**
 * Resolves the display name for a cuboid's annotation class.
 * Falls back to the raw class ID when the class is not found.
 */
export function resolveAnnotationClassName({
    annotationClasses,
    annotationClassId
}: ResolveAnnotationClassNameParams): string {
    return annotationClasses.find(({ id }) => id === annotationClassId)?.name ?? annotationClassId;
}
