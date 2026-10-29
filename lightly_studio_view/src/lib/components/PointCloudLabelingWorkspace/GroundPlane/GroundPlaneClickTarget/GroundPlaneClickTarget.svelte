<script lang="ts">
    import { T } from '@threlte/core';
    import type { Bounds3, CameraMode, Vector3 } from '../../domain';
    import { getCuboidCreationPlane } from './cuboidCreationPlane';

    /** Defines mesh click event shared by this module. */
    interface MeshClickEvent {
        /** World-space location returned by the placement-plane raycast. */
        point: { x: number; y: number; z: number };
    }

    /** Invisible ground-plane mesh used to capture click positions for cuboid creation. */
    interface Props {
        /** Retained bounds that keep the click plane aligned with the visible ground plane. */
        bounds: Bounds3;
        /** Projection orientation used for rendering and editing. */
        cameraMode?: CameraMode;
        /** Fires with the world-space click position when the plane is clicked. */
        onclick: (position: Vector3) => void;
    }

    let { bounds, onclick, cameraMode = 'perspective' }: Props = $props();
    const layout = $derived(getCuboidCreationPlane(bounds, cameraMode));
</script>

{#if layout}
    <T.Mesh
        position={[...layout.center]}
        rotation={[...layout.rotation]}
        visible={false}
        onclick={(e: MeshClickEvent) => onclick([e.point.x, e.point.y, e.point.z])}
    >
        <T.PlaneGeometry args={[layout.size, layout.size]} />
        <T.MeshBasicMaterial />
    </T.Mesh>
{/if}
