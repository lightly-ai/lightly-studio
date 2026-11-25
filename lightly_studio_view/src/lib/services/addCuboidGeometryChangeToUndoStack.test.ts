import { describe, expect, it, vi } from 'vitest';
import type { Cuboid3dCreate } from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';
import {
    addCuboidGeometryChangeToUndoStack,
    CUBOID_GEOMETRY_CHANGE_GROUP_ID
} from './addCuboidGeometryChangeToUndoStack';

const previousCuboid: Cuboid3dCreate = {
    frame_id: 'lidar-top',
    px: 1,
    py: 2,
    pz: 3,
    qx: 0,
    qy: 0,
    qz: 0,
    qw: 1,
    sx: 4,
    sy: 5,
    sz: 6,
    interpolated: true
};

describe('addCuboidGeometryChangeToUndoStack', () => {
    it('adds an undo that restores the previous geometry', async () => {
        const addReversibleAction = vi.fn();
        const restoreGeometry = vi.fn().mockResolvedValue(true);

        addCuboidGeometryChangeToUndoStack({
            annotationId: 'cuboid-1',
            previousCuboid,
            addReversibleAction,
            restoreGeometry
        });
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;
        await action.execute();

        expect(action.groupId).toBe(CUBOID_GEOMETRY_CHANGE_GROUP_ID);
        expect(restoreGeometry).toHaveBeenCalledWith('cuboid-1', previousCuboid);
    });

    it('rejects the undo when the restore fails, so the undo stays in the history', async () => {
        const addReversibleAction = vi.fn();

        addCuboidGeometryChangeToUndoStack({
            annotationId: 'cuboid-1',
            previousCuboid,
            addReversibleAction,
            restoreGeometry: vi.fn().mockResolvedValue(false)
        });
        const action = addReversibleAction.mock.calls[0][0] as ReversibleAction;

        await expect(action.execute()).rejects.toThrow(
            'Failed to restore the geometry of annotation cuboid-1.'
        );
    });
});
