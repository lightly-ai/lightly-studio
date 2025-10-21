<script lang="ts">
    import { Slider } from '$lib/components/ui/slider/index.js';
    import _ from 'lodash';
    import { Grid3x3, Image } from '@lucide/svelte';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    const { min = 100, max = 1500 } = $props();

    const { sampleSize, updateSampleSize } = useGlobalStorage();

    const width = $derived($sampleSize.width);

    const handleChange = _.throttle((values: number[]) => {
        updateSampleSize(values[0]);
    }, 100);
</script>

<div class="w-300 flex space-x-4 text-diffuse-foreground">
    <!-- Control to change image size -->
    <Grid3x3 class="h-6 w-6" />
    <Slider
        class="w-full flex-1"
        value={[width]}
        {min}
        {max}
        step={1}
        onValueChange={handleChange}
    />
    <Image class="h-6 w-6" />
</div>
