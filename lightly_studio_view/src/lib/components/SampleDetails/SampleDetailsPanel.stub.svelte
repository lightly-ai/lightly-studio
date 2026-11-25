<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        children?: Snippet;
        [key: string]: unknown;
    }

    let { children }: Props = $props();
</script>

{@render children?.()}
