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

<div class={cn('rounded-lg border border-gray-800 bg-black', className)}>
    {@render children()}
</div>
