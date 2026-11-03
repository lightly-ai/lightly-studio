<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import type { GridType } from '$lib/types';
    import SelectionPill from './SelectionPill.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
        onClear: () => void;
        gridType: GridType;
        gridTotal?: number;
        onSelectAll?: () => void;
        canSearchSimilar?: boolean;
    }
    let {
        client,
        selectedCount,
        onClear,
        gridType,
        gridTotal,
        onSelectAll,
        canSearchSimilar
    }: Props = $props();
</script>

<QueryClientProvider {client}>
    <SelectionPill
        {selectedCount}
        {onClear}
        collectionId="c1"
        {gridType}
        {gridTotal}
        {onSelectAll}
        {canSearchSimilar}
    />
</QueryClientProvider>
