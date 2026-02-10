<script lang="ts">
    /// <reference types="svelte/elements" />
    import type { SVGAttributes } from 'svelte/elements';

    type SampleAnnotationRectProps = {
        sample: {
            width: number;
            height: number;
        };
        interactionRect?: SVGRectElement | undefined | null;
        cursor: 'auto' | 'crosshair';
        pointerEvents?: 'all' | 'none';
    } & SVGAttributes<SVGRectElement>;

    let {
        sample,
        interactionRect = $bindable<SVGRectElement>(),
        cursor = 'crosshair',
        pointerEvents = 'all',
        onclick,
        onpointermove,
        onpointerleave,
        onpointerdown,
        onpointerup,
        onkeydown
    }: SampleAnnotationRectProps = $props();
</script>

<rect
    bind:this={interactionRect}
    width={sample.width}
    height={sample.height}
    fill="transparent"
    pointer-events={pointerEvents}
    style={`outline: 0; cursor: ${cursor}`}
    tabindex="0"
    role="button"
    {onclick}
    {onpointermove}
    {onpointerleave}
    {onpointerdown}
    {onpointerup}
    {onkeydown}
/>
