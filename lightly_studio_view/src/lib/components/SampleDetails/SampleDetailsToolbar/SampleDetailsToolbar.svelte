<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import ResizeBrushButton from '$lib/components/ResizeBrushButton/ResizeBrushButton.svelte';
    import { Eraser } from '@lucide/svelte';

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
            size-4
            hover:text-primary
            ${isEraser ? 'text-primary' : ''}
        `}
            />
        </button>
        <ResizeBrushButton bind:value={brushRadius} {collectionId} />
    </CardContent>
</Card>
