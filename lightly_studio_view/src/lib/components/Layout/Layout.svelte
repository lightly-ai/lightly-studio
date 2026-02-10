<script lang="ts">
    import type { Snippet } from 'svelte';

    const { children, header }: { children: Snippet; header?: Snippet } = $props();
</script>

{#if header}
    <div class="flex-none">
        {@render header()}
    </div>
{/if}

<div class="relative flex min-h-0 flex-1 flex-col">
    <div class="flex min-h-0 flex-1 space-x-4 p-4">
        {@render children()}
    </div>
</div>
