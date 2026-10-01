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
            groups.push({ sourceId: source.id, sourceName: source.name, cuboids: sourceCuboids });
            bySourceId.delete(source.id);
        }
    }

    for (const [sourceId, sourceCuboids] of bySourceId) {
        groups.push({ sourceId, sourceName: UNKNOWN_SOURCE_NAME, cuboids: sourceCuboids });
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
