<script lang="ts">
    import { untrack } from 'svelte';
    import RotationCursor from './RotationCursor/RotationCursor.svelte';
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
        colorMode?: ColorMode;
        pointSize?: number;
        intensityRange?: [number, number];
        /** Static cuboid annotations rendered over the point cloud. */
        cuboids?: readonly CuboidAnnotation[];
        annotationClasses?: readonly AnnotationClass[];
        pointCloudBounds?: Bounds3;
        /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
        fitKey?: string;
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
        fitKey,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        onselect,
        onhover
    }: Props = $props();

    // The ground plane keeps the bounds it was placed with, so it stays put while ticks change.
    // It is placed again only when `fitKey` changes, e.g. for another coordinate frame.
    let groundPlaneBounds = $state<Bounds3>(untrack(() => pointCloudBounds));
    let groundPlaneKey = untrack(() => fitKey);
    $effect(() => {
        const key = fitKey;
        const bounds = pointCloudBounds;
        untrack(() => {
            if (key === groundPlaneKey && !isEmptyBounds(groundPlaneBounds)) return;
            groundPlaneKey = key;
            groundPlaneBounds = bounds;
        });
    });

    let cursorX = $state(0);
    let cursorY = $state(0);
    let viewport: HTMLDivElement | undefined = $state();

    function isEmptyBounds(bounds: Bounds3): boolean {
        return bounds.min.every((value, axis) => value === bounds.max[axis]);
    }

    function handleMouseMove(event: MouseEvent) {
        const rect = (event.currentTarget as HTMLDivElement).getBoundingClientRect();
        cursorX = event.clientX - rect.left;
        cursorY = event.clientY - rect.top;
    }
</script>

<div
    class="relative h-full w-full"
    role="application"
    data-testid="workspace-scene-viewport"
    onmousemove={handleMouseMove}
    bind:this={viewport}
>
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} {fitKey} />
        <GroundPlane pointCloudBounds={groundPlaneBounds} />
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
    <RotationCursor target={viewport} {cursorX} {cursorY} />
    <CuboidTooltipOverlay {cursorX} {cursorY} {hoveredAnnotationId} {cuboids} {annotationClasses} />
</div>
