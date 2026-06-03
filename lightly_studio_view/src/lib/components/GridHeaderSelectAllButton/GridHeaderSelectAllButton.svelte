<script lang="ts">
    import { SquareCheck } from '@lucide/svelte';
    import Button from '../ui/button/button.svelte';

    interface Props {
        onclick: () => Promise<void>;
        compact?: boolean;
    }

    const { onclick, compact = false }: Props = $props();
</script>

<Button
    class="h-8 shrink-0 gap-1.5 px-2 text-diffuse-foreground hover:bg-background hover:text-foreground"
    data-testid="select-all-button"
    variant="ghost"
    aria-label="Select all"
    title="Select all"
    {onclick}
>
    <SquareCheck class="size-4" />
    {#if !compact}
        <span>Select all</span>
    {/if}
</Button>
