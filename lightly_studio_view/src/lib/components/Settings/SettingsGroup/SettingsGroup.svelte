<script lang="ts">
    import type { Snippet } from 'svelte';
    import { cn } from '$lib/utils';

    interface Props {
        title?: string;
        columns?: 1 | 2;
        children: Snippet;
    }

    const { title, columns = 1, children }: Props = $props();
</script>

<section class="space-y-1">
    {#if title}
        <h3 class="text-sm font-medium text-muted-foreground">{title}</h3>
    {/if}
    <div
        class={cn(
            '[&>*]:border-t [&>*]:border-border/60',
            columns === 2
                ? 'grid grid-cols-2 gap-x-10 [&>*:nth-child(-n+2)]:border-t-0'
                : '[&>*:first-child]:border-t-0'
        )}
    >
        {@render children()}
    </div>
</section>
