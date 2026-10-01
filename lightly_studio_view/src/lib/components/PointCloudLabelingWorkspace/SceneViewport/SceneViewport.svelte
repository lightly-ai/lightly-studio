<script lang="ts">
    import { onMount } from 'svelte';
    import { Rotate3d } from '@lucide/svelte';
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import type { ColorMode, PointBatch } from '$lib/components/PointCloudViewer';
    import CuboidLayer from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidLayer.svelte';
    import GroundPlane from '$lib/components/PointCloudLabelingWorkspace/GroundPlane/GroundPlane.svelte';
    import CuboidTooltipOverlay from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidTooltip/CuboidTooltipOverlay.svelte';
    import SceneNavigationControls from './SceneNavigationControls.svelte';
    import type {
        AnnotationClass,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';

    /** Composes the shared Threlte scene from the point cloud and annotation layers. */
    interface Props {
        /** Point positions and intensities consumed by the existing renderer. */
        batch?: PointBatch;
        /** Point color mapping mode. */
        colorMode?: ColorMode;
        /** Screen-space point size in pixels. */
        pointSize?: number;
        /** Optional intensity range used by intensity coloring. */
        intensityRange?: [number, number];
        /** Static cuboid annotations rendered over the point cloud. */
        cuboids?: readonly CuboidAnnotation[];
        /** Classes used to color cuboid annotations. */
        annotationClasses?: readonly AnnotationClass[];
        /** Bounds of the displayed point cloud. */
        pointCloudBounds?: Bounds3;
        /** Identity of the currently selected cuboid, or null. */
        selectedAnnotationId?: string | null;
        /** Identity of the currently hovered cuboid, or null. */
        hoveredAnnotationId?: string | null;
        /** Tool that determines whether cuboids can be selected. */
        activeTool?: WorkspaceTool;
        /** Fires when the user selects or deselects a cuboid. */
        onselect?: (annotationId: string | null) => void;
        /** Fires when the pointer enters or leaves a cuboid. */
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
    }

    const EMPTY_BATCH: PointBatch = {
        positions: new Float32Array(0),
        intensities: new Float32Array(0),
        count: 0
    };
    const EMPTY_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

    let {
        batch = EMPTY_BATCH,
        colorMode = 'none',
        pointSize = 2,
        intensityRange,
        cuboids = [],
        annotationClasses = [],
        pointCloudBounds = EMPTY_BOUNDS,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        onselect,
        onhover
    }: Props = $props();

    let cursorX = $state(0);
    let cursorY = $state(0);
    let isRotating = $state(false);

    function handleMouseMove(event: MouseEvent) {
        const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
        cursorX = event.clientX - rect.left;
        cursorY = event.clientY - rect.top;
    }

    function handleMouseDown(event: MouseEvent) {
        if (event.button === 0 && event.target instanceof HTMLCanvasElement) isRotating = true;
    }

    onMount(() => {
        const stopRotating = () => (isRotating = false);
        window.addEventListener('mouseup', stopRotating);
        return () => window.removeEventListener('mouseup', stopRotating);
    });
</script>

<div
    class="relative h-full w-full"
    role="application"
    data-testid="workspace-scene-viewport"
    onmousemove={handleMouseMove}
    onmousedown={handleMouseDown}
    onmouseup={() => (isRotating = false)}
>
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} />
        <GroundPlane {pointCloudBounds} />
        <CuboidLayer
            {cuboids}
            {annotationClasses}
            {pointCloudBounds}
            {selectedAnnotationId}
            {hoveredAnnotationId}
            {activeTool}
            {onselect}
            {onhover}
        />
    </Canvas>
    <SceneNavigationControls />
    {#if isRotating}
        <div
            class="pointer-events-none absolute z-20"
            style={`left: ${cursorX + 14}px; top: ${cursorY + 14}px`}
            aria-hidden="true"
        >
            <Rotate3d class="size-5 text-white drop-shadow" />
        </div>
    {/if}
    <CuboidTooltipOverlay {cursorX} {cursorY} {hoveredAnnotationId} {cuboids} {annotationClasses} />
</div>
