<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import AnnotationsAnnotatePopover from './AnnotationsAnnotatePopover.svelte';

    interface Props {
        client: QueryClient;
        selectedCount: number;
    }
    let { client, selectedCount }: Props = $props();
</script>

<QueryClientProvider {client}>
    <AnnotationsAnnotatePopover
        collectionId="c1"
        {selectedCount}
        open={true}
        onOpenChange={() => {}}
    />
</QueryClientProvider>
