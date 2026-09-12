<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        brightness?: number;
        contrast?: number;
        children?: Snippet;
        [key: string]: unknown;
    }

    // ImageAdjustments binds these props.
    let { brightness = $bindable(0), contrast = $bindable(0), children }: Props = $props();
</script>

{@render children?.()}
