<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import ConnectedDatasetSplitDialog from '../ConnectedDatasetSplitDialog/ConnectedDatasetSplitDialog.svelte';

    interface Props {
        client: QueryClient;
        sampleType: 'image' | 'video';
        onClose: () => void;
    }
    let { client, sampleType, onClose }: Props = $props();
</script>

<QueryClientProvider {client}>
    <ConnectedDatasetSplitDialog collectionId="collection" {sampleType} {onClose} />
</QueryClientProvider>
