<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { throttle } from 'lodash-es';
    import { ZoomIn, ZoomOut } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        min?: number;
        max?: number;
        compact?: boolean;
    }

    const { min = 1, max = 16, compact = false }: Props = $props();

    const { updateSampleSize, sampleSize } = useGlobalStorage();

    const width = $derived($sampleSize.width);

    // Invert slider so right = fewer columns = bigger images (like Apple Photos).
    const sliderValue = $derived(max - width + min);

    const handleChange = throttle((values: number[]) => {
        updateSampleSize(max - values[0] + min);
    }, 100);

    function zoomOut() {
        const next = Math.min(width + 1, max);
        updateSampleSize(next);
    }

    function zoomIn() {
        const next = Math.max(width - 1, min);
        updateSampleSize(next);
    }
</script>

<div
    class="flex shrink-0 items-center text-diffuse-foreground"
    class:w-28={!compact}
    class:space-x-2={!compact}
    class:space-x-4={compact}
>
    <Tooltip content="Decrease thumbnail size" position="top">
        <button
            onclick={zoomOut}
            disabled={width >= max}
            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
            aria-label="Zoom out"
        >
            <ZoomOut class="size-[13px]" />
        </button>
    </Tooltip>

    {#if !compact}
        <Tooltip content="Adjust thumbnail size" position="top" triggerClass="flex flex-1">
            <Slider
                type="multiple"
                class="w-full flex-1"
                trackClass="data-[orientation='horizontal']:h-1.5"
                thumbClass="size-3.5 border"
                value={[sliderValue]}
                {min}
                {max}
                step={1}
                onValueChange={handleChange}
            />
        </Tooltip>
    {/if}

    <Tooltip content="Increase thumbnail size" position="top">
        <button
            onclick={zoomIn}
            disabled={width <= min}
            class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30"
            aria-label="Zoom in"
        >
            <ZoomIn class="size-[13px]" />
        </button>
    </Tooltip>
</div>
