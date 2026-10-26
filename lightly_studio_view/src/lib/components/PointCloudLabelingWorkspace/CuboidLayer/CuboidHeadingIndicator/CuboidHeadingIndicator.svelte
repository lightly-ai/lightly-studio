<script lang="ts">
    import { T, useParentObject3D, useTask, useThrelte } from '@threlte/core';
    import { OrthographicCamera, PerspectiveCamera, Vector3 } from 'three';
    /** Screen-sized heading indicator anchored to the cuboid's forward face. */
    interface Props {
        /** Local origin of the heading arrow. */
        origin: Vector3;
        /** Annotation class color. */
        color: string;
    }
    let { origin, color }: Props = $props();
    const { camera, renderer } = useThrelte();
    const parentObject3D = useParentObject3D();
    let arrowLength = $state(0);

    useTask(() => {
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
        arrowLength = Math.max(worldUnitsPerPixel * 32, 0.01);
    });
</script>

<T.ArrowHelper args={[new Vector3(1, 0, 0), origin, arrowLength, color, 0.35, 0.2]} />
