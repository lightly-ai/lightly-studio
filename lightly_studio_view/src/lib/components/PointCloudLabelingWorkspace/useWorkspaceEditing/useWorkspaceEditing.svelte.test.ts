import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';
import type { useWorkspaceSceneData } from '../useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { getTickDetailsSequenceQueryKey } from '$lib/hooks';
import { useWorkspaceEditing } from './useWorkspaceEditing.svelte';

const { invalidateQueries } = vi.hoisted(() => ({ invalidateQueries: vi.fn() }));
vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: () => ({ invalidateQueries }) }));
vi.mock('$lib/hooks', () => ({
    useGlobalStorage: () => ({ addReversibleAction: vi.fn() }),
    getTickDetailsSequenceQueryKey: (sequence: unknown) => ['tick-details', sequence]
}));
const { captured, createCuboid } = vi.hoisted(() => ({
    captured: { onGeometryUpdated: (): Promise<unknown> => Promise.resolve() },
    createCuboid: vi.fn(async (_box: unknown, onCreated: (id: string) => Promise<void>) =>
        onCreated('cuboid-2')
    )
}));
vi.mock('../useCreateCuboidAnnotation', () => ({
    useCreateCuboidAnnotation: () => ({ handleCreateCuboid: createCuboid })
}));
const { deleteCuboid, waitForSaves, useDeleteCuboidAnnotation } = vi.hoisted(() => {
    const deleteCuboid = vi.fn();
    return {
        deleteCuboid,
        waitForSaves: vi.fn(),
        useDeleteCuboidAnnotation: vi.fn<
            (params: { refresh: () => Promise<unknown> }) => {
                handleDeleteCuboid: typeof deleteCuboid;
            }
        >(() => ({ handleDeleteCuboid: deleteCuboid }))
    };
});
vi.mock('../useDeleteCuboidAnnotation', () => ({ useDeleteCuboidAnnotation }));
vi.mock('../useUpdateCuboidAnnotation', () => ({
    useUpdateCuboidAnnotation: (params: { onUpdated: () => Promise<unknown> }) => {
        captured.onGeometryUpdated = params.onUpdated;
        return { waitForSaves };
    }
}));
vi.mock('../useStartSequenceTrack', () => ({ useStartSequenceTrack: () => ({}) }));
vi.mock('../useExtendSequenceTrack', () => ({ useExtendSequenceTrack: () => ({}) }));
vi.mock('../useDeleteSequenceTrack', () => ({ useDeleteSequenceTrack: () => ({}) }));
vi.mock('../useUpdateCuboidClass', () => ({ useUpdateCuboidClass: () => ({}) }));

const sequence = { datasetId: 'dataset-1', sequenceId: 'sequence-1' };
const refetch = vi.fn().mockResolvedValue(undefined);
let dispose = () => {};
afterEach(() => dispose());

const refetchAnnotationSources = vi.fn();

type SceneData = ReturnType<typeof useWorkspaceSceneData>;
type Cuboid = SceneData['cuboids'][number];

const cuboid = (id: string, trackId: string | null) => ({ id, trackId }) as Cuboid;

function setup(targetSource = 'labels', cuboids: Cuboid[] = []) {
    let editing!: ReturnType<typeof useWorkspaceEditing>;
    let tickCuboids = $state(cuboids);
    const data = {
        get cuboids() {
            return tickCuboids;
        },
        annotationSourceNames: ['labels'],
        refetchAnnotationSources
    } as unknown as SceneData;
    const workspace = { tickDetails: { refetch } } as unknown as PointCloudWorkspaceContext;
    dispose = $effect.root(() => {
        editing = useWorkspaceEditing(
            () => workspace,
            () => sequence as WorkspaceOptions,
            () => data,
            () => true,
            () => ({ targetSource, blockedReason: null, needsPick: false })
        );
    });
    editing.selectedCuboidId = 'cuboid-1';
    flushSync();
    const showTick = (nextCuboids: Cuboid[]) => {
        tickCuboids = nextCuboids;
        flushSync();
    };
    return Object.assign(editing, { showTick });
}

describe('useWorkspaceEditing', () => {
    it('clears the selection when the create tool is chosen', () => {
        const editing = setup();
        editing.activeTool = 'create-cuboid';
        expect(editing.selectedCuboidId).toBeNull();
    });

    it('clears the selection when adding a track starts the create tool', () => {
        const editing = setup();
        editing.toggleAddTrack();
        expect(editing.activeTool).toBe('create-cuboid');
        expect(editing.selectedCuboidId).toBeNull();
    });

    it('keeps the selection when another tool is chosen', () => {
        const editing = setup();
        editing.activeTool = 'select';
        expect(editing.selectedCuboidId).toBe('cuboid-1');
    });

    it('reloads the sources after a cuboid created a new source', async () => {
        refetchAnnotationSources.mockClear();
        const editing = setup('review');
        await editing.handleCreateCuboid({ center: [0, 0, 0], size: [1, 1, 1], yaw: 0 });
        expect(refetchAnnotationSources).toHaveBeenCalledOnce();
    });

    it('does not reload the sources after a cuboid went to an existing source', async () => {
        refetchAnnotationSources.mockClear();
        const editing = setup('labels');
        await editing.handleCreateCuboid({ center: [0, 0, 0], size: [1, 1, 1], yaw: 0 });
        expect(refetchAnnotationSources).not.toHaveBeenCalled();
    });

    it('refreshes the other ticks after a cuboid geometry update', async () => {
        setup();
        refetch.mockClear();

        await captured.onGeometryUpdated();

        expect(invalidateQueries).toHaveBeenCalledWith({
            queryKey: getTickDetailsSequenceQueryKey(sequence),
            refetchType: 'none'
        });
        expect(refetch).toHaveBeenCalledOnce();
    });

    it('deletes a cuboid after its running saves are complete', async () => {
        let finishSaves!: () => void;
        waitForSaves.mockReturnValue(new Promise<void>((resolve) => (finishSaves = resolve)));
        deleteCuboid.mockResolvedValue(true);
        const editing = setup();

        const deleting = editing.handleDeleteCuboid('cuboid-1');
        await Promise.resolve();
        expect(waitForSaves).toHaveBeenCalledWith('cuboid-1');
        expect(deleteCuboid).not.toHaveBeenCalled();
        finishSaves();
        await deleting;

        expect(deleteCuboid).toHaveBeenCalledWith('cuboid-1');
        expect(editing.selectedCuboidId).toBeNull();
    });

    it('clears the selection when the refresh after a delete fails', async () => {
        waitForSaves.mockResolvedValue(undefined);
        deleteCuboid.mockRejectedValue(new Error('refresh failed'));
        const editing = setup();
        editing.selectedCuboidId = 'cuboid-1';

        await expect(editing.handleDeleteCuboid('cuboid-1')).rejects.toThrow('refresh failed');

        expect(editing.selectedCuboidId).toBeNull();
    });

    it('completes the delete refresh after the tracks and ticks are refetched', async () => {
        let finishTicks!: () => void;
        invalidateQueries.mockClear();
        invalidateQueries
            .mockResolvedValueOnce(undefined)
            .mockReturnValueOnce(new Promise<void>((resolve) => (finishTicks = resolve)));
        setup();
        const { refresh } = useDeleteCuboidAnnotation.mock.lastCall![0];
        let isComplete = false;

        const refreshing = refresh().then(() => (isComplete = true));
        await Promise.resolve();
        expect(invalidateQueries).toHaveBeenCalledTimes(2);
        expect(isComplete).toBe(false);
        finishTicks();
        await refreshing;

        expect(isComplete).toBe(true);
    });

    describe('on a tick change', () => {
        it('selects the cuboid of the same track', () => {
            const editing = setup('labels', [cuboid('cuboid-1', 'track-1')]);
            editing.showTick([cuboid('cuboid-9', 'track-2'), cuboid('cuboid-5', 'track-1')]);
            expect(editing.selectedCuboidId).toBe('cuboid-5');
        });

        it('selects the track again after a tick without it', () => {
            const editing = setup('labels', [cuboid('cuboid-1', 'track-1')]);
            editing.showTick([]);
            editing.showTick([cuboid('cuboid-7', 'track-1')]);
            expect(editing.selectedCuboidId).toBe('cuboid-7');
        });

        it('does not select another cuboid for an untracked cuboid', () => {
            const editing = setup('labels', [cuboid('cuboid-1', null)]);
            editing.showTick([cuboid('cuboid-5', null)]);
            expect(editing.selectedCuboidId).toBe('cuboid-1');
        });

        it('keeps a selection of the next tick that is not loaded yet', () => {
            const editing = setup('labels', [
                cuboid('cuboid-1', 'track-1'),
                cuboid('cuboid-2', 'track-2')
            ]);
            editing.selectedCuboidId = 'cuboid-8';
            flushSync();
            editing.showTick([cuboid('cuboid-5', 'track-1'), cuboid('cuboid-8', 'track-2')]);
            expect(editing.selectedCuboidId).toBe('cuboid-8');
        });

        it('does not select the track after the selection is cleared', () => {
            const editing = setup('labels', [cuboid('cuboid-1', 'track-1')]);
            editing.selectedCuboidId = null;
            flushSync();
            editing.showTick([cuboid('cuboid-5', 'track-1')]);
            expect(editing.selectedCuboidId).toBeNull();
        });
    });
});
