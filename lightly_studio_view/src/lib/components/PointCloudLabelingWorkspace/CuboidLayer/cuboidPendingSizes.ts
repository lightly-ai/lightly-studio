import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';

interface PendingSizesTracker {
    get(id: string): Domain.Vector3 | undefined;
    set(id: string, size: Domain.Vector3): void;
    delete(id: string): void;
    reconcile(cuboids: readonly Domain.CuboidAnnotation[]): void;
}

/**
 * Tracks in-flight resize values per cuboid so successive gizmo drags
 * accumulate correctly before refreshed annotation data arrives from the server.
 *
 * Call `reconcile` whenever the cuboids list is refreshed — entries whose
 * pending size matches the server value (or whose cuboid disappeared) are cleared.
 */
export function createPendingSizesTracker(): PendingSizesTracker {
    const pending = new Map<string, Domain.Vector3>();

    return {
        get: (id) => pending.get(id),
        set: (id, size) => pending.set(id, size),
        delete: (id) => pending.delete(id),
        reconcile(cuboids) {
            for (const [id, size] of pending) {
                const cuboid = cuboids.find((c) => c.id === id);
                if (
                    !cuboid ||
                    (cuboid.size[0] === size[0] &&
                        cuboid.size[1] === size[1] &&
                        cuboid.size[2] === size[2])
                ) {
                    pending.delete(id);
                }
            }
        }
    };
}
