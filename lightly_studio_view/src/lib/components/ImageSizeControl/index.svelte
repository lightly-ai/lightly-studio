<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { throttle } from 'lodash-es';
    import { ZoomIn, ZoomOut } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    const { min = 1, max = 12 } = $props();

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

<div class="mx-auto flex max-w-56 items-center space-x-2 text-diffuse-foreground">
    <button
        onclick={zoomOut}
        disabled={width >= max}
        class="flex h-6 w-6 shrink-0 items-center justify-center rounded transition-opacity hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-30"
        aria-label="Zoom out"
    >
        <ZoomOut class="h-4 w-4" />
    </button>

    <Slider
        type="multiple"
        class="w-full flex-1"
        value={[sliderValue]}
        {min}
        {max}
        step={1}
        onValueChange={handleChange}
    />

    <button
        onclick={zoomIn}
        disabled={width <= min}
        class="flex h-6 w-6 shrink-0 items-center justify-center rounded transition-opacity hover:opacity-70 disabled:cursor-not-allowed disabled:opacity-30"
        aria-label="Zoom in"
    >
        <ZoomIn class="h-4 w-4" />
    </button>
</div>
