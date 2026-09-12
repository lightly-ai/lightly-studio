<script lang="ts">
    import type { Snippet } from 'svelte';

    // Bindable so `bind:brightness` and `bind:contrast` work on the ImageAdjustments stub.
    let {
        brightness = $bindable(0),
        contrast = $bindable(0),
        children
    }: {
        brightness?: number;
        contrast?: number;
        children?: Snippet;
        [key: string]: unknown;
    } = $props();
</script>

{@render children?.()}
