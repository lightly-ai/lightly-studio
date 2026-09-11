<script lang="ts">
    import { Canvas } from '@threlte/core';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudScene from '../../PointCloudViewer/PointCloudScene.svelte';
    import type { ColorMode } from '../../PointCloudViewer/pointCloudUtils';
    import type { PointBatch } from '../../PointCloudViewer/pointCloudBuffer';
    import CuboidLayer from '../CuboidLayer/CuboidLayer.svelte';
    import type {
        AnnotationClass,
        Bounds3,
        CuboidAnnotation,
        CuboidHandle,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { CuboidCreationConfig } from '../CuboidLayer/cuboidCreation';

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
        /** Optional configuration for creating cuboids in the active frame. */
        creation?: CuboidCreationConfig;
        /** Fires when the user selects or deselects a cuboid. */
        onselect?: (annotationId: string | null) => void;
        /** Fires when the pointer enters or leaves a cuboid. */
        onhover?: (annotationId: string | null, handle: CuboidHandle | null) => void;
        /** Fires when a drag ends with the updated cuboid geometry. */
        oncuboidupdate?: (cuboid: CuboidAnnotation) => void;
        /** Fires when the user presses Delete or Backspace with a cuboid selected. */
        oncuboiddelete?: (annotationId: string) => void;
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
        creation,
        onselect,
        onhover,
        oncuboidupdate,
        oncuboiddelete
    }: Props = $props();

    let orbitControlsRef = $state<ThreeOrbitControls | undefined>();
</script>

<div class="h-full w-full" data-testid="workspace-scene-viewport">
    <Canvas>
        <PointCloudScene
            {batch}
            {colorMode}
            {pointSize}
            {intensityRange}
            bind:controlsRef={orbitControlsRef}
        />
        <CuboidLayer
            {cuboids}
            {annotationClasses}
            {pointCloudBounds}
            {selectedAnnotationId}
            {hoveredAnnotationId}
            {activeTool}
            orbitControls={orbitControlsRef}
            {creation}
            {onselect}
            {onhover}
            {oncuboidupdate}
            {oncuboiddelete}
        />
    </Canvas>
</div>
