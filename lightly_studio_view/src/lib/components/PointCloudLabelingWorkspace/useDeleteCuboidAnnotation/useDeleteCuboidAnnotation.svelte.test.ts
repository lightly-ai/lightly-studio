import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { createAnnotationIdMap } from '../cuboidUndo';
import { useDeleteCuboidAnnotation } from './useDeleteCuboidAnnotation.svelte';

const { deleteWithUndo } = vi.hoisted(() => ({ deleteWithUndo: vi.fn() }));

vi.mock('$lib/hooks', () => ({
    useDeleteAnnotationWithUndo: () => ({ deleteWithUndo })
}));

const cuboid = { sample_id: 'cuboid-1' } as AnnotationView;

describe('useDeleteCuboidAnnotation', () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    let annotationIds = createAnnotationIdMap();

    const setup = () =>
        useDeleteCuboidAnnotation({
            getCollectionId: () => 'collection-1',
            getAnnotations: () => [cuboid],
            annotationIds,
            refresh
        });

    beforeEach(() => {
        vi.resetAllMocks();
        deleteWithUndo.mockResolvedValue(true);
        annotationIds = createAnnotationIdMap();
    });

    it('deletes the cuboid with undo', async () => {
        expect(await setup().handleDeleteCuboid('cuboid-1')).toBe(true);

        expect(deleteWithUndo).toHaveBeenCalledWith(cuboid, refresh, expect.any(Function));
    });

    it('maps the deleted cuboid to its restored copy', async () => {
        await setup().handleDeleteCuboid('cuboid-1');
        const onRestored = deleteWithUndo.mock.calls[0][2];

        onRestored({ sample_id: 'restored-1' });

        expect(annotationIds.resolve('cuboid-1')).toBe('restored-1');
    });

    it('deletes nothing for an unknown cuboid', async () => {
        expect(await setup().handleDeleteCuboid('other')).toBe(false);

        expect(deleteWithUndo).not.toHaveBeenCalled();
    });
});
