<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useEmbeddingPlotStatus } from './useEmbeddingPlotStatus';

    interface Props {
        queryClient: QueryClient;
        getCollectionId: () => string;
        onQuery: (query: ReturnType<typeof useEmbeddingPlotStatus>) => void;
    }

    const { queryClient, getCollectionId, onQuery }: Props = $props();
    setQueryClientContext(untrack(() => queryClient));
    untrack(() => onQuery(useEmbeddingPlotStatus(getCollectionId)));
</script>
