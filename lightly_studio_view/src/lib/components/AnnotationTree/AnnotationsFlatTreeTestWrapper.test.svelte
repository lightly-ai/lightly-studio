<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useAnnotationsInfinite } from '$lib/hooks/useAnnotationsInfinite/useAnnotationsInfinite';
    import AnnotationTree from './AnnotationTree.svelte';
    import { useTreeAnnotationsFilter } from './useTreeAnnotationsFilter.svelte';

    interface Props {
        client: QueryClient;
        collectionId: string;
        sourceId: string;
    }

    let { client, collectionId, sourceId }: Props = $props();

    setQueryClientContext(untrack(() => client));

    // Mirrors the Annotations grid: the tree filter of the tab's source goes into its request.
    const treeFilter = useTreeAnnotationsFilter(() => ({
        collectionId,
        sourceId,
        enabled: true
    }));
    useAnnotationsInfinite(() => ({
        collection_id: sourceId,
        annotation_pairs: treeFilter.current?.annotation_pairs,
        enabled: treeFilter.ready
    }));
</script>

<AnnotationTree {collectionId} {sourceId} flat />
