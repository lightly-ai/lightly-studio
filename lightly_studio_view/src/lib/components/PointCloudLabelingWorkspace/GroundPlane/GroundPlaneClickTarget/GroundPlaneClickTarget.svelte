<script lang="ts">
    import { T } from '@threlte/core';
    import { computeGroundPlaneLayout } from '../groundPlaneLayout';

    type Bounds3 = Parameters<typeof computeGroundPlaneLayout>[0];
    type Vector3 = NonNullable<ReturnType<typeof computeGroundPlaneLayout>>['center'];

    interface MeshClickEvent {
        point: { x: number; y: number; z: number };
    }

    /** Invisible ground-plane mesh used to capture click positions for cuboid creation. */
    interface Props {
        /** Retained bounds that keep the click plane aligned with the visible ground plane. */
        bounds: Bounds3;
        /** Fires with the world-space click position when the plane is clicked. */
        onclick: (position: Vector3) => void;
    }

    let { bounds, onclick }: Props = $props();

    const GROUND_PLANE_SIZE_FACTOR = 10;
    const layout = $derived(computeGroundPlaneLayout(bounds));
    const size = $derived(
        layout
            ? Math.max(bounds.max[0] - bounds.min[0], bounds.max[1] - bounds.min[1]) *
                  GROUND_PLANE_SIZE_FACTOR
            : 0
    );
</script>

{#if layout}
    <T.Mesh
        position={[...layout.center]}
        visible={false}
        onclick={(e: MeshClickEvent) => onclick([e.point.x, e.point.y, e.point.z])}
    >
        <T.PlaneGeometry args={[size, size]} />
        <T.MeshBasicMaterial />
    </T.Mesh>
{/if}
