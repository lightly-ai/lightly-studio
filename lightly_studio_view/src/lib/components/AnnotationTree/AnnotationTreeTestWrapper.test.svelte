<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import AnnotationTree from './AnnotationTree.svelte';

    interface Props {
        client: QueryClient;
        collectionId: string;
    }

    let { client, collectionId }: Props = $props();

    setQueryClientContext(untrack(() => client));
</script>

<AnnotationTree {collectionId} />
