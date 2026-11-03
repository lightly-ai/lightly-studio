<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import type { GridType } from '$lib/types';
    import SelectionPill from './SelectionPill.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
        onClear: () => void;
        gridType: GridType;
        isEditing: boolean;
    }
    let { client, selectedCount, onClear, gridType, isEditing }: Props = $props();
</script>

<QueryClientProvider {client}>
    <SelectionPill {selectedCount} {onClear} collectionId="c1" {gridType} {isEditing} />
</QueryClientProvider>
