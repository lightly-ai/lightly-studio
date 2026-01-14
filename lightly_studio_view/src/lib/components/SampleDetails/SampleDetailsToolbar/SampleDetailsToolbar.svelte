<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import { onMount } from 'svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import BrushToolbarButton from '../BrushToolbarButton/BrushToolbarButton.svelte';

    type SampleDetailsToolbar = {
        collectionId: string;
        brushRadius: number;
        isEraser: boolean;
    };

    let {
        brushRadius = $bindable<number>(),
        isEraser = $bindable<boolean>()
    }: SampleDetailsToolbar = $props();

    const sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    onMount(() => {
        sampleDetailsToolbarContext.status = 'none';
    });
</script>

<Card>
    <CardContent>
        <SampleDetailsToolbarTooltip label="Bounding Box Tool">
            <BoundingBoxToolbarButton />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Brush Tool">
            <BrushToolbarButton />
        </SampleDetailsToolbarTooltip>
    </CardContent>
</Card>
