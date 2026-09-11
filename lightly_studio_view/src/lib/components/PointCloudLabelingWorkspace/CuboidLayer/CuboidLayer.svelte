<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import CuboidTooltip from './CuboidTooltip/CuboidTooltip.svelte';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners } from './cuboidSelection';

    interactivity();

    /** Renders cuboid annotations with selection, hover highlights, and manipulation handles. */
    interface Props {
        /** Cuboids to render in the active point-cloud frame. */
        cuboids: readonly Domain.CuboidAnnotation[];
        /** Annotation classes used to resolve each cuboid's display color. */
        annotationClasses: readonly Domain.AnnotationClass[];
        /** Identity of the currently selected cuboid, or null. */
        selectedAnnotationId?: string | null;
        /** Identity of the currently hovered cuboid, or null. */
        hoveredAnnotationId?: string | null;
        /** Tool that determines whether cuboids can be selected. */
        activeTool?: Domain.WorkspaceTool;
        /** Bounds of the point cloud containing the cuboids. */
        pointCloudBounds: Domain.Bounds3;
        /** Fires when the user selects or deselects a cuboid. */
        onselect?: (annotationId: string | null) => void;
        /** Fires when the pointer enters or leaves a cuboid. */
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        /** Fires when a drag ends with the updated cuboid geometry. */
        oncuboidupdate?: (cuboid: Domain.CuboidAnnotation) => void;
    }

    let {
        cuboids,
        annotationClasses,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        onselect,
        onhover,
        oncuboidupdate
    }: Props = $props();

    const { renderer } = useThrelte();
    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    let cuboidClicked = false;

    $effect(() => {
        const next = createCuboidRenderItems(cuboids);
        renderCuboids = next;
        return () => disposeCuboidRenderItems(next);
    });

    $effect(() => {
        return addCuboidSelectionListeners({
            canvas: renderer.domElement,
            activeTool,
            onselect,
            isCuboidClicked: () => cuboidClicked,
            resetCuboidClicked: () => (cuboidClicked = false)
        });
    });
</script>

{#each renderCuboids as item (item.annotation.id)}
    {@const base = resolveCuboidColor(annotationClasses, item.annotation.annotationClassId)}
    {@const annotationClassName =
        annotationClasses.find(({ id }) => id === item.annotation.annotationClassId)?.name ??
        item.annotation.annotationClassId}
    {@const isSelected = selectedAnnotationId === item.annotation.id}
    {@const isHovered = hoveredAnnotationId === item.annotation.id}
    {@const color = highlightCuboidColor(base, isSelected, isHovered)}
    {#snippet visual()}
        <CuboidVisual
            {item}
            baseColor={base}
            edgeColor={color}
            {activeTool}
            {onselect}
            {onhover}
            onselected={() => (cuboidClicked = true)}
        />
        {#if isHovered}
            <CuboidTooltip {annotationClassName} annotation={item.annotation} />
        {/if}
    {/snippet}

    {#if isSelected}
        <CuboidGizmo annotation={item.annotation} {activeTool} {oncuboidupdate}>
            {@render visual()}
        </CuboidGizmo>
    {:else}
        <T.Group position={[...item.annotation.center]} quaternion={[...item.annotation.rotation]}>
            {@render visual()}
        </T.Group>
    {/if}
{/each}
