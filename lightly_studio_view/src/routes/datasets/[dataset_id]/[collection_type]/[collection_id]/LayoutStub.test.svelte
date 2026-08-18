<script lang="ts">
    import type { Snippet } from 'svelte';
    // Generic stub for heavy child components: renders children transparently
    // and accepts (but ignores) all other props.
    let { children }: { children?: Snippet; [key: string]: unknown } = $props();
</script>

{@render children?.()}
