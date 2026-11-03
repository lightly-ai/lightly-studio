<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import ImagesAnnotatePopover from './ImagesAnnotatePopover.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
    }
    let { client, selectedCount }: Props = $props();
</script>

<QueryClientProvider {client}>
    <ImagesAnnotatePopover collectionId="c1" {selectedCount} open={true} onOpenChange={() => {}} />
</QueryClientProvider>
