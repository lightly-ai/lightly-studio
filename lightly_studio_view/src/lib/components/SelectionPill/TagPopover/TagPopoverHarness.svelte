<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import TagPopover from './TagPopover.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
    }
    let { client, selectedCount }: Props = $props();
</script>

<QueryClientProvider {client}>
    <TagPopover
        collectionId="c1"
        gridType="images"
        {selectedCount}
        open={true}
        onOpenChange={() => {}}
    />
</QueryClientProvider>
