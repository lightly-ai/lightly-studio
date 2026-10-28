import { useThrelte } from '@threlte/core';
import { untrack } from 'svelte';
import { OrthographicCamera, type Box3 } from 'three';
import type { PointCloudPointsProps } from '../pointCloudPointsProps';
import { fitCameraToBounds, fitCameraToCuboid } from '../../pointCloudCamera';
import {
    applyCameraViewState,
    getCameraWorldUnitsPerPixel,
    type SceneViewState
} from '../../sceneViewState';

/** Owns camera fitting, resize handling, and bidirectional view synchronization. */
export function usePointCloudCamera(
    getOptions: () => Omit<
        PointCloudPointsProps,
        'batch' | 'colorMode' | 'pointSize' | 'intensityRange'
    >
) {
    const { renderer, invalidate } = useThrelte();
    const camera = $derived(getOptions().camera);
    const controls = $derived(getOptions().controls);
    const fitKey = $derived(getOptions().fitKey ?? '');
    const cameraMode = $derived(getOptions().cameraMode ?? 'perspective');
    const cameraCuboid = $derived(getOptions().cameraCuboid);
    // Keep the selection-time camera frame fixed throughout annotation edits.
    const cuboidFrameKey = $derived(
        cameraCuboid ? JSON.stringify([cameraCuboid.id, cameraCuboid.frameId]) : undefined
    );
    const isScaleSource = $derived(getOptions().isScaleSource ?? false);
    const viewState = $derived(getOptions().viewState);
    const onViewStateChange = $derived(getOptions().onViewStateChange);
    let fittedKey: string | undefined;
    let fittedCuboidFrameKey: string | undefined;
    let latestBounds: Box3 | undefined;
    let applyingViewState = false;
    const getViewportAspect = (): number => {
        const { clientWidth, clientHeight } = renderer.domElement;
        return clientHeight > 0 ? clientWidth / clientHeight : 1;
    };

    const fitCamera = () => {
        const { clientWidth, clientHeight } = renderer.domElement;
        if (!latestBounds || !camera || !controls || clientWidth <= 0 || clientHeight <= 0)
            return false;
        applyingViewState = true;
        try {
            if (
                cameraCuboid &&
                cameraMode !== 'perspective' &&
                camera instanceof OrthographicCamera
            ) {
                fitCameraToCuboid(camera, controls, cameraCuboid, cameraMode, getViewportAspect());
            } else {
                fitCameraToBounds(camera, controls, latestBounds, cameraMode, getViewportAspect());
            }
            fittedKey = fitKey;
            fittedCuboidFrameKey = cuboidFrameKey;
        } finally {
            applyingViewState = false;
        }
        return true;
    };

    const refitCameraToViewport = () => {
        if (!latestBounds || !camera || !controls) return;
        const { clientWidth, clientHeight } = renderer.domElement;
        if (clientWidth <= 0 || clientHeight <= 0) return;
        if ((fittedKey !== fitKey || fittedCuboidFrameKey !== cuboidFrameKey) && !fitCamera())
            return;
        if (viewState) applyViewState(viewState);
        else {
            const scale = getCameraWorldUnitsPerPixel(camera, controls.target, clientHeight);
            if (scale)
                applyViewState({ target: controls.target.toArray(), worldUnitsPerPixel: scale });
            if (isScaleSource) publishViewState();
        }
        invalidate();
    };

    const publishViewState = () => {
        if (applyingViewState || !camera || !controls || fittedKey !== fitKey) return;
        const target = controls.target;
        if (!isScaleSource && !viewState) return;
        const worldUnitsPerPixel = getCameraWorldUnitsPerPixel(
            camera,
            target,
            renderer.domElement.clientHeight
        );
        if (worldUnitsPerPixel === undefined) return;
        onViewStateChange?.({
            target: [target.x, target.y, target.z],
            worldUnitsPerPixel
        });
    };

    const applyViewState = (currentViewState: SceneViewState | null | undefined) => {
        if (!currentViewState || !camera || !controls || fittedKey !== fitKey) return;
        const { clientWidth, clientHeight } = renderer.domElement;
        applyingViewState = true;
        try {
            if (
                applyCameraViewState(camera, controls.target, currentViewState, {
                    width: clientWidth,
                    height: clientHeight
                })
            )
                controls.update();
        } finally {
            applyingViewState = false;
        }
        invalidate();
    };

    $effect(() => {
        const currentCamera = camera;
        const currentControls = controls;
        if (!currentCamera || !currentControls) return;

        const handleControlChange = () => {
            if (applyingViewState) return;
            publishViewState();
        };
        currentControls.addEventListener('change', handleControlChange);
        return () => currentControls.removeEventListener('change', handleControlChange);
    });

    $effect(() => {
        if (!cuboidFrameKey || cameraMode === 'perspective' || !camera || !controls) return;
        void fitKey;
        untrack(() => {
            if (fitCamera()) invalidate();
        });
    });

    $effect(() => {
        const currentViewState = viewState;
        applyViewState(currentViewState);
    });

    $effect(() => {
        const canvas = renderer.domElement;
        const resizeObserver = new ResizeObserver(refitCameraToViewport);
        resizeObserver.observe(canvas);
        return () => resizeObserver.disconnect();
    });

    return {
        updateBounds(bounds: Box3 | undefined) {
            latestBounds = bounds;
            if (fittedKey !== fitKey && bounds && camera && controls && fitCamera()) {
                if (viewState) applyViewState(viewState);
                else if (isScaleSource) publishViewState();
            }
        }
    };
}
