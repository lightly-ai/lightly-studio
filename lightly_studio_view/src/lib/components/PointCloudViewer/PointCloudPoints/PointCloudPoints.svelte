<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { onDestroy, untrack } from 'svelte';
    import { createPointCloudBuffer } from '../pointCloudBuffer';
    import type { PointCloudPointsProps } from './pointCloudPointsProps';
    import { usePointCloudCamera } from './usePointCloudCamera/usePointCloudCamera.svelte';
    let {
        batch,
        colorMode,
        pointSize,
        intensityRange,
        fitKey = '',
        camera,
        controls,
        cameraMode = 'perspective',
        isScaleSource = false,
        viewState = null,
        onViewStateChange
    }: PointCloudPointsProps = $props();

    const { invalidate } = useThrelte();
    const pointCloudBuffer = createPointCloudBuffer();
    onDestroy(() => pointCloudBuffer.dispose());
    const cameraSync = usePointCloudCamera(() => ({
        camera,
        controls,
        fitKey,
        cameraMode,
        isScaleSource,
        viewState,
        onViewStateChange
    }));
    $effect(() => {
        const currentBatch = batch;
        void camera;
        void controls;
        void fitKey;
        untrack(() => {
            cameraSync.updateBounds(pointCloudBuffer.updatePositions(currentBatch));
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
