<script lang="ts">
    import { T } from '@threlte/core';
    import CuboidVisual from '../CuboidVisual.svelte';
    import CuboidGizmo from '../CuboidGizmo.svelte';
    import { CuboidFaceResize } from '../CuboidFaceResize';
    import { useCuboidLayerContext } from '../cuboidLayerContext';
    import { highlightCuboidColor, resolveCuboidColor } from '../cuboidColors';
    import { getCuboidGizmoMode, buildCuboidTransformPayload } from '../cuboidTransform';
    import type { createCuboidRenderItems } from '../cuboidRenderItems';
    /** Geometry and annotation metadata for one cuboid instance. */
    interface Props {
        /** Render resources owned by the containing layer. */
        item: ReturnType<typeof createCuboidRenderItems>[number];
    }
    let { item }: Props = $props();
    const getLayer = useCuboidLayerContext();
    const layer = $derived(getLayer());
    const base = $derived(
        resolveCuboidColor(layer.annotationClasses, item.annotation.annotationClassId)
    );
    const isSelected = $derived(layer.selectedAnnotationId === item.annotation.id);
    const isHovered = $derived(layer.hoveredAnnotationId === item.annotation.id);
    const gizmoMode = $derived(getCuboidGizmoMode(layer.activeTool));
</script>

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
            layer.hoverTracker.markClicked();
            if (layer.activeTool === 'select' && layer.onselect)
                layer.hoverTracker.hit(id, vol, layer.onselect);
        }}
        onhoverenter={(id, vol) => layer.hoverTracker.enter(id, vol)}
        onhoverleave={(id) => layer.hoverTracker.leave(id)}
    />
    {#if isSelected}
        {#if gizmoMode}
            <CuboidGizmo
                mode={gizmoMode}
                cameraMode={layer.cameraMode}
                onTransformEnd={(obj) => {
                    const payload = buildCuboidTransformPayload(item.annotation, obj);
                    layer.onCuboidTransform?.(payload);
                    void layer.transforms.commit(payload);
                }}
                onInteractionStart={() => {
                    layer.hoverTracker.markClicked();
                    layer.transforms.begin(item.annotation);
                }}
                onInteractionCancel={() => layer.transforms.cancel(item.annotation.id)}
            />
        {/if}
        {#if layer.activeTool === 'resize'}
            <CuboidFaceResize
                annotation={item.annotation}
                cameraMode={layer.cameraMode}
                baseColor={base}
                onResizeStart={() => {
                    layer.hoverTracker.markClicked();
                    layer.transforms.begin(item.annotation);
                }}
                onResizeCancel={() => layer.transforms.cancel(item.annotation.id)}
                onResizeEnd={(payload) => void layer.transforms.commit(payload)}
            />
        {/if}
    {/if}
</T.Group>
