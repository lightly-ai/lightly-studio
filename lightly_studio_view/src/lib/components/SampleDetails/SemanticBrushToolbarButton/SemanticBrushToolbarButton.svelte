<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { PenLine } from '@lucide/svelte';

    type Props = { onclick: () => void; isActive?: boolean; ariaLabel?: string };

    const {
        onclick,
        isActive = undefined,
        ariaLabel = 'Semantic Segmentation Brush'
    }: Props = $props();

    let { context: sampleDetailsToolbarContext } = useSampleDetailsToolbarContext();

    const isFocused = $derived(
        isActive !== undefined ? isActive : sampleDetailsToolbarContext.status === 'brush'
    );
</script>

<button
    type="button"
    {onclick}
    aria-label={ariaLabel}
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <PenLine
        class={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
