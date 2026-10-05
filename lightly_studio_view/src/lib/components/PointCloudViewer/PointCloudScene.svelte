<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import PointCloudPoints from './PointCloudPoints/PointCloudPoints.svelte';
    import * as THREE from 'three';
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
    }

    let { batch, colorMode = 'none', pointSize = 2, intensityRange }: Props = $props();

    const BACKGROUND_COLOR = 'hsl(20, 14.3%, 4.1%)';
    const { invalidate, renderer } = useThrelte();
    let cameraRef: THREE.PerspectiveCamera | undefined = $state();
    let controlsRef: ThreeOrbitControls | undefined = $state();

    $effect(() => {
        const canvas = renderer.domElement;

        // Suppress browser context menu so right-drag rotate works uninterrupted.
        const suppress = (e: Event) => e.preventDefault();
        canvas.addEventListener('contextmenu', suppress);

        return () => {
            canvas.removeEventListener('contextmenu', suppress);
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
            LEFT: THREE.MOUSE.PAN,
            MIDDLE: THREE.MOUSE.DOLLY,
            RIGHT: THREE.MOUSE.ROTATE
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
    camera={cameraRef}
    controls={controlsRef}
/>
