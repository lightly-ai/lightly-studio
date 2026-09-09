<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { untrack } from 'svelte';
    import * as THREE from 'three';
    import { fitCameraToBounds } from './pointCloudCamera';
    import { createPointCloudBuffer } from './pointCloudBuffer';
    import type { ColorMode } from './pointCloudUtils';
    import type { PointBatch } from './pointCloudBuffer';

    interface Props {
        /** Current point cloud batch with positions, intensities, and count. */
        batch: PointBatch;
        /** How points are colored: by height, intensity, or neutral gray. */
        colorMode?: ColorMode;
        /** Screen-space point size in pixels. */
        pointSize?: number;
        /** Min/max clamp for intensity-based coloring. */
        intensityRange?: [number, number];
    }

    let { batch, colorMode = 'none', pointSize = 2, intensityRange }: Props = $props();

    const BACKGROUND_COLOR = 'hsl(20, 14.3%, 4.1%)';
    const { invalidate } = useThrelte();
    let cameraRef: THREE.PerspectiveCamera | undefined = $state();
    let controlsRef: ThreeOrbitControls | undefined = $state();
    const pointCloudBuffer = createPointCloudBuffer();
    let hasFitted = false;

    $effect(() => {
        return () => {
            pointCloudBuffer.dispose();
        };
    });
    // Position effect: copy batch into shared buffers, update draw range and bounds.
    // cameraRef and controlsRef are read in the tracked section so the effect
    // retries the fit once both refs are bound; hasFitted is only set to true
    // after the fit is actually performed.
    $effect(() => {
        const currentBatch = batch;
        const camera = cameraRef;
        const controls = controlsRef;
        untrack(() => {
            const bounds = pointCloudBuffer.updatePositions(currentBatch);
            if (!hasFitted && bounds && camera && controls) {
                // Point clouds arrive Z-up, which the height color mode assumes too. Set it
                // imperatively rather than as a prop so it is in place before the controls
                // read it and before the first fit.
                camera.up.set(0, 0, 1);
                fitCameraToBounds(camera, controls, bounds);
                hasFitted = true;
            }
            invalidate();
        });
    });
    // Color effect: rebuild colors when batch, colorMode, or intensityRange change.
    $effect(() => {
        const currentBatch = batch;
        const mode = colorMode;
        const range = intensityRange;
        untrack(() => {
            pointCloudBuffer.updateColors(currentBatch.count, mode, range);
            invalidate();
        });
    });
</script>

<T.Color attach="background" args={[BACKGROUND_COLOR]} />

<T.PerspectiveCamera bind:ref={cameraRef} makeDefault fov={60} near={0.1} far={10000}>
    <OrbitControls bind:ref={controlsRef} enableDamping />
</T.PerspectiveCamera>

<T.AmbientLight intensity={1} />

<T.Points geometry={pointCloudBuffer.geometry}>
    <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} />
</T.Points>
