<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import { throttle } from 'lodash-es';
    import { Grid3x3, Image } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    const { min = 1, max = 12 } = $props();

    const { updateSampleSize, sampleSize } = useGlobalStorage();

    const width = $derived($sampleSize.width);

    const handleChange = throttle((values: number[]) => {
        updateSampleSize(values[0]);
    }, 100);
</script>

<div class="w-300 flex space-x-4 text-diffuse-foreground">
    <!-- Control to change image size -->
    <Image class="h-6 w-6" />

    <Slider
        type="multiple"
        class="w-full flex-1"
        value={[width]}
        {min}
        {max}
        step={1}
        onValueChange={handleChange}
    />
    <Grid3x3 class="h-6 w-6" />
</div>
