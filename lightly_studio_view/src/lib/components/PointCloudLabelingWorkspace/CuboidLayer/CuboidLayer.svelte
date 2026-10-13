<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners, pickSmallestFromIntersections } from './cuboidSelection';

    type CuboidIntersection = Parameters<typeof pickSmallestFromIntersections>[0][number];

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
    }

    let {
        cuboids,
        annotationClasses,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        onselect,
        onhover
    }: Props = $props();

    const { renderer } = useThrelte();
    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    let cuboidClicked = false;

    // Pending hits from the current click event — all overlapping cuboids report here.
    let pendingHits: CuboidIntersection[] = [];
    let hitScheduled = false;

    // Currently-hovered cuboids: annotationId → volume. Maintained across pointer-enter/leave
    // events so that the smallest overlapping cuboid is always highlighted.
    let hoveredCuboids = new Map<string, number>();

    function onCuboidHit(annotationId: string, volume: number): void {
        if (activeTool !== 'select') return;
        cuboidClicked = true;
        pendingHits.push({ annotationId, volume });
        if (!hitScheduled) {
            hitScheduled = true;
            queueMicrotask(() => {
                const winnerId = pickSmallestFromIntersections(pendingHits);
                if (winnerId !== null) onselect?.(winnerId);
                pendingHits = [];
                hitScheduled = false;
            });
        }
    }

    function hoveredAsIntersections(): CuboidIntersection[] {
        return [...hoveredCuboids.entries()].map(([annotationId, volume]) => ({
            annotationId,
            volume
        }));
    }

    function onCuboidHoverEnter(annotationId: string, volume: number): void {
        hoveredCuboids.set(annotationId, volume);
        onhover?.(pickSmallestFromIntersections(hoveredAsIntersections()), null);
    }

    function onCuboidHoverLeave(annotationId: string): void {
        hoveredCuboids.delete(annotationId);
        onhover?.(pickSmallestFromIntersections(hoveredAsIntersections()), null);
    }

    $effect(() => {
        hoveredCuboids.clear();
        onhover?.(null, null);
        const next = createCuboidRenderItems(cuboids);
        renderCuboids = next;
        return () => disposeCuboidRenderItems(next);
    });

    $effect(() => {
        return addCuboidSelectionListeners({
            canvas: renderer.domElement,
            activeTool,
            onselect,
            onhover: (id, handle) => {
                if (id === null) hoveredCuboids.clear();
                onhover?.(id, handle);
            },
            isCuboidClicked: () => cuboidClicked,
            resetCuboidClicked: () => (cuboidClicked = false)
        });
    });
</script>

{#each renderCuboids as item (item.annotation.id)}
    {@const base = resolveCuboidColor(annotationClasses, item.annotation.annotationClassId)}
    {@const isSelected = selectedAnnotationId === item.annotation.id}
    {@const isHovered = hoveredAnnotationId === item.annotation.id}
    {@const color = highlightCuboidColor(base, isSelected, isHovered)}
    <T.Group position={[...item.annotation.center]} quaternion={[...item.annotation.rotation]}>
        <CuboidVisual
            {item}
            baseColor={base}
            edgeColor={color}
            {isHovered}
            {isSelected}
            onhit={onCuboidHit}
            onhoverenter={onCuboidHoverEnter}
            onhoverleave={onCuboidHoverLeave}
        />
        {#if isSelected}
            <CuboidGizmo />
        {/if}
    </T.Group>
{/each}
