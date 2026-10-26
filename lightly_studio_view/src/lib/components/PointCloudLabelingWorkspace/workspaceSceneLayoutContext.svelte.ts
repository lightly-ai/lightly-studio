import { getContext, setContext } from 'svelte';
import type { CameraMode } from './domain';
import type { SceneViewState } from '$lib/components/PointCloudViewer';
import type { PointCloudWorkspaceLayoutState } from './pointCloudWorkspaceLayoutContext.svelte';
const KEY = Symbol('workspace-scene-layout');

/** Provides shared camera synchronization and expansion state to scene viewports. */
export function provideWorkspaceSceneLayout(getLayout: () => PointCloudWorkspaceLayoutState) {
    let viewState = $state<SceneViewState | null>(null);
    let expandedProjection = $state<CameraMode | null>(null);
    let fitKey: string | undefined;
    $effect(() => {
        const layout = getLayout();
        if (!layout.showOrthographicViews) expandedProjection = null;
    });
    $effect(() => {
        const nextKey = getLayout().fitKey;
        if (nextKey === fitKey) return;
        fitKey = nextKey;
        viewState = null;
    });
    const context = {
        get viewState() {
            return viewState;
        },
        get expandedProjection() {
            return expandedProjection;
        },
        onViewStateChange: (next: SceneViewState) => {
            viewState = next;
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
