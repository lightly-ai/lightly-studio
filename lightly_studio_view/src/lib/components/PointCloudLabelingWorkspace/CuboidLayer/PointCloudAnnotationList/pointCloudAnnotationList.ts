import type {
    AnnotationClass,
    AnnotationSource,
    CuboidAnnotation
} from '$lib/components/PointCloudLabelingWorkspace/domain';

export const UNKNOWN_SOURCE_NAME = 'Unknown source';
export const NO_PARENT_TRACK_GROUP_LABEL = 'No parent track';

interface AnnotationGroup {
    readonly sourceId: string;
    readonly sourceName: string;
    readonly cuboids: readonly CuboidAnnotation[];
}

interface GroupAnnotationsBySourceParams {
    cuboids: readonly CuboidAnnotation[];
    sources: readonly AnnotationSource[];
}

interface ResolveAnnotationSourceNameParams {
    annotationSourceId: string | null | undefined;
    sources: readonly AnnotationSource[];
}

interface ResolveAnnotationClassNameParams {
    annotationClasses: readonly AnnotationClass[];
    annotationClassId: string;
}

/** Resolves the human-readable source name for a cuboid, if one is available. */
export function resolveAnnotationSourceName({
    annotationSourceId,
    sources
}: ResolveAnnotationSourceNameParams): string | undefined {
    if (!annotationSourceId) return undefined;
    const name = sources.find(({ id }) => id === annotationSourceId)?.name;
    return name?.trim() ? name : undefined;
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

    function emitWithDescendants(cuboid: CuboidAnnotation): void {
        result.push(cuboid);
        if (cuboid.trackNumber !== null) {
            const children = childrenByParent.get(cuboid.trackNumber);
            if (children) {
                childrenByParent.delete(cuboid.trackNumber);
                for (const child of children) {
                    emitWithDescendants(child);
                }
            }
        }
    }

    const result: CuboidAnnotation[] = [];
    for (const parent of parents) {
        emitWithDescendants(parent);
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

/** A node in the annotation tree, holding a cuboid and its direct subtree. */
interface AnnotationTreeNode {
    /** The cuboid at this node, or null for absent parent group headers. */
    readonly cuboid: CuboidAnnotation | null;
    readonly children: readonly AnnotationTreeNode[];
    /** Total annotations in this subtree, including this node when it has a cuboid. */
    readonly subtreeSize: number;
}

function buildVirtualGroupNode(children: AnnotationTreeNode[]): AnnotationTreeNode {
    return {
        cuboid: null,
        children,
        subtreeSize: children.reduce((sum, c) => sum + c.subtreeSize, 0)
    };
}

interface BuildAnnotationForestParams {
    cuboids: readonly CuboidAnnotation[];
}

interface GroupOrphansUnderAbsentParentsParams {
    orphans: readonly CuboidAnnotation[];
    buildNode: (cuboid: CuboidAnnotation) => AnnotationTreeNode;
}

/**
 * Groups orphans whose parent is absent from the frame into virtual parent nodes.
 *
 * Orphans are grouped by `parentTrackNumber` under a node with `cuboid: null`.
 */
function groupOrphansUnderAbsentParents({
    orphans,
    buildNode
}: GroupOrphansUnderAbsentParentsParams): AnnotationTreeNode[] {
    const orphansByParentTrack = new Map<number, CuboidAnnotation[]>();

    for (const orphan of orphans) {
        const group = orphansByParentTrack.get(orphan.parentTrackNumber!);
        if (group) {
            group.push(orphan);
        } else {
            orphansByParentTrack.set(orphan.parentTrackNumber!, [orphan]);
        }
    }

    const absentParentGroups: AnnotationTreeNode[] = [];
    for (const [, groupCuboids] of orphansByParentTrack) {
        absentParentGroups.push(buildVirtualGroupNode(groupCuboids.map(buildNode)));
    }

    return absentParentGroups;
}

/**
 * Converts a flat, pre-sorted list of cuboids into a forest of annotation trees.
 *
 * Parent roots (with children) become top-level tree nodes.
 * Orphans whose parent is absent from the frame are grouped under a virtual
 * parent node (cuboid: null). Standalone roots (no children) are collected
 * into a "No parent track" group at the end.
 */
export function buildAnnotationForest({
    cuboids
}: BuildAnnotationForestParams): AnnotationTreeNode[] {
    const knownTrackNumbers = new Set<number>(
        cuboids
            .filter((c): c is CuboidAnnotation & { trackNumber: number } => c.trackNumber !== null)
            .map((c) => c.trackNumber)
    );

    const childrenByParentTrack = new Map<number, CuboidAnnotation[]>();
    const roots: CuboidAnnotation[] = [];
    const orphans: CuboidAnnotation[] = [];

    for (const cuboid of cuboids) {
        if (cuboid.parentTrackNumber === null) {
            roots.push(cuboid);
        } else if (knownTrackNumbers.has(cuboid.parentTrackNumber)) {
            const group = childrenByParentTrack.get(cuboid.parentTrackNumber);
            if (group) {
                group.push(cuboid);
            } else {
                childrenByParentTrack.set(cuboid.parentTrackNumber, [cuboid]);
            }
        } else {
            orphans.push(cuboid);
        }
    }

    function buildNode(cuboid: CuboidAnnotation): AnnotationTreeNode {
        const directChildren =
            cuboid.trackNumber !== null
                ? (childrenByParentTrack.get(cuboid.trackNumber) ?? [])
                : [];
        const children = directChildren.map(buildNode);
        return {
            cuboid,
            children,
            subtreeSize: 1 + children.reduce((sum, c) => sum + c.subtreeSize, 0)
        };
    }

    const parentRoots: CuboidAnnotation[] = [];
    const standaloneRoots: CuboidAnnotation[] = [];

    for (const root of roots) {
        if (
            root.trackNumber !== null &&
            (childrenByParentTrack.get(root.trackNumber)?.length ?? 0) > 0
        ) {
            parentRoots.push(root);
        } else {
            standaloneRoots.push(root);
        }
    }

    const absentParentGroups = groupOrphansUnderAbsentParents({
        orphans,
        buildNode
    });

    const noParentTrackChildren = standaloneRoots.map(buildNode);
    const noParentTrackGroup: AnnotationTreeNode[] =
        noParentTrackChildren.length > 0 ? [buildVirtualGroupNode(noParentTrackChildren)] : [];

    return [
        ...parentRoots.map(buildNode),
        ...absentParentGroups,
        ...noParentTrackGroup
    ];
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
