<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        children: Snippet<[{ footer: Snippet }]>;
        [key: string]: unknown;
    }

    let { children }: Props = $props();
</script>

{#snippet footer()}{/snippet}

{@render children({ footer })}
