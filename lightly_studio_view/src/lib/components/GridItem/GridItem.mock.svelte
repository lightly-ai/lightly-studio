<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        children?: Snippet;
        dataTestId?: string;
        onSelect?: (event: MouseEvent | KeyboardEvent) => void;
        [key: string]: unknown;
    }

    let { children, dataTestId, onSelect }: Props = $props();
</script>

<div
    data-testid={dataTestId}
    onclick={(e) => onSelect?.(e)}
    onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect?.(e)}
    role="button"
    tabindex="0"
>
    {#if children}
        {@render children()}
    {/if}
</div>
