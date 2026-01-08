<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import ResizeBrushButton from '$lib/components/ResizeBrushButton/ResizeBrushButton.svelte';
    import { Eraser } from '@lucide/svelte';
    import SampleDetailsToolbarTooltip from '$lib/components/SampleDetails/SampleDetailsToolbarTooltip/SampleDetailsToolbarTooltip.svelte';
    import BoundingBoxToolbarButton from '../BoundingBoxToolbarButton/BoundingBoxToolbarButton.svelte';

    type SampleDetailsToolbar = {
        collectionId: string;
        brushRadius: number;
        isEraser: boolean;
    };

    let {
        collectionId,
        brushRadius = $bindable<number>(),
        isEraser = $bindable<number>()
    }: SampleDetailsToolbar = $props();
</script>

<Card>
    <CardContent>
        <SampleDetailsToolbarTooltip label="Bounding Box Tool">
            <BoundingBoxToolbarButton />
        </SampleDetailsToolbarTooltip>
        <SampleDetailsToolbarTooltip label="Eraser Tool">
            <button
                type="button"
                aria-label="Toggle eraser"
                onclick={() => (isEraser = !isEraser)}
                class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none 
        ${isEraser ? 'bg-black/40' : 'hover:bg-black/20'}
    `}
            >
                <Eraser
                    class={`
            size-6
            hover:text-primary
            ${isEraser ? 'text-primary' : ''}
        `}
                />
            </button>
        </SampleDetailsToolbarTooltip>

        <SampleDetailsToolbarTooltip label="Resize Tool">
            <ResizeBrushButton bind:value={brushRadius} {collectionId} />
        </SampleDetailsToolbarTooltip>
    </CardContent>
</Card>
