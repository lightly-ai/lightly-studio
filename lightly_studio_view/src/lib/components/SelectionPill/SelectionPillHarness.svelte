<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import type { GridType } from '$lib/types';
    import SelectionPill from './SelectionPill.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
        onClear: () => void;
        gridType: GridType;
    }
    let { client, selectedCount, onClear, gridType }: Props = $props();
</script>

<QueryClientProvider {client}>
    <SelectionPill {selectedCount} {onClear} collectionId="c1" {gridType} />
</QueryClientProvider>
