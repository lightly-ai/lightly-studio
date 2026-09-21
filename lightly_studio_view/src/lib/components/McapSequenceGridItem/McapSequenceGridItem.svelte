<script lang="ts">
    import { BoxIcon } from '@lucide/svelte';

    interface Props {
        sampleCount: number;
        width: number;
        height: number;
    }

    let { sampleCount, width, height }: Props = $props();
</script>

<div
    data-testid="mcap-sequence-grid-item"
    class="relative h-full w-full"
    style="width: {width}px; height: {height}px"
>
    <div
        class="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted text-muted-foreground"
    >
        <BoxIcon class="size-10" />
        <span class="text-sm font-medium">MCAP sequence</span>
    </div>
    {#if sampleCount > 1}
        <div
            class="absolute bottom-1 right-1 rounded-sm bg-black/60 px-1.5 py-0.5 text-xs font-bold text-white"
            data-testid="mcap-sequence-frame-count"
        >
            +{sampleCount - 1}
        </div>
    {/if}
</div>
