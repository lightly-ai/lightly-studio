<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { interactivity } from '@threlte/extras';
    import type * as Domain from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { GroundPlaneClickTarget } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import CuboidGizmo from './CuboidGizmo.svelte';
    import { CuboidFaceResize } from './CuboidFaceResize';
    import CuboidVisual from './CuboidVisual.svelte';
    import { highlightCuboidColor, resolveCuboidColor } from './cuboidColors';
    import { createCuboidHoverTracker } from './cuboidHoverTracker';
    import { createCuboidTransformState } from './cuboidTransformState';
    import { createCuboidRenderItems, disposeCuboidRenderItems } from './cuboidRenderItems';
    import { addCuboidSelectionListeners } from './cuboidSelection';
    import { GIZMO_MODES, buildCuboidTransformPayload } from './cuboidTransform';
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
    const transforms = createCuboidTransformState({
        onTransform: (payload) => onCuboidTransform?.(payload)
    });
    const { annotations } = transforms;
    const hoverTracker = createCuboidHoverTracker((id, handle) => onhover?.(id, handle));

    $effect(() => {
        hoverTracker.clear();
        onhover?.(null, null);
        transforms.reconcile(cuboids);
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
    <GroundPlaneClickTarget bounds={groundPlaneBounds} onclick={(p) => onCreateCuboid?.(p)} />
{/if}

{#each renderCuboids as item (item.annotation.id)}
    {@const base = resolveCuboidColor(annotationClasses, item.annotation.annotationClassId)}
    {@const isSelected = selectedAnnotationId === item.annotation.id}
    {@const isHovered = hoveredAnnotationId === item.annotation.id}
    {@const gizmoMode = GIZMO_MODES[activeTool]}
    <T.Group
        position.x={item.annotation.center[0]}
        position.y={item.annotation.center[1]}
        position.z={item.annotation.center[2]}
        quaternion.x={item.annotation.rotation[0]}
        quaternion.y={item.annotation.rotation[1]}
        quaternion.z={item.annotation.rotation[2]}
        quaternion.w={item.annotation.rotation[3]}
    >
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
        {#if isSelected}
            {#if gizmoMode}
                <CuboidGizmo
                    mode={gizmoMode}
                    onTransformEnd={(obj) =>
                        void transforms.commit(buildCuboidTransformPayload(item.annotation, obj))}
                    onInteractionStart={() => {
                        hoverTracker.markClicked();
                        transforms.begin(item.annotation);
                    }}
                    onInteractionCancel={() => transforms.cancel(item.annotation.id)}
                />
            {/if}
            {#if activeTool === 'resize'}
                <CuboidFaceResize
                    annotation={item.annotation}
                    baseColor={base}
                    onResizeStart={() => {
                        hoverTracker.markClicked();
                        transforms.begin(item.annotation);
                    }}
                    onResizeCancel={() => transforms.cancel(item.annotation.id)}
                    onResizeEnd={(payload) => void transforms.commit(payload)}
                />
            {/if}
        {/if}
    </T.Group>
{/each}
