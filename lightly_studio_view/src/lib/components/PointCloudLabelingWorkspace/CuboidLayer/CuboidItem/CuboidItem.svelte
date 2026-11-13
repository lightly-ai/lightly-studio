<script lang="ts">
    import { T } from '@threlte/core';
    import CuboidVisual from '../CuboidVisual.svelte';
    import CuboidGizmo from '../CuboidGizmo.svelte';
    import { CuboidFaceResize } from '../CuboidFaceResize';
    import { useCuboidLayerContext } from '../cuboidLayerContext';
    import { highlightCuboidColor, resolveCuboidColor } from '../cuboidColors';
    import { getCuboidEditModes, buildCuboidTransformPayload } from '../cuboidTransform';
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
    const editModes = $derived(getCuboidEditModes(layer.activeTool, layer.cameraMode));
    const gizmoModes = $derived(
        editModes.filter((mode): mode is 'translate' | 'rotate' => mode !== 'resize')
    );
    let transformStartAnnotation: typeof item.annotation | null = $state(null);
    type GizmoObject = Parameters<typeof buildCuboidTransformPayload>[1];

    function onTransformEnd(obj: GizmoObject) {
        const payload = buildCuboidTransformPayload(
            transformStartAnnotation ?? item.annotation,
            obj
        );
        transformStartAnnotation = null;
        layer.onCuboidTransform?.(payload);
        void layer.transforms.commit(payload);
    }

    function onTransformPreview(obj: GizmoObject) {
        layer.transforms.preview(
            buildCuboidTransformPayload(transformStartAnnotation ?? item.annotation, obj.clone())
        );
    }

    function onInteractionStart() {
        layer.hoverTracker.markClicked();
        transformStartAnnotation = item.annotation;
        layer.transforms.begin(item.annotation);
    }

    function onInteractionCancel() {
        transformStartAnnotation = null;
        layer.transforms.cancel(item.annotation.id);
    }
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
        {#each gizmoModes as mode (mode)}
            <CuboidGizmo
                {mode}
                cameraMode={layer.cameraMode}
                size={item.annotation.size}
                {onTransformEnd}
                {onTransformPreview}
                {onInteractionStart}
                {onInteractionCancel}
            />
        {/each}
        {#if editModes.includes('resize')}
            <CuboidFaceResize
                annotation={item.annotation}
                cameraMode={layer.cameraMode}
                baseColor={base}
                onResizeStart={() => {
                    layer.hoverTracker.markClicked();
                    layer.transforms.begin(item.annotation);
                }}
                onResizeCancel={() => layer.transforms.cancel(item.annotation.id)}
                onResizePreview={(payload) => layer.transforms.preview(payload)}
                onResizeEnd={(payload) => void layer.transforms.commit(payload)}
            />
        {/if}
    {/if}
</T.Group>
