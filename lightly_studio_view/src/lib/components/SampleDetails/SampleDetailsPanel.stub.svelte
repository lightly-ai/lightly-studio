<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { CollectionViewWithCount } from '$lib/api/lightly_studio_local';

    interface Props {
        children?: Snippet;
        /** Rendered like SampleDetailsPanel does, so page tests can check the breadcrumb. */
        breadcrumb?: Snippet<[{ collection: CollectionViewWithCount }]>;
        [key: string]: unknown;
    }

    let { children, breadcrumb }: Props = $props();
</script>

{@render breadcrumb?.({ collection: { name: 'Root collection' } as CollectionViewWithCount })}
{@render children?.()}
