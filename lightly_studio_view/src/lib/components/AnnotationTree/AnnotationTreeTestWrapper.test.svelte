<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useImagesInfinite } from '$lib/hooks/useImagesInfinite/useImagesInfinite';
    import AnnotationTree from './AnnotationTree.svelte';
    import { useTreeAnnotationsFilter } from './useTreeAnnotationsFilter.svelte';

    interface Props {
        client: QueryClient;
        collectionId: string;
    }

    let { client, collectionId }: Props = $props();

    setQueryClientContext(untrack(() => client));

    // Mirrors the Images grid: the tree filter is merged into the images request.
    const treeFilter = useTreeAnnotationsFilter(() => ({ collectionId, enabled: true }));
    useImagesInfinite(
        () => ({
            collection_id: collectionId,
            mode: 'normal',
            filters: { ...treeFilter.current }
        }),
        () => treeFilter.ready
    );
</script>

<AnnotationTree {collectionId} />
<button type="button" onclick={() => treeFilter.onlyClass('car')}>Class bar car</button>
