<script lang="ts">
    import { T, useThrelte } from '@threlte/core';
    import { OrbitControls } from '@threlte/extras';
    import type { OrbitControls as ThreeOrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
    import { untrack } from 'svelte';
    import * as THREE from 'three';
    import { fitCameraToBounds } from './pointCloudCamera';
    import { createPointCloudBuffer } from './pointCloudBuffer';
    import { extractHighlightedPositions } from './pointCloudUtils';
    import type { ColorMode, PointHighlight } from './pointCloudUtils';
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
        /** Points drawn in a single color over the color mode. */
        highlight?: PointHighlight;
        /** Screen-space size of the highlighted points in pixels; defaults to 3x `pointSize`. */
        highlightPointSize?: number;
    }

    let {
        batch,
        colorMode = 'none',
        pointSize = 2,
        intensityRange,
        highlight,
        highlightPointSize
    }: Props = $props();

    const BACKGROUND_COLOR = 'hsl(20, 14.3%, 4.1%)';
    const { invalidate, renderer } = useThrelte();
    let cameraRef: THREE.PerspectiveCamera | undefined = $state();
    let controlsRef: ThreeOrbitControls | undefined = $state();
    const pointCloudBuffer = createPointCloudBuffer();
    let hasFitted = false;
    // The highlighted points are drawn again on top, larger, since one material has one size.
    const highlightGeometry = new THREE.BufferGeometry();
    const highlightColor = $derived(new THREE.Color().setRGB(...(highlight?.color ?? [1, 1, 1])));
    const highlightSize = $derived(highlightPointSize ?? pointSize * 3);

    $effect(() => {
        const canvas = renderer.domElement;

        // Suppress browser context menu so right-drag rotate works uninterrupted.
        const suppress = (e: Event) => e.preventDefault();
        canvas.addEventListener('contextmenu', suppress);

        return () => {
            canvas.removeEventListener('contextmenu', suppress);
            pointCloudBuffer.dispose();
            highlightGeometry.dispose();
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
    // Color effect: rebuild colors when batch, colorMode, intensityRange, or highlight change.
    $effect(() => {
        const currentBatch = batch;
        const mode = colorMode;
        const range = intensityRange;
        const currentColors = currentBatch.colors;
        const currentHighlight = highlight;
        untrack(() => {
            // DEBUG(cuboid-highlight): remove once the highlight is verified.
            console.debug('[cuboid-highlight] scene recolor', {
                count: currentBatch.count,
                colorMode: mode,
                hasHighlight: Boolean(currentHighlight),
                maskLength: currentHighlight?.mask.length
            });
            pointCloudBuffer.updateColors(
                currentBatch.count,
                mode,
                range,
                currentColors,
                currentHighlight
            );
            invalidate();
        });
    });
    // Highlight effect: rebuild the highlighted points when batch or highlight change.
    $effect(() => {
        const currentBatch = batch;
        const currentHighlight = highlight;
        untrack(() => {
            const positions = currentHighlight
                ? extractHighlightedPositions(
                      currentBatch.positions,
                      currentBatch.count,
                      currentHighlight.mask
                  )
                : new Float32Array(0);
            highlightGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            highlightGeometry.computeBoundingSphere();
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

<T.Points geometry={highlightGeometry} visible={Boolean(highlight)}>
    <T.PointsMaterial color={highlightColor} size={highlightSize} sizeAttenuation={false} />
</T.Points>
