<script lang="ts">
    import { setQueryClientContext, type QueryClient } from '@tanstack/svelte-query';
    import { untrack } from 'svelte';
    import { useVideos } from './useVideos.svelte';

    interface Props {
        queryClient: QueryClient;
        getParams: Parameters<typeof useVideos>[0];
    }

    const { queryClient, getParams }: Props = $props();
    setQueryClientContext(untrack(() => queryClient));
    useVideos(() => getParams());
</script>
