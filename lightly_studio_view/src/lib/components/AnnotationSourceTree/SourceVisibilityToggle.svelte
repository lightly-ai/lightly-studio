<script lang="ts">
    import { Eye, EyeOff } from '@lucide/svelte';
    import { Tooltip } from '$lib/components/ui/tooltip';

    interface Props {
        isHidden: boolean;
        sourceName: string;
        onToggle: () => void;
    }

    let { isHidden, sourceName, onToggle }: Props = $props();
</script>

<Tooltip content={isHidden ? 'Show annotation source' : 'Hide annotation source'}>
    <button
        type="button"
        aria-label="{isHidden ? 'Show' : 'Hide'} annotation source {sourceName}"
        data-testid="source-visibility-toggle"
        class="flex shrink-0 items-center {isHidden
            ? ''
            : 'opacity-0 focus:opacity-100 group-hover:opacity-100'}"
        onclick={onToggle}
    >
        {#if isHidden}
            <EyeOff class="size-4 text-muted-foreground" />
        {:else}
            <Eye class="size-4" />
        {/if}
    </button>
</Tooltip>
