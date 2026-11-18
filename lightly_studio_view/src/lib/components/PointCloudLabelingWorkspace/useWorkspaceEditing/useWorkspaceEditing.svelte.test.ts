import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';
import type { useWorkspaceSceneData } from '../useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { useWorkspaceEditing } from './useWorkspaceEditing.svelte';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: () => ({}) }));
const { createCuboid } = vi.hoisted(() => ({
    createCuboid: vi.fn(async (_box: unknown, onCreated: (id: string) => Promise<void>) =>
        onCreated('cuboid-2')
    )
}));
vi.mock('../useCreateCuboidAnnotation', () => ({
    useCreateCuboidAnnotation: () => ({ handleCreateCuboid: createCuboid })
}));
vi.mock('../useDeleteCuboidAnnotation', () => ({ useDeleteCuboidAnnotation: () => ({}) }));
vi.mock('../useUpdateCuboidAnnotation', () => ({ useUpdateCuboidAnnotation: () => ({}) }));
vi.mock('../useStartSequenceTrack', () => ({ useStartSequenceTrack: () => ({}) }));
vi.mock('../useExtendSequenceTrack', () => ({ useExtendSequenceTrack: () => ({}) }));
vi.mock('../useDeleteSequenceTrack', () => ({ useDeleteSequenceTrack: () => ({}) }));
vi.mock('../useUpdateCuboidClass', () => ({ useUpdateCuboidClass: () => ({}) }));

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
    const workspace = {
        tickDetails: { refetch: vi.fn().mockResolvedValue(undefined) }
    } as unknown as PointCloudWorkspaceContext;
    dispose = $effect.root(() => {
        editing = useWorkspaceEditing(
            () => workspace,
            () => ({}) as WorkspaceOptions,
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
});
