<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useEmbeddings } from './useEmbeddings';

    interface Props {
        queryClient: QueryClient;
        getParams: Parameters<typeof useEmbeddings>[0];
        onQuery: (query: ReturnType<typeof useEmbeddings>) => void;
    }

    const { queryClient, getParams, onQuery }: Props = $props();
    setQueryClientContext(untrack(() => queryClient));
    untrack(() => onQuery(useEmbeddings(getParams)));
</script>
