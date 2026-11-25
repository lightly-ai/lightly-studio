import { getContext, setContext } from 'svelte';
import type { CameraMode } from './domain';
import type { PointCloudWorkspaceLayoutState } from './pointCloudWorkspaceLayoutContext.svelte';
const KEY = Symbol('workspace-scene-layout');

/** Provides expansion state to scene viewports and ends a cuboid draft of a removed viewport. */
export function provideWorkspaceSceneLayout(getLayout: () => PointCloudWorkspaceLayoutState) {
    let expandedProjection = $state<CameraMode | null>(null);
    let hadOrthographicViews = false;
    $effect(() => {
        const layout = getLayout();
        const hasOrthographicViews = layout.showOrthographicViews;
        if (!hasOrthographicViews) {
            expandedProjection = null;
            // A removed viewport cannot clear the highlight of its cuboid draft.
            if (hadOrthographicViews) layout.onCuboidDraftChange(null);
        }
        hadOrthographicViews = hasOrthographicViews;
    });
    const context = {
        get expandedProjection() {
            return expandedProjection;
        },
        toggleExpanded: (mode: CameraMode) => {
            expandedProjection = expandedProjection === mode ? null : mode;
        }
    };
    setContext(KEY, context);
    return context;
}

/** Reads the camera state scoped to this workspace's scene layout. */
export function useWorkspaceSceneLayout() {
    const context = getContext<ReturnType<typeof provideWorkspaceSceneLayout> | undefined>(KEY);
    if (!context) throw new Error('Workspace scene layout context is missing.');
    return context;
}
