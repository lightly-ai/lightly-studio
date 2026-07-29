<script lang="ts">
    import type { Snippet } from 'svelte';
    // Generic stub for heavy child components: renders children transparently
    // and accepts (but ignores) all other props.
    // svelte-ignore custom_element_props_identifier
    let { children, ...rest }: { children?: Snippet; [key: string]: unknown } = $props();

    void rest; // Suppress unused-variable warning in tests
</script>

{@render children?.()}
