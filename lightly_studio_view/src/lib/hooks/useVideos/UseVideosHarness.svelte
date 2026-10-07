<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useVideos } from './useVideos.svelte';

    interface Props {
        queryClient: QueryClient;
        getParams: Parameters<typeof useVideos>[0];
        onError: (error: unknown) => void;
    }

    const { queryClient, getParams, onError }: Props = $props();
    setQueryClientContext(untrack(() => queryClient));
    const { query } = useVideos(() => getParams());
    $effect(() => onError(query.error));
</script>
