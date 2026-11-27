<script lang="ts">
    import { T } from '@threlte/core';
    import { HTML } from '@threlte/extras';
    import { BufferGeometry, Float32BufferAttribute, Vector3 as ThreeVector3 } from 'three';
    import type { Vector3 } from '../domain';
    import { formatDistance } from './egoRange';
    import { getEgoDistanceLine } from './getEgoDistanceLine';

    interface Props {
        egoPosition: Vector3;
        target: Vector3;
    }

    let { egoPosition, target }: Props = $props();

    const LINE_COLOR = '#f59e0b';
    const DASH_SIZE = 0.5;
    const GAP_SIZE = 0.3;

    const line = $derived(getEgoDistanceLine(egoPosition, target));
    const geometry = $derived.by(() => {
        const geometry = new BufferGeometry().setFromPoints([
            new ThreeVector3(...line.start),
            new ThreeVector3(...line.end)
        ]);
        // Dashes need the distance along the line at each point.
        geometry.setAttribute('lineDistance', new Float32BufferAttribute([0, line.length], 1));
        return geometry;
    });

    $effect(() => {
        const current = geometry;
        return () => current.dispose();
    });
</script>

<!-- Not pickable, so it never blocks a click on a cuboid. -->
<T.Line {geometry} raycast={() => null}>
    <T.LineDashedMaterial color={LINE_COLOR} dashSize={DASH_SIZE} gapSize={GAP_SIZE} />
</T.Line>
<HTML position={[...line.labelPosition]} center pointerEvents="none">
    <span
        class="whitespace-nowrap rounded bg-background/80 px-1.5 py-0.5 text-xs tabular-nums text-amber-400"
        data-testid="ego-distance-label">{formatDistance(line.meters)}</span
    >
</HTML>
