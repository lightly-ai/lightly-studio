<script lang="ts">
    import RotationCursor from '../RotationCursor/RotationCursor.svelte';
    import SceneNavigationControls from '../SceneNavigationControls.svelte';
    import CuboidTooltipOverlay from '../../CuboidLayer/CuboidTooltip/CuboidTooltipOverlay.svelte';
    import { useSceneViewportContext } from '../sceneViewportContext';
    const { getProps, interaction } = useSceneViewportContext();
    const props = $derived(getProps());
</script>

{#if props.header}
    <div class="absolute inset-x-0 top-0 z-10">
        {@render props.header()}
    </div>
{/if}
{#if interaction.isActive && props.showActiveBorder}
    <div
        class="pointer-events-none absolute inset-0 z-20 border border-primary/30"
        aria-hidden="true"
    ></div>
{/if}
{#if props.tools}
    <div class="absolute left-2 top-10 z-10">
        {@render props.tools()}
    </div>
{/if}
<SceneNavigationControls
    isActive={interaction.isActive}
    showNavigationHelpers={props.showNavigationHelpers}
    navigationId={interaction.navigationId}
    allowRotation={props.cameraMode === 'perspective'}
/>
<RotationCursor
    target={interaction.viewport}
    cursorX={interaction.cursorX}
    cursorY={interaction.cursorY}
/>
{#if props.showAnnotationTooltips}
    <CuboidTooltipOverlay
        cursorX={interaction.cursorX}
        cursorY={interaction.cursorY}
        hoveredAnnotationId={props.hoveredAnnotationId}
        cuboids={props.cuboids}
        annotationClasses={props.annotationClasses}
        annotationSources={props.annotationSources}
    />
{/if}
