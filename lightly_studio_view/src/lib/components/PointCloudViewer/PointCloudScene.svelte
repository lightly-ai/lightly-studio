<script lang="ts">
    import { T } from '@threlte/core';
    import type { PerspectiveCamera, OrthographicCamera, Plane } from 'three';
    import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudPoints from './PointCloudPoints/PointCloudPoints.svelte';
    import SceneCamera from './SceneCamera/SceneCamera.svelte';
    import type { ColorMode } from './pointCloudUtils';
    import type { PointBatch } from './types';
    import type {
        CuboidAnnotation,
        CameraMode,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { SceneViewState } from './sceneViewState';
    import { useSceneCameraNavigation } from './useSceneCameraNavigation/useSceneCameraNavigation.svelte';
    interface Props {
        batch: PointBatch;
        clippingPlanes?: Plane[];
        colorMode?: ColorMode;
        pointSize?: number;
        intensityRange?: [number, number];
        fitKey?: string;
        activeTool?: WorkspaceTool;
        cameraMode?: CameraMode;
        cameraCuboid?: CuboidAnnotation;
        isScaleSource?: boolean;
        isActive?: () => boolean;
        navigationId?: symbol;
        viewState?: SceneViewState | null;
        onViewStateChange?: (viewState: SceneViewState) => void;
    }
    let {
        batch,
        clippingPlanes = [],
        colorMode = 'none',
        pointSize = 2,
        intensityRange,
        fitKey = '',
        activeTool = 'select',
        cameraMode = 'perspective',
        cameraCuboid,
        isScaleSource = false,
        isActive,
        navigationId,
        viewState = null,
        onViewStateChange
    }: Props = $props();

    let activeCamera = $state<PerspectiveCamera | OrthographicCamera>();
    let controlsRef = $state<OrbitControls>();
    useSceneCameraNavigation(() => ({
        camera: activeCamera,
        controls: controlsRef,
        isActive,
        navigationId
    }));
</script>

<T.Color attach="background" args={['hsl(20, 14.3%, 4.1%)']} />
<SceneCamera {cameraMode} {activeTool} bind:camera={activeCamera} bind:controls={controlsRef} />
<T.AmbientLight intensity={1} />
<PointCloudPoints
    {batch}
    {clippingPlanes}
    {colorMode}
    {pointSize}
    {intensityRange}
    {fitKey}
    camera={activeCamera}
    controls={controlsRef}
    {cameraMode}
    {cameraCuboid}
    {isScaleSource}
    {viewState}
    {onViewStateChange}
/>
