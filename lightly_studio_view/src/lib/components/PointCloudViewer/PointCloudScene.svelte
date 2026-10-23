<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudPoints from './PointCloudPoints/PointCloudPoints.svelte';
    import * as THREE from 'three';
    import { createSceneNavigationController } from './sceneNavigationController';
    import type { ColorMode } from './pointCloudUtils';
    import type { PointBatch } from './types';
    import type {
        CameraMode,
        WorkspaceTool
    } from '$lib/components/PointCloudLabelingWorkspace/domain';

    interface Props {
        /** Current point cloud batch with positions, intensities, and count. */
        batch: PointBatch;
        /** How points are colored: by height, intensity, per-point rgb, or neutral gray. */
        colorMode?: ColorMode;
        /** Screen-space point size in pixels. */
        pointSize?: number;
        /** Min/max clamp for intensity-based coloring. */
        intensityRange?: [number, number];
        /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
        fitKey?: string;
        /** Tool that determines whether orbit rotation is enabled. */
        activeTool?: WorkspaceTool;
        cameraMode?: CameraMode;
    }

    let {
        batch,
        colorMode = 'none',
        pointSize = 2,
        intensityRange,
        fitKey = '',
        activeTool = 'select',
        cameraMode = 'perspective'
    }: Props = $props();

    const BACKGROUND_COLOR = 'hsl(20, 14.3%, 4.1%)';
    const { invalidate, renderer } = useThrelte();
    let perspectiveCameraRef: THREE.PerspectiveCamera | undefined = $state();
    let orthographicCameraRef: THREE.OrthographicCamera | undefined = $state();
    const activeCamera = $derived(
        cameraMode === 'perspective' ? perspectiveCameraRef : orthographicCameraRef
    );
    let controlsRef: ThreeOrbitControls | undefined = $state();

    $effect(() => {
        if (!perspectiveCameraRef || !controlsRef || cameraMode !== 'perspective') return;
        const navigation = createSceneNavigationController({
            camera: perspectiveCameraRef,
            controls: controlsRef,
            invalidate
        });
        const canvas = renderer.domElement;
        const suppress = (event: Event) => event.preventDefault();
        canvas.addEventListener('contextmenu', suppress);
        canvas.addEventListener('pointerdown', navigation.cancel);
        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            canvas.removeEventListener('pointerdown', navigation.cancel);
            navigation.dispose();
        };
    });
</script>

<T.Color attach="background" args={[BACKGROUND_COLOR]} />

{#if cameraMode === 'perspective'}
    <T.PerspectiveCamera
        bind:ref={perspectiveCameraRef}
        makeDefault
        fov={60}
        near={0.1}
        far={10000}
        up={[0, 0, 1]}
    >
        <OrbitControls
            bind:ref={controlsRef}
            enableDamping
            enableRotate={activeTool !== 'create-cuboid'}
            screenSpacePanning={false}
            mouseButtons={{
                LEFT: THREE.MOUSE.ROTATE,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN
            }}
            touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE }}
        />
    </T.PerspectiveCamera>
{:else}
    <T.OrthographicCamera
        bind:ref={orthographicCameraRef}
        makeDefault
        left={-1}
        right={1}
        top={1}
        bottom={-1}
        near={0.1}
        far={10000}
        up={cameraMode === 'top' ? [0, 1, 0] : [0, 0, 1]}
    >
        <OrbitControls
            bind:ref={controlsRef}
            enableDamping
            enableRotate={false}
            screenSpacePanning
            mouseButtons={{
                LEFT: THREE.MOUSE.PAN,
                MIDDLE: THREE.MOUSE.DOLLY,
                RIGHT: THREE.MOUSE.PAN
            }}
            touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN }}
        />
    </T.OrthographicCamera>
{/if}

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
/>
