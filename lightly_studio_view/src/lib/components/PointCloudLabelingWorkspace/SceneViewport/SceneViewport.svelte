<script lang="ts">
    import { Canvas } from '@threlte/core';
    import PointCloudScene from '../../PointCloudViewer/PointCloudScene.svelte';
    import type { ColorMode } from '../../PointCloudViewer/pointCloudUtils';
    import type { PointBatch } from '../../PointCloudViewer/pointCloudBuffer';
    import CuboidLayer from '../CuboidLayer/CuboidLayer.svelte';
    import type { AnnotationClass, Bounds3, CuboidAnnotation } from '../domain';

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
        pointCloudBounds = EMPTY_BOUNDS
    }: Props = $props();
</script>

<div class="h-full w-full" data-testid="workspace-scene-viewport">
    <Canvas>
        <PointCloudScene {batch} {colorMode} {pointSize} {intensityRange} />
        <CuboidLayer {cuboids} {annotationClasses} {pointCloudBounds} />
    </Canvas>
</div>
