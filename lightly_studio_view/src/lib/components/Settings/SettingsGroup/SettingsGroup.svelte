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
        <h3 class="border-b border-foreground/30 pb-2 text-sm font-semibold text-foreground">
            {title}
        </h3>
    {/if}
    <div
        class={cn(
            '[&>*:first-child]:border-t-0 [&>*]:border-t [&>*]:border-border/40',
            columns === 2 && 'sm:grid sm:grid-cols-2 sm:gap-x-10 sm:[&>*:nth-child(2)]:border-t-0'
        )}
    >
        {@render children()}
    </div>
</section>
