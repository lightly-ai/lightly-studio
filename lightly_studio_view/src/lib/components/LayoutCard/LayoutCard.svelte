<script lang="ts">
    import type { Snippet } from 'svelte';

    const {
        children,
        className = ''
    }: {
        children: Snippet;
        className?: string;
    } = $props();
</script>

<div class={`h-full w-full space-y-6 rounded-[1vw] bg-card p-4 ${className}`}>
    {@render children()}
</div>
