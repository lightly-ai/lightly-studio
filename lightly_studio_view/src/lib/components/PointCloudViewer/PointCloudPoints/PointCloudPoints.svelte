<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { onDestroy, untrack } from 'svelte';
    import { createPointCloudFrameBuffers } from '../createPointCloudFrameBuffers';
    import type { OrthographicCamera, PerspectiveCamera, Plane } from 'three';
    import type { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import type { ColorMode } from '../pointCloudUtils';
    import type { PointBatch } from '../types';
    import type {
        CuboidAnnotation,
        CameraMode
    } from '$lib/components/PointCloudLabelingWorkspace/domain';
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
        cameraCuboid?: CuboidAnnotation;
        isActive?: () => boolean;
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
        cameraCuboid,
        isActive,
        isScaleSource = false,
        viewState = null,
        onViewStateChange
    }: Props = $props();

    const { invalidate, renderer } = useThrelte();
    renderer.localClippingEnabled = true;
    const frameBuffers = createPointCloudFrameBuffers();
    onDestroy(() => frameBuffers.dispose());
    let prepared = $state.raw<ReturnType<typeof frameBuffers.update>>();
    const cameraSync = usePointCloudCamera(() => ({
        camera,
        controls,
        fitKey,
        cameraMode,
        cameraCuboid,
        isActive,
        isScaleSource,
        viewState,
        onViewStateChange
    }));
    $effect(() => {
        const currentBatch = batch;
        const mode = colorMode;
        const range = intensityRange;
        if (!currentBatch.segments) void currentBatch.colors;
        untrack(() => {
            prepared = frameBuffers.update(currentBatch, mode, range);
            invalidate();
        });
    });
    $effect(() => {
        const bounds = prepared?.bounds;
        void camera;
        void controls;
        void fitKey;
        untrack(() => cameraSync.updateBounds(bounds));
    });
</script>

{#each prepared?.geometries ?? [] as geometry (geometry)}
    <T.Points {geometry}>
        <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} {clippingPlanes} />
    </T.Points>
{/each}
