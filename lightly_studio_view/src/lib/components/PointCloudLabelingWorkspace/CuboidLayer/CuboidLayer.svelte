<script lang="ts">
    import { untrack } from 'svelte';
    import { useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type * as Domain from '../domain';
    import type { createCuboidTransformState } from './cuboidTransformState';
    import { GroundPlaneClickTarget } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import CuboidItem from './CuboidItem/CuboidItem.svelte';
    import { provideCuboidLayerContext } from './cuboidLayerContext';
    import { createCuboidHoverTracker } from './cuboidHoverTracker';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners } from './cuboidSelection';

    interface Props {
        cuboids: readonly Domain.CuboidAnnotation[];
        annotationClasses: readonly Domain.AnnotationClass[];
        transforms: ReturnType<typeof createCuboidTransformState>;
        selectedAnnotationId?: string | null;
        hoveredAnnotationId?: string | null;
        activeTool?: Domain.WorkspaceTool;
        cameraMode?: Domain.CameraMode;
        groundPlaneBounds: Domain.Bounds3;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        onCreateCuboid?: (position: Domain.Vector3) => void;
        onCuboidTransform?: (
            payload: Parameters<ReturnType<typeof createCuboidTransformState>['commit']>[0]
        ) => void;
    }

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
    }: Props = $props();

    const { renderer } = useThrelte();
    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    const annotations = $derived(transforms.annotations);
    const cuboidIdsKey = $derived(
        JSON.stringify(
            cuboids
                .filter(({ id }) => cameraMode === 'perspective' || id === selectedAnnotationId)
                .map(({ id }) => id)
        )
    );
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
        const visibleAnnotations =
            cameraMode === 'perspective'
                ? $annotations
                : $annotations.filter(({ id }) => id === selectedAnnotationId);
        const next = createCuboidRenderItems(visibleAnnotations, cameraMode);
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
