<script lang="ts">
    import { cn } from '$lib/utils';
    import PointSizeControl from './PointSizeControl/PointSizeControl.svelte';
    import { resolveSceneViewportProps } from './resolveSceneViewportProps';
    import type { SceneViewportProps } from './sceneViewportProps';
    import { useSceneViewport } from './useSceneViewport/useSceneViewport.svelte';
    import { provideSceneViewportContext } from './sceneViewportContext';
    import SceneViewportCanvas from './SceneViewportCanvas/SceneViewportCanvas.svelte';
    import SceneViewportOverlay from './SceneViewportOverlay/SceneViewportOverlay.svelte';
    // This wrapper forwards scene inputs and is not exposed as a custom element.
    // svelte-ignore custom_element_props_identifier
    let { pointSize = $bindable(2), ...inputs }: SceneViewportProps = $props();
    const viewportProps = $derived(
        resolveSceneViewportProps({
            ...inputs,
            pointSize,
            isScaleSource: inputs.isScaleSource ?? !inputs.header
        })
    );
    const interaction = useSceneViewport(() => viewportProps);
    provideSceneViewportContext({ getProps: () => viewportProps, interaction });
</script>

<!-- Viewports receive focus for keyboard navigation. -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
    class={cn(
        'relative h-full w-full',
        viewportProps.activeTool === 'create-cuboid' && 'cursor-crosshair'
    )}
    role="application"
    aria-label="Point-cloud scene viewport"
    aria-current={interaction.isActive ? 'true' : undefined}
    data-testid="workspace-scene-viewport"
    tabindex="0"
    onpointerenter={interaction.activate}
    onpointerdown={interaction.activate}
    onfocusin={interaction.activate}
    onmousemove={interaction.handleMouseMove}
    bind:this={interaction.viewport}
>
    <SceneViewportCanvas />
    <SceneViewportOverlay />
    {#if !inputs.header}
        <PointSizeControl bind:value={pointSize} />
    {/if}
</div>
