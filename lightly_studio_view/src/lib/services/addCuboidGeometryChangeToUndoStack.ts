import type { Cuboid3dCreate } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const CUBOID_GEOMETRY_CHANGE_GROUP_ID = 'cuboid-geometry-change';

export const addCuboidGeometryChangeToUndoStack = ({
    annotationId,
    previousCuboid,
    addReversibleAction,
    restoreGeometry
}: {
    annotationId: string;
    /** The geometry and interpolation flag before the change. */
    previousCuboid: Cuboid3dCreate;
    addReversibleAction: (action: ReversibleAction) => void;
    restoreGeometry: (annotationId: string, cuboid: Cuboid3dCreate) => Promise<boolean>;
}) => {
    addReversibleAction({
        id: `cuboid-geometry-change-${annotationId}-${Date.now()}`,
        description: 'Undo cuboid geometry change',
        execute: async () => {
            const restored = await restoreGeometry(annotationId, previousCuboid);
            // A rejected undo stays in the undo history, so the user can try again.
            if (!restored) {
                throw new Error(`Failed to restore the geometry of annotation ${annotationId}.`);
            }
        },
        timestamp: new Date(),
        groupId: CUBOID_GEOMETRY_CHANGE_GROUP_ID
    });
};
