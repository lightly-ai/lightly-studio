<script lang="ts">
    import { PaintRoller } from '@lucide/svelte';

    type Props = { onclick: () => void; isActive?: boolean };

    const { onclick, isActive = false }: Props = $props();
</script>

<button
    type="button"
    {onclick}
    aria-label="Semantic Segmentation Brush"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none
                ${isActive ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <PaintRoller
        class={`size-4 transition-colors ${isActive ? 'text-primary' : ''} hover:text-primary`}
    />
</button>
