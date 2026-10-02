<script lang="ts">
    import { Canvas } from '@threlte/core';
    import { PointCloudScene } from '$lib/components/PointCloudViewer';
    import type { ColorMode, PointBatch, PointHighlight } from '$lib/components/PointCloudViewer';
    import { computePointsInsideCuboid } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidGeometry';
    import {
        highlightCuboidColor,
        resolveCuboidColor
    } from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/cuboidColors';
    import CuboidLayer from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidLayer.svelte';
    import CuboidTooltipOverlay from '$lib/components/PointCloudLabelingWorkspace/CuboidLayer/CuboidTooltip/CuboidTooltipOverlay.svelte';
    import GroundGrid from './GroundGrid/GroundGrid.svelte';
    import OriginAxes from './OriginAxes/OriginAxes.svelte';
    import type {
        AnnotationClass,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';

    /** Composes the shared Threlte scene from the point cloud, ground grid, origin axes, and annotation layers. */
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

    // The points inside the selected cuboid take its selected edge color, so they stand out.
    const highlight = $derived.by((): PointHighlight | undefined => {
        const selected = cuboids.find((cuboid) => cuboid.id === selectedAnnotationId);
        // DEBUG(cuboid-highlight): remove once the highlight is verified.
        console.debug('[cuboid-highlight] selection', {
            selectedAnnotationId,
            cuboidIds: cuboids.map((cuboid) => cuboid.id),
            found: Boolean(selected),
            pointCount: batch.count
        });
        if (!selected) return undefined;
        const color = highlightCuboidColor(
            resolveCuboidColor(annotationClasses, selected.annotationClassId),
            true,
            false
        );
        const mask = computePointsInsideCuboid(batch.positions, batch.count, selected);
        const insideCount = mask.reduce((total, inside) => total + inside, 0);
        console.debug('[cuboid-highlight] points inside', {
            id: selected.id,
            center: selected.center,
            size: selected.size,
            rotation: selected.rotation,
            insideCount,
            pointCount: batch.count,
            firstPoint: Array.from(batch.positions.subarray(0, 3)),
            color: [color.r, color.g, color.b]
        });
        return { mask, color: [color.r, color.g, color.b] };
    });

    let cursorX = $state(0);
    let cursorY = $state(0);

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
>
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} {highlight} />
        <GroundGrid />
        <OriginAxes />
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
    <CuboidTooltipOverlay {cursorX} {cursorY} {hoveredAnnotationId} {cuboids} {annotationClasses} />
</div>
