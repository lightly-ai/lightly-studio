<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudPoints from './PointCloudPoints/PointCloudPoints.svelte';
    import * as THREE from 'three';
    import { createSceneNavigationController } from './sceneNavigationController';
    import type { ColorMode } from './pointCloudUtils';
    import type { PointBatch } from './types';

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
    }

    let { batch, colorMode = 'none', pointSize = 2, intensityRange, fitKey = '' }: Props = $props();

    const BACKGROUND_COLOR = 'hsl(20, 14.3%, 4.1%)';
    const { invalidate, renderer } = useThrelte();
    let cameraRef: THREE.PerspectiveCamera | undefined = $state();
    let controlsRef: ThreeOrbitControls | undefined = $state();

    $effect(() => {
        if (!cameraRef || !controlsRef) return;
        const navigation = createSceneNavigationController({
            camera: cameraRef,
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

<T.PerspectiveCamera
    bind:ref={cameraRef}
    makeDefault
    fov={60}
    near={0.1}
    far={10000}
    up={[0, 0, 1]}
>
    <OrbitControls
        bind:ref={controlsRef}
        enableDamping
        screenSpacePanning={false}
        mouseButtons={{
            LEFT: THREE.MOUSE.ROTATE,
            MIDDLE: THREE.MOUSE.DOLLY,
            RIGHT: THREE.MOUSE.PAN
        }}
        touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE }}
    />
</T.PerspectiveCamera>

<T.AmbientLight intensity={1} />

<PointCloudPoints
    {batch}
    {colorMode}
    {pointSize}
    {intensityRange}
    {fitKey}
    camera={cameraRef}
    controls={controlsRef}
/>
