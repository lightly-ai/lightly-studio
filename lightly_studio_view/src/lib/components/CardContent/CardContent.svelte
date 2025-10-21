<script lang="ts">
    import { cn } from '$lib/utils';
    import type { Snippet } from 'svelte';
    const {
        children,
        className
    }: {
        children: Snippet;
        className?: string;
    } = $props();
</script>

<div class={cn('p-4', className)}>
    {@render children()}
</div>
