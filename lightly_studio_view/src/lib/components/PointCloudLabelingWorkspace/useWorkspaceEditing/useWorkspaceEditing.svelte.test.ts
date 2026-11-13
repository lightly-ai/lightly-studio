import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';
import type { useWorkspaceSceneData } from '../useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { useWorkspaceEditing } from './useWorkspaceEditing.svelte';

vi.mock('@tanstack/svelte-query', () => ({ useQueryClient: () => ({}) }));
vi.mock('../useCreateCuboidAnnotation', () => ({ useCreateCuboidAnnotation: () => ({}) }));
vi.mock('../useDeleteCuboidAnnotation', () => ({ useDeleteCuboidAnnotation: () => ({}) }));
vi.mock('../useUpdateCuboidAnnotation', () => ({ useUpdateCuboidAnnotation: () => ({}) }));
vi.mock('../useStartSequenceTrack', () => ({ useStartSequenceTrack: () => ({}) }));
vi.mock('../useExtendSequenceTrack', () => ({ useExtendSequenceTrack: () => ({}) }));
vi.mock('../useDeleteSequenceTrack', () => ({ useDeleteSequenceTrack: () => ({}) }));
vi.mock('../useUpdateCuboidClass', () => ({ useUpdateCuboidClass: () => ({}) }));

let dispose = () => {};
afterEach(() => dispose());

function setup() {
    let editing!: ReturnType<typeof useWorkspaceEditing>;
    dispose = $effect.root(() => {
        editing = useWorkspaceEditing(
            () => ({}) as PointCloudWorkspaceContext,
            () => ({}) as WorkspaceOptions,
            () => ({ cuboids: [] }) as unknown as ReturnType<typeof useWorkspaceSceneData>,
            () => true
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
});
