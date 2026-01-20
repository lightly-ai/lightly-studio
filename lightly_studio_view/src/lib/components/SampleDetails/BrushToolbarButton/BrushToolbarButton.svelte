<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Brush } from '@lucide/svelte';

    type Props = { onclick: () => void };

    const { onclick }: Props = $props();

    let { context: sampleDetailsToolbarContext } = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'brush');
</script>

<button
    type="button"
    {onclick}
    aria-label="Segmentation Mask Brush"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Brush
        class={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
