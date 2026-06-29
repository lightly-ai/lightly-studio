<script lang="ts">
    import { Pentagon } from '@lucide/svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    type Props = { onclick: () => void };

    const { onclick }: Props = $props();

    const { context: sampleDetailsToolbarContext } = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'polygon');
</script>

<button
    type="button"
    {onclick}
    aria-label="Polygon Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Pentagon
        class={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
