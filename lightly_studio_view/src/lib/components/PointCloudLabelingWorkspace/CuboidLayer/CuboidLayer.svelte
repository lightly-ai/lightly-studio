<script lang="ts">
    import { untrack } from 'svelte';
    import { useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type { CuboidLayerProps } from './cuboidLayerProps';
    import { GroundPlaneClickTarget } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import CuboidItem from './CuboidItem/CuboidItem.svelte';
    import { provideCuboidLayerContext } from './cuboidLayerContext';
    import { createCuboidHoverTracker } from './cuboidHoverTracker';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners } from './cuboidSelection';

    interactivity();

    let {
        cuboids,
        annotationClasses,
        transforms,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        cameraMode = 'perspective',
        groundPlaneBounds,
        onselect,
        onhover,
        onCreateCuboid,
        onCuboidTransform
    }: CuboidLayerProps = $props();

    const { renderer } = useThrelte();
    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    const annotations = $derived(transforms.annotations);
    const cuboidIdsKey = $derived(JSON.stringify(cuboids.map(({ id }) => id)));
    const hoverTracker = createCuboidHoverTracker((id, handle) => onhover?.(id, handle));
    provideCuboidLayerContext(() => ({
        annotationClasses,
        transforms,
        activeTool,
        cameraMode,
        hoverTracker,
        selectedAnnotationId,
        hoveredAnnotationId,
        onselect,
        onCuboidTransform
    }));

    $effect(() => {
        void cuboidIdsKey;
        hoverTracker.clear();
        untrack(() => onhover?.(null, null));
    });

    $effect(() => {
        const next = createCuboidRenderItems($annotations);
        renderCuboids = next;
        return () => disposeCuboidRenderItems(next);
    });

    $effect(() => {
        return addCuboidSelectionListeners({
            canvas: renderer.domElement,
            activeTool,
            onselect,
            onhover: (id) => hoverTracker.handleSelectionHover(id),
            isCuboidClicked: () => hoverTracker.isClicked(),
            resetCuboidClicked: () => hoverTracker.resetClicked()
        });
    });
</script>

{#if activeTool === 'create-cuboid'}
    <GroundPlaneClickTarget
        bounds={groundPlaneBounds}
        {cameraMode}
        onclick={(p) => onCreateCuboid?.(p)}
    />
{/if}

{#each renderCuboids as item (item.annotation.id)}
    <CuboidItem {item} />
{/each}
