<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { untrack } from 'svelte';
    import * as THREE from 'three';
    import { fitCameraToBounds } from './pointCloudCamera';
    import { createPointCloudBuffer } from './pointCloudBuffer';
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
    const pointCloudBuffer = createPointCloudBuffer();
    let fittedKey: string | undefined;

    $effect(() => {
        const canvas = renderer.domElement;

        // Suppress browser context menu so right-drag rotate works uninterrupted.
        const suppress = (e: Event) => e.preventDefault();
        canvas.addEventListener('contextmenu', suppress);

        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            pointCloudBuffer.dispose();
        };
    });
    // Position effect: copy batch into shared buffers, update draw range and bounds.
    // cameraRef and controlsRef are read in the tracked section so the effect
    // retries the fit once both refs are bound; fittedKey is only set after the fit is actually
    // performed. The camera is refitted when fitKey changes, since the cloud then moves.
    $effect(() => {
        const currentBatch = batch;
        const camera = cameraRef;
        const controls = controlsRef;
        const currentFitKey = fitKey;
        untrack(() => {
            const bounds = pointCloudBuffer.updatePositions(currentBatch);
            if (fittedKey !== currentFitKey && bounds && camera && controls) {
                fitCameraToBounds(camera, controls, bounds);
                fittedKey = currentFitKey;
            }
            invalidate();
        });
    });
    // Color effect: rebuild colors when batch, colorMode, or intensityRange change.
    $effect(() => {
        const currentBatch = batch;
        const mode = colorMode;
        const range = intensityRange;
        const currentColors = currentBatch.colors;
        untrack(() => {
            pointCloudBuffer.updateColors(currentBatch.count, mode, range, currentColors);
            invalidate();
        });
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

<T.Points geometry={pointCloudBuffer.geometry}>
    <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} />
</T.Points>
