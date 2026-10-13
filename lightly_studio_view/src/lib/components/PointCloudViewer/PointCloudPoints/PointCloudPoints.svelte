<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { onDestroy, untrack } from 'svelte';
    import type { PerspectiveCamera } from 'three';
    import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { fitCameraToBounds } from '../pointCloudCamera';
    import { createPointCloudBuffer } from '../pointCloudBuffer';
    import type { ColorMode } from '../pointCloudUtils';
    import type { PointBatch } from '../types';

    interface Props {
        batch: PointBatch;
        colorMode: ColorMode;
        pointSize: number;
        intensityRange?: [number, number];
        /** Refits the camera whenever this changes, e.g. when the coordinate frame changes. */
        fitKey?: string;
        camera?: PerspectiveCamera;
        controls?: OrbitControls;
    }
    let {
        batch,
        colorMode,
        pointSize,
        intensityRange,
        fitKey = '',
        camera,
        controls
    }: Props = $props();
    const { invalidate } = useThrelte();
    const pointCloudBuffer = createPointCloudBuffer();
    let fittedKey: string | undefined;
    onDestroy(() => pointCloudBuffer.dispose());
    // Position effect: copy batch into shared buffers, update draw range and bounds.
    // camera and controls are read in the tracked section so the effect retries the fit
    // once both refs are bound; fittedKey is only updated after the fit is performed.
    // The camera is refitted when fitKey changes, e.g. when the coordinate frame changes.
    $effect(() => {
        const currentBatch = batch;
        const currentCamera = camera;
        const currentControls = controls;
        const currentFitKey = fitKey;
        untrack(() => {
            const bounds = pointCloudBuffer.updatePositions(currentBatch);
            if (fittedKey !== currentFitKey && bounds && currentCamera && currentControls) {
                fitCameraToBounds(currentCamera, currentControls, bounds);
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

<T.Points geometry={pointCloudBuffer.geometry}>
    <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} />
</T.Points>
