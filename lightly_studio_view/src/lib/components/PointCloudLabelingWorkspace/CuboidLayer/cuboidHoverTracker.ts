import { pickSmallestFromIntersections } from './cuboidSelection';

type CuboidIntersection = Parameters<typeof pickSmallestFromIntersections>[0][number];

interface CuboidHoverTracker {
    enter(annotationId: string, volume: number): void;
    leave(annotationId: string): void;
    clear(): void;
    hit(annotationId: string, volume: number, onselect: (id: string) => void): void;
    handleSelectionHover(annotationId: string | null): void;
    markClicked(): void;
    isClicked(): boolean;
    resetClicked(): void;
}

/**
 * Manages cuboid hover state and batched click-hit resolution.
 *
 * Hover: maintains a map of currently-hovered cuboid volumes and emits the
 * smallest one via `onhover` on every enter/leave.
 *
 * Hit: batches all cuboid click intersections within a single microtask and
 * resolves the smallest one via the per-hit `onselect` callback.
 */
export function createCuboidHoverTracker(
    onhover: (id: string | null, handle: null) => void
): CuboidHoverTracker {
    const hovered = new Map<string, number>();
    let pendingHits: CuboidIntersection[] = [];
    let hitScheduled = false;
    let clicked = false;

    function emitHover(): void {
        const entries = [...hovered.entries()].map(([annotationId, volume]) => ({
            annotationId,
            volume
        }));
        onhover(pickSmallestFromIntersections(entries), null);
    }

    return {
        enter(annotationId, volume) {
            hovered.set(annotationId, volume);
            emitHover();
        },
        leave(annotationId) {
            hovered.delete(annotationId);
            emitHover();
        },
        clear() {
            hovered.clear();
        },
        handleSelectionHover(annotationId) {
            if (annotationId === null) hovered.clear();
            onhover(annotationId, null);
        },
        hit(annotationId, volume, onselect) {
            clicked = true;
            pendingHits.push({ annotationId, volume });
            if (!hitScheduled) {
                hitScheduled = true;
                queueMicrotask(() => {
                    const winnerId = pickSmallestFromIntersections(pendingHits);
                    if (winnerId !== null) onselect(winnerId);
                    pendingHits = [];
                    hitScheduled = false;
                });
            }
        },
        markClicked() {
            clicked = true;
        },
        isClicked() {
            return clicked;
        },
        resetClicked() {
            clicked = false;
        }
    };
}
