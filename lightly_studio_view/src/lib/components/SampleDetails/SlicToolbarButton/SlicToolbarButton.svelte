<script lang="ts">
    import { Bot } from '@lucide/svelte';

    interface Props {
        onclick: () => void;
        isActive?: boolean;
    }

    const { onclick, isActive = false }: Props = $props();
</script>

<button
    type="button"
    {onclick}
    aria-pressed={isActive}
    aria-label="AI-Assisted labeling"
    class={`flex
 items-center justify-center rounded-md p-2 transition-colors
        focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
                ${isActive ? 'bg-black/40' : 'hover:bg-black/20'}`}
>
    <Bot class={`size-4 transition-colors ${isActive ? 'text-primary' : ''} hover:text-primary`} />
</button>
