<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { onDestroy, untrack } from 'svelte';
    import { createPointCloudBuffer } from '../pointCloudBuffer';
    import type { OrthographicCamera, PerspectiveCamera, Plane } from 'three';
    import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import type { ColorMode } from '../pointCloudUtils';
    import type { PointBatch } from '../types';
    import type { CameraMode } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import type { SceneViewState } from '../sceneViewState';
    import { usePointCloudCamera } from './usePointCloudCamera/usePointCloudCamera.svelte';
    interface Props {
        batch: PointBatch;
        clippingPlanes?: Plane[];
        colorMode: ColorMode;
        pointSize: number;
        intensityRange?: [number, number];
        fitKey?: string;
        camera?: PerspectiveCamera | OrthographicCamera;
        controls?: OrbitControls;
        cameraMode?: CameraMode;
        isScaleSource?: boolean;
        viewState?: SceneViewState | null;
        onViewStateChange?: (viewState: SceneViewState) => void;
    }
    let {
        batch,
        clippingPlanes = [],
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
    }: Props = $props();

    const { invalidate, renderer } = useThrelte();
    renderer.localClippingEnabled = true;
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
    <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} {clippingPlanes} />
</T.Points>
