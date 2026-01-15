<script lang="ts">
    import VectorSquareIcon from '$lib/components/VectorSquareIcon/VectorSquareIcon.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';

    type Props = { onclick: () => void };

    const { onclick }: Props = $props();

    let { context: sampleDetailsToolbarContext } = useSampleDetailsToolbarContext();

    const isFocused = $derived(sampleDetailsToolbarContext.status === 'bounding-box');
</script>

<button
    type="button"
    {onclick}
    aria-label="Bounding Box Tool"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isFocused ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <VectorSquareIcon
        className={`size-4 transition-colors ${isFocused ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
