<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { SceneViewState } from '$lib/components/PointCloudViewer';

    /** Inputs and callbacks for scene viewport content harness. */
    interface Props {
        /** Optional header rendered inside the viewport focus boundary. */
        header?: Snippet;
        /** Optional editing controls anchored inside the viewport. */
        tools?: Snippet;
        /** Projection orientation used for rendering and editing. */
        cameraMode?: string;
        fitKey?: string;
        /** Shared camera state received through the workspace context. */
        viewState?: SceneViewState | null;
        /** Simulates camera navigation without creating a WebGL renderer. */
        onViewStateChange?: (state: SceneViewState) => void;
    }

    let {
        header,
        tools,
        cameraMode = 'perspective',
        viewState,
        fitKey,
        onViewStateChange
    }: Props = $props();
    let localViewState = $state<SceneViewState | null>(null);
    $effect(() => {
        void fitKey;
        localViewState = null;
    });
    function navigate() {
        localViewState = {
            target: [1, 2, 3],
            worldUnitsPerPixel: cameraMode === 'perspective' ? 0.05 : 0.025
        };
        onViewStateChange?.(localViewState);
    }
</script>

<section aria-label={cameraMode} data-testid="scene-viewport-instance">
    {@render header?.()}
    {@render tools?.()}
    <output aria-label={`${cameraMode} scale`}
        >{(viewState ?? localViewState)?.worldUnitsPerPixel ?? 'unset'}</output
    >
    <button onclick={navigate}>Navigate {cameraMode}</button>
</section>
