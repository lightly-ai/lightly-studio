<script lang="ts">
    import { T } from '@threlte/core';
    import { Vector3 } from 'three';

    /**
     * Origin indicator of the scene frame: one arrow per axis from (0, 0, 0).
     *
     * The arrows use the usual colors: x is red, y is green, and z is blue.
     */
    interface Props {
        /** Arrow length, in meters. */
        length?: number;
    }

    let { length = 2 }: Props = $props();

    const ORIGIN = new Vector3(0, 0, 0);
    const AXES = [
        { direction: new Vector3(1, 0, 0), color: '#ef4444' },
        { direction: new Vector3(0, 1, 0), color: '#22c55e' },
        { direction: new Vector3(0, 0, 1), color: '#3b82f6' }
    ];

    const headLength = $derived(length * 0.2);
    const headWidth = $derived(length * 0.1);
</script>

{#each AXES as axis (axis.color)}
    <T.ArrowHelper args={[axis.direction, ORIGIN, length, axis.color, headLength, headWidth]} />
{/each}
