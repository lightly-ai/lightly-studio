<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import UseSelectionTagCountsProbe from './UseSelectionTagCountsProbe.svelte';
    import type { SelectionTarget } from '$lib/hooks/useSelectionTarget/useSelectionTarget';

    interface Props {
        client: QueryClient;
        target: SelectionTarget;
    }
    let { client, target }: Props = $props();
</script>

<QueryClientProvider {client}>
    <UseSelectionTagCountsProbe {target} />
</QueryClientProvider>
