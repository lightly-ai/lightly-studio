<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type { Object3D } from 'three';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { GroundPlaneClickTarget } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import { CuboidFaceResize } from './CuboidFaceResize';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners, pickSmallestFromIntersections } from './cuboidSelection';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';

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
        /** Retained bounds that keep the click plane aligned with the visible ground plane. */
        groundPlaneBounds: Domain.Bounds3;
        /** Fires when the user selects or deselects a cuboid. */
        onselect?: (annotationId: string | null) => void;
        /** Fires when the pointer enters or leaves a cuboid. */
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        /** Fires when the user clicks the ground plane in create-cuboid mode. */
        onCreateCuboid?: (position: Domain.Vector3) => void;
        /** Fires when the user finishes transforming a cuboid via the gizmo. */
        onCuboidTransform?: ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform'];
    }

    let {
        cuboids,
        annotationClasses,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        groundPlaneBounds,
        onselect,
        onhover,
        onCreateCuboid,
        onCuboidTransform
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

    const GIZMO_MODES: Partial<Record<Domain.WorkspaceTool, 'translate' | 'rotate' | 'scale'>> = {
        translate: 'translate',
        rotate: 'rotate'
    };

    function handleTransformEnd(annotation: Domain.CuboidAnnotation, obj: Object3D): void {
        const center: Domain.Vector3 = [obj.position.x, obj.position.y, obj.position.z];
        const q = obj.quaternion;
        const rotation: Domain.Quaternion = [q.x, q.y, q.z, q.w];
        const size: Domain.Vector3 = [
            annotation.size[0] * obj.scale.x,
            annotation.size[1] * obj.scale.y,
            annotation.size[2] * obj.scale.z
        ];
        obj.scale.set(1, 1, 1);
        void onCuboidTransform?.({
            annotationId: annotation.id,
            frameId: annotation.frameId,
            center,
            rotation,
            size
        });
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

{#if activeTool === 'create-cuboid'}
    <GroundPlaneClickTarget
        bounds={groundPlaneBounds}
        onclick={(position) => onCreateCuboid?.(position)}
    />
{/if}

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
            {@const gizmoMode = GIZMO_MODES[activeTool]}
            {#if gizmoMode}
                <CuboidGizmo
                    mode={gizmoMode}
                    onTransformEnd={(obj) => handleTransformEnd(item.annotation, obj)}
                    onInteractionStart={() => (cuboidClicked = true)}
                />
            {/if}
            {#if activeTool === 'resize'}
                <CuboidFaceResize
                    annotation={item.annotation}
                    baseColor={base}
                    onResizeStart={() => (cuboidClicked = true)}
                    onResizeEnd={(payload) => void onCuboidTransform?.(payload)}
                />
            {/if}
        {/if}
    </T.Group>
{/each}
