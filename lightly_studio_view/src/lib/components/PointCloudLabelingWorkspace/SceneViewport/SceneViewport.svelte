<script lang="ts">
    import { untrack, type ComponentProps } from 'svelte';
    import RotationCursor from './RotationCursor/RotationCursor.svelte';
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import type { ColorMode, PointBatch } from '$lib/components/PointCloudViewer';
    import CuboidLayer from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidLayer.svelte';
    import { GroundPlane } from '$lib/components/PointCloudLabelingWorkspace/GroundPlane';
    import OriginAxes from '$lib/components/PointCloudLabelingWorkspace/OriginAxes/OriginAxes.svelte';
    import CuboidTooltipOverlay from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidTooltip/CuboidTooltipOverlay.svelte';
    import SceneNavigationControls from './SceneNavigationControls.svelte';
    import PointSizeControl from './PointSizeControl/PointSizeControl.svelte';
    import { cn } from '$lib/utils';
    import type {
        AnnotationClass,
        AnnotationSource,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        Vector3,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { createCuboidTransformState } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidTransformState';

    /** Composes the shared Threlte scene from the point cloud and annotation layers. */
    interface Props {
        /** Point positions and intensities consumed by the existing renderer. */
        batch?: PointBatch;
        colorMode?: ColorMode;
        pointSize?: number;
        intensityRange?: [number, number];
        /** Cuboid annotations rendered over the point cloud (typically the transform overlay). */
        cuboids?: readonly CuboidAnnotation[];
        annotationClasses?: readonly AnnotationClass[];
        annotationSources?: readonly AnnotationSource[];
        /** Transform state shared with the parent; drives the gizmo and face-resize interactions. */
        transforms: ReturnType<typeof createCuboidTransformState>;
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
        /** Fires when the user clicks the ground plane in create-cuboid mode. */
        onCreateCuboid?: (position: Vector3) => void;
        /** Fires when the user finishes transforming a cuboid via the gizmo. */
        onCuboidTransform?: ComponentProps<typeof CuboidLayer>['onCuboidTransform'];
        /** Fires on the left arrow key. */
        onPreviousTick?: () => void;
        /** Fires on the right arrow key. */
        onNextTick?: () => void;
    }

    const EMPTY_BATCH: PointBatch = {
        positions: new Float32Array(0),
        intensities: new Float32Array(0),
        count: 0
    };
    const EMPTY_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };
    // `[contenteditable]` also matches `""` and `plaintext-only`, and editable ancestors.
    const IGNORED_KEY_TARGETS =
        'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="slider"]';

    let {
        batch = EMPTY_BATCH,
        colorMode = 'none',
        pointSize = $bindable(2),
        intensityRange,
        cuboids = [],
        annotationClasses = [],
        annotationSources = [],
        transforms,
        pointCloudBounds = EMPTY_BOUNDS,
        fitKey,
        selectedAnnotationId = null,
        hoveredAnnotationId = null,
        activeTool = 'select',
        onselect,
        onhover,
        onCreateCuboid,
        onCuboidTransform,
        onPreviousTick,
        onNextTick
    }: Props = $props();

    $effect(() => {
        const handleKeydown = (event: KeyboardEvent) => {
            if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
            const handler =
                event.key === 'ArrowLeft'
                    ? onPreviousTick
                    : event.key === 'ArrowRight'
                      ? onNextTick
                      : undefined;
            if (!handler) return;
            const target = event.target;
            if (target instanceof HTMLElement && target.closest(IGNORED_KEY_TARGETS)) return;
            event.preventDefault();
            handler();
        };
        window.addEventListener('keydown', handleKeydown);
        return () => window.removeEventListener('keydown', handleKeydown);
    });

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
    class={cn('relative h-full w-full', activeTool === 'create-cuboid' && 'cursor-crosshair')}
    role="application"
    data-testid="workspace-scene-viewport"
    onmousemove={handleMouseMove}
    bind:this={viewport}
>
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} {fitKey} {activeTool} />
        <GroundPlane pointCloudBounds={groundPlaneBounds} />
        <OriginAxes />
        <CuboidLayer
            {cuboids}
            {annotationClasses}
            {transforms}
            {groundPlaneBounds}
            {selectedAnnotationId}
            {hoveredAnnotationId}
            {activeTool}
            {onselect}
            {onhover}
            {onCreateCuboid}
            {onCuboidTransform}
        />
    </Canvas>
    <SceneNavigationControls />
    <PointSizeControl bind:value={pointSize} />
    <RotationCursor target={viewport} {cursorX} {cursorY} />
    <CuboidTooltipOverlay
        {cursorX}
        {cursorY}
        {hoveredAnnotationId}
        {cuboids}
        {annotationClasses}
        {annotationSources}
    />
</div>
