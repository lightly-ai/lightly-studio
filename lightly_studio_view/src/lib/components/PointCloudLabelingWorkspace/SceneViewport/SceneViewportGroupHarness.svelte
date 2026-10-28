<script lang="ts">
    import SceneViewport from './SceneViewport.svelte';
    import { provideActiveViewportContext } from './activeViewportContext';
    import type { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';

    /** Inputs and callbacks for scene viewport group harness. */
    interface Props {
        /** Shared annotation transforms and their persistence actions. */
        transforms: ReturnType<typeof createCuboidTransformState>;
        /** Advances the main test viewport to the next tick. */
        onMainNext: () => void;
        /** Advances the top test viewport to the next tick. */
        onTopNext: () => void;
    }

    let { transforms, onMainNext, onTopNext }: Props = $props();
    provideActiveViewportContext();
</script>

<SceneViewport {transforms} onNextTick={onMainNext}>
    {#snippet header()}
        <button type="button">Scene settings</button>
    {/snippet}
</SceneViewport>
<SceneViewport {transforms} cameraMode="top" onNextTick={onTopNext} />
