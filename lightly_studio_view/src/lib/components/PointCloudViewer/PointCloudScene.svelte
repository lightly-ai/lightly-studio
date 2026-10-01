<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { untrack } from 'svelte';
    import * as THREE from 'three';
    import { fitCameraToBounds } from './pointCloudCamera';
    import { createPointCloudBuffer } from './pointCloudBuffer';
    import {
        listenToSceneNavigation,
        type SceneNavigationAction
    } from './sceneNavigation';
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
    const pointCloudBuffer = createPointCloudBuffer();
    let hasFitted = false;
    let navigationFrame: number | undefined;
    let navigationDamping = true;
    let lastContinuousNavigationTime = 0;
    const continuousNavigation = new Set<SceneNavigationAction>();

    function animateContinuousNavigation(now: number) {
        if (continuousNavigation.size === 0) {
            navigationFrame = undefined;
            if (controlsRef) controlsRef.enableDamping = navigationDamping;
            return;
        }

        const camera = cameraRef;
        const controls = controlsRef;
        if (!camera || !controls) return;

        const delta = Math.min((now - lastContinuousNavigationTime) / 1000, 0.05);
        lastContinuousNavigationTime = now;
        const direction = controls.target.clone().sub(camera.position);
        direction.z = 0;
        direction.normalize();
        const right = direction.clone().cross(new THREE.Vector3(0, 0, 1)).normalize();
        const move = new THREE.Vector3();

        if (continuousNavigation.has('forward')) move.add(direction);
        if (continuousNavigation.has('backward')) move.sub(direction);
        if (continuousNavigation.has('right')) move.add(right);
        if (continuousNavigation.has('left')) move.sub(right);
        move.multiplyScalar(camera.position.distanceTo(controls.target) * 0.85 * delta);
        camera.position.add(move);
        controls.target.add(move);

        const rotateLeft = continuousNavigation.has('rotate-left');
        const rotateRight = continuousNavigation.has('rotate-right');
        if (rotateLeft !== rotateRight) {
            const spherical = new THREE.Spherical().setFromVector3(
                camera.position.clone().sub(controls.target)
            );
            spherical.theta += (rotateLeft ? 1 : -1) * 0.9 * delta;
            camera.position
                .copy(controls.target)
                .add(new THREE.Vector3().setFromSpherical(spherical));
        }

        controls.update();
        invalidate();
        navigationFrame = requestAnimationFrame(animateContinuousNavigation);
    }

    function animateNavigation(
        camera: THREE.PerspectiveCamera,
        controls: ThreeOrbitControls,
        targetPosition: THREE.Vector3,
        targetCenter: THREE.Vector3
    ) {
        if (navigationFrame === undefined) navigationDamping = controls.enableDamping;
        else cancelAnimationFrame(navigationFrame);

        controls.enableDamping = false;
        const startPosition = camera.position.clone();
        const startCenter = controls.target.clone();
        const startedAt = performance.now();
        const duration = 180;

        const animate = (now: number) => {
            const progress = Math.min((now - startedAt) / duration, 1);
            const eased = 1 - (1 - progress) ** 3;
            camera.position.lerpVectors(startPosition, targetPosition, eased);
            controls.target.lerpVectors(startCenter, targetCenter, eased);
            controls.update();
            invalidate();

            if (progress < 1) {
                navigationFrame = requestAnimationFrame(animate);
                return;
            }
            navigationFrame = undefined;
            controls.enableDamping = navigationDamping;
        };

        navigationFrame = requestAnimationFrame(animate);
    }

    function cancelNavigationAnimation() {
        continuousNavigation.clear();
        if (navigationFrame === undefined) return;
        cancelAnimationFrame(navigationFrame);
        navigationFrame = undefined;
        if (controlsRef) controlsRef.enableDamping = navigationDamping;
    }

    $effect(() =>
        listenToSceneNavigation(({ action, phase }) => {
            const camera = cameraRef;
            const controls = controlsRef;
            if (!camera || !controls) return;

            if (phase === 'start') {
                if (navigationFrame === undefined) navigationDamping = controls.enableDamping;
                else cancelAnimationFrame(navigationFrame);
                continuousNavigation.add(action);
                controls.enableDamping = false;
                lastContinuousNavigationTime = performance.now();
                navigationFrame = requestAnimationFrame(animateContinuousNavigation);
                return;
            }
            if (phase === 'stop') {
                continuousNavigation.delete(action);
                return;
            }

            const targetPosition = camera.position.clone();
            const targetCenter = controls.target.clone();

            if (
                action === 'forward' ||
                action === 'backward' ||
                action === 'left' ||
                action === 'right'
            ) {
                const direction = targetCenter.clone().sub(targetPosition);
                direction.z = 0;
                direction.normalize();
                const right = direction.clone().cross(new THREE.Vector3(0, 0, 1)).normalize();
                const move =
                    action === 'forward'
                        ? direction
                        : action === 'backward'
                          ? direction.negate()
                          : action === 'left'
                            ? right.negate()
                            : right;
                move.multiplyScalar(targetPosition.distanceTo(targetCenter) * 0.08);
                targetPosition.add(move);
                targetCenter.add(move);
            } else {
                const offset = targetPosition.clone().sub(targetCenter);
                const spherical = new THREE.Spherical().setFromVector3(offset);
                const step = 0.12;
                spherical.theta += action === 'rotate-left' ? step : -step;
                targetPosition
                    .copy(targetCenter)
                    .add(new THREE.Vector3().setFromSpherical(spherical));
            }
            animateNavigation(camera, controls, targetPosition, targetCenter);
        })
    );

    $effect(() => {
        const canvas = renderer.domElement;

        // Suppress browser context menu so right-drag rotate works uninterrupted.
        const suppress = (e: Event) => e.preventDefault();
        const interruptNavigation = () => cancelNavigationAnimation();
        canvas.addEventListener('contextmenu', suppress);
        canvas.addEventListener('pointerdown', interruptNavigation);

        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            canvas.removeEventListener('pointerdown', interruptNavigation);
            cancelNavigationAnimation();
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
            LEFT: THREE.MOUSE.ROTATE,
            MIDDLE: THREE.MOUSE.DOLLY,
            RIGHT: THREE.MOUSE.PAN
        }}
        touches={{ ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE }}
    />
</T.PerspectiveCamera>

<T.AmbientLight intensity={1} />

<T.Points geometry={pointCloudBuffer.geometry}>
    <T.PointsMaterial vertexColors size={pointSize} sizeAttenuation={false} />
</T.Points>
