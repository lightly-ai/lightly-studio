<script lang="ts">
    import { T, useParentObject3D, useTask, useThrelte } from '@threlte/core';
    import { onDestroy } from 'svelte';
    import { ArrowHelper, OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';
    /** Screen-sized heading indicator anchored to the cuboid's forward face. */
    interface Props {
        /** Local origin of the heading arrow. */
        origin: Vector3;
        /** Annotation class color. */
        color: string;
    }
    let { origin, color }: Props = $props();
    const { camera, invalidate, renderer } = useThrelte();
    const parentObject3D = useParentObject3D();
    // One long-lived arrow, so hover re-renders cannot recreate it at zero length.
    const arrow = new ArrowHelper(new Vector3(1, 0, 0), new Vector3(), 0);
    arrow.raycast = () => {};
    arrow.traverse((child) => {
        child.renderOrder = 999;
        if ('material' in child && child.material && !Array.isArray(child.material)) {
            // Draw over points and the translucent hover fill instead of depth-fighting them.
            Object.assign(child.material, { depthTest: false, depthWrite: false });
        }
    });
    let arrowLength = 0;
    onDestroy(() => arrow.dispose());

    $effect(() => {
        arrow.position.copy(origin);
        arrow.setColor(color);
        invalidate();
    });

    useTask(
        () => {
            const viewportHeight = renderer.domElement.clientHeight;
            const object = parentObject3D.current;
            if (!viewportHeight || !object) return;

            const worldPosition = object.getWorldPosition(new Vector3());
            const activeCamera = camera.current;
            const distance = activeCamera.position.distanceTo(worldPosition);
            const worldUnitsPerPixel =
                activeCamera instanceof OrthographicCamera
                    ? 2 / (activeCamera.zoom * viewportHeight)
                    : (2 *
                          distance *
                          Math.tan(((activeCamera as PerspectiveCamera).fov * Math.PI) / 360)) /
                      viewportHeight;
            const nextArrowLength = Math.max(worldUnitsPerPixel * 32, 0.01);
            if (Math.abs(nextArrowLength - arrowLength) < 1e-6) return;

            arrowLength = nextArrowLength;
            arrow.setLength(nextArrowLength, nextArrowLength * 0.35, nextArrowLength * 0.2);
            invalidate();
        },
        { autoInvalidate: false }
    );
</script>

<T is={arrow} />
