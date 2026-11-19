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

function setup(targetSource = 'labels') {
    let editing!: ReturnType<typeof useWorkspaceEditing>;
    const data = {
        cuboids: [],
        annotationSourceNames: ['labels'],
        refetchAnnotationSources
    } as unknown as ReturnType<typeof useWorkspaceSceneData>;
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
    return editing;
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
});
