<script lang="ts">
    import { T } from '@threlte/core';
    import { BufferGeometry, Vector3 } from 'three';
    import type { EgoRange } from './egoRange';

    interface Props {
        range: EgoRange;
    }

    let { range }: Props = $props();

    const SEGMENT_COUNT = 128;
    const RING_COLOR = '#f59e0b';

    // Depend on the radius only, so an ego move does not rebuild the geometry.
    const radius = $derived(range.radius);
    const geometry = $derived.by(() => {
        const points = Array.from({ length: SEGMENT_COUNT }, (_, index) => {
            const angle = (index / SEGMENT_COUNT) * Math.PI * 2;
            return new Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
        });
        return new BufferGeometry().setFromPoints(points);
    });

    $effect(() => {
        const current = geometry;
        return () => current.dispose();
    });
</script>

<!-- Not pickable, so it never blocks a click on a cuboid. -->
<T.LineLoop {geometry} position={[...range.position]} raycast={() => null}>
    <T.LineBasicMaterial color={RING_COLOR} />
</T.LineLoop>
