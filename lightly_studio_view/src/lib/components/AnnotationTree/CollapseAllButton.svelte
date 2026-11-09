<script lang="ts">
    import { ChevronsDownUp, ChevronsUpDown } from '@lucide/svelte';

    interface Props {
        anyOpen: boolean;
        onToggle: (open: boolean) => void;
    }

    let { anyOpen, onToggle }: Props = $props();

    const label = $derived(anyOpen ? 'Collapse all' : 'Expand all');
</script>

<button
    type="button"
    aria-label={label}
    title={label}
    class="flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    onclick={() => onToggle(!anyOpen)}
>
    {#if anyOpen}
        <ChevronsDownUp class="size-4" aria-hidden="true" />
    {:else}
        <ChevronsUpDown class="size-4" aria-hidden="true" />
    {/if}
</button>
