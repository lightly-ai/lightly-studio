<script lang="ts">
    import { Layers3 } from '@lucide/svelte';

    interface Props {
        onclick: () => void;
        isActive?: boolean;
    }

    let { onclick, isActive = false }: Props = $props();
</script>

<button
    type="button"
    {onclick}
    aria-label="Find all instances"
    title="Find all instances"
    class={`flex items-center justify-center rounded-md p-2 transition-colors ${isActive ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Layers3 class={`size-4 ${isActive ? 'text-primary' : ''}`} />
</button>
