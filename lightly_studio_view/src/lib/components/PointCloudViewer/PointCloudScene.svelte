<script lang="ts">
    import { T } from '@threlte/core';
    import type { PerspectiveCamera, OrthographicCamera } from 'three';
    import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudPoints from './PointCloudPoints/PointCloudPoints.svelte';
    import SceneCamera from './SceneCamera/SceneCamera.svelte';
    import type { PointCloudSceneProps } from './pointCloudSceneProps';
    import { useSceneCameraNavigation } from './useSceneCameraNavigation/useSceneCameraNavigation.svelte';
    let {
        batch,
        colorMode = 'none',
        pointSize = 2,
        intensityRange,
        fitKey = '',
        activeTool = 'select',
        cameraMode = 'perspective',
        isScaleSource = false,
        isActive,
        navigationId,
        viewState = null,
        onViewStateChange
    }: PointCloudSceneProps = $props();

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
    {colorMode}
    {pointSize}
    {intensityRange}
    {fitKey}
    camera={activeCamera}
    controls={controlsRef}
    {cameraMode}
    {isScaleSource}
    {viewState}
    {onViewStateChange}
/>
