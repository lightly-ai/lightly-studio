<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import type { ImageFilter } from '$lib/api/lightly_studio_local';
    import { useUnannotatedImageCounts } from './useAnnotationPairCounts.svelte';

    interface Props {
        client: QueryClient;
        filter: ImageFilter;
    }

    let { client, filter }: Props = $props();

    setQueryClientContext(untrack(() => client));

    useUnannotatedImageCounts(() => ({ collectionId: 'images', filter }));
</script>
