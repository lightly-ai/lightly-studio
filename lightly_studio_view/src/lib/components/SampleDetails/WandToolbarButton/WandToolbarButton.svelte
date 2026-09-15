<script lang="ts">
    import { WandSparkles } from '@lucide/svelte';

    interface Props {
        onclick: () => void;
        isActive?: boolean;
    }

    let { onclick, isActive = false }: Props = $props();
</script>

<button
    type="button"
    {onclick}
    aria-label="Smart select"
    class="flex items-center justify-center rounded-md p-2 transition-colors hover:bg-black/20"
>
    <WandSparkles class={`size-4 ${isActive ? 'text-primary' : ''}`} />
</button>
