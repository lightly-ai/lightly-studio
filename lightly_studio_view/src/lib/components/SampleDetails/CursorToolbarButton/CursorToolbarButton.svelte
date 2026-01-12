<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { MousePointer } from '@lucide/svelte';

    const sampleDetailsToolbarContext = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'cursor');
</script>

<button
    type="button"
    onclick={() => {
        sampleDetailsToolbarContext.status = 'cursor';
    }}
    aria-label="Cursor Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <MousePointer
        class={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
