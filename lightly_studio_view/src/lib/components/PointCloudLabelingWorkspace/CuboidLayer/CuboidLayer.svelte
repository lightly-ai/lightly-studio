<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type { Object3D } from 'three';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { GroundPlaneClickTarget } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidHoverTracker } from './cuboidHoverTracker';
    import { createPendingSizesTracker } from './cuboidPendingSizes';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners } from './cuboidSelection';
    import {
        GIZMO_MODES,
        buildCuboidTransformPayload,
        captureTransformSnapshot,
        restoreTransformSnapshot
    } from './cuboidTransform';
    import type { useUpdateCuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/useUpdateCuboidAnnotation';

    interactivity();

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
    }: {
        cuboids: readonly Domain.CuboidAnnotation[];
        annotationClasses: readonly Domain.AnnotationClass[];
        selectedAnnotationId?: string | null;
        hoveredAnnotationId?: string | null;
        activeTool?: Domain.WorkspaceTool;
        groundPlaneBounds: Domain.Bounds3;
        onselect?: (annotationId: string | null) => void;
        onhover?: (annotationId: string | null, handle: Domain.CuboidHandle | null) => void;
        onCreateCuboid?: (position: Domain.Vector3) => void;
        onCuboidTransform?: ReturnType<typeof useUpdateCuboidAnnotation>['handleCuboidTransform'];
    } = $props();

    const { renderer } = useThrelte();
    let renderCuboids = $state<ReturnType<typeof createCuboidRenderItems>>([]);
    const pendingSizes = createPendingSizesTracker();
    const hoverTracker = createCuboidHoverTracker((id, handle) => onhover?.(id, handle));
    const transformVersions = new Map<string, number>();

    async function handleTransformEnd(
        ann: Domain.CuboidAnnotation,
        obj: Object3D,
        snapshot: ReturnType<typeof captureTransformSnapshot>
    ): Promise<void> {
        const payload = buildCuboidTransformPayload(ann, obj, pendingSizes.get(ann.id));
        pendingSizes.set(ann.id, payload.size);
        const version = (transformVersions.get(ann.id) ?? 0) + 1;
        transformVersions.set(ann.id, version);
        const success = await onCuboidTransform?.(payload);
        if (success === false && transformVersions.get(ann.id) === version) {
            pendingSizes.delete(ann.id);
            restoreTransformSnapshot(obj, snapshot);
        }
    }

    $effect(() => {
        hoverTracker.clear();
        onhover?.(null, null);
        pendingSizes.reconcile(cuboids);
        const next = createCuboidRenderItems(cuboids);
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
    <GroundPlaneClickTarget bounds={groundPlaneBounds} onclick={(p) => onCreateCuboid?.(p)} />
{/if}

{#each renderCuboids as item (item.annotation.id)}
    {@const base = resolveCuboidColor(annotationClasses, item.annotation.annotationClassId)}
    {@const isSelected = selectedAnnotationId === item.annotation.id}
    {@const isHovered = hoveredAnnotationId === item.annotation.id}
    {@const gizmoMode = GIZMO_MODES[activeTool]}
    <T.Group position={[...item.annotation.center]} quaternion={[...item.annotation.rotation]}>
        <CuboidVisual
            {item}
            baseColor={base}
            edgeColor={highlightCuboidColor(base, isSelected, isHovered)}
            {isHovered}
            {isSelected}
            onhit={(id, vol) => {
                hoverTracker.markClicked();
                if (activeTool === 'select' && onselect) hoverTracker.hit(id, vol, onselect);
            }}
            onhoverenter={(id, vol) => hoverTracker.enter(id, vol)}
            onhoverleave={(id) => hoverTracker.leave(id)}
        />
        {#if isSelected && gizmoMode}
            <CuboidGizmo
                mode={gizmoMode}
                onTransformEnd={(obj, snapshot) => handleTransformEnd(item.annotation, obj, snapshot)}
                onInteractionStart={() => hoverTracker.markClicked()}
            />
        {/if}
    </T.Group>
{/each}
