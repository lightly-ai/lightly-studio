<script lang="ts">
    import { Slider } from '$lib/components/ui/slider';

    /** Overlay slider that controls the rendered point size in pixels. */
    interface Props {
        value: number;
        min?: number;
        max?: number;
        step?: number;
    }

    let { value = $bindable(), min = 1, max = 10, step = 0.5 }: Props = $props();
</script>

<div
    class="absolute bottom-3 left-3 z-10 flex w-44 items-center gap-2 rounded-md border bg-background/80 px-2 py-1.5 text-xs shadow"
    data-testid="point-size-control"
>
    <span class="whitespace-nowrap">Point size</span>
    <Slider type="single" bind:value {min} {max} {step} aria-label="Point size" />
    <span class="w-6 text-right tabular-nums">{value}</span>
</div>
