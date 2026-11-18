<script lang="ts">
    import { QueryClientProvider, type QueryClient } from '@tanstack/svelte-query';
    import type { ComponentProps } from 'svelte';
    import PointCloudAnnotationDetails from './PointCloudAnnotationDetails.svelte';

    interface Props extends ComponentProps<typeof PointCloudAnnotationDetails> {
        client: QueryClient;
    }

    let {
        client,
        annotation,
        annotationSourceName,
        editable,
        occupiedTrackIds,
        onAnnotationChange,
        onTrackChange
    }: Props = $props();
</script>

<QueryClientProvider {client}>
    <PointCloudAnnotationDetails
        {annotation}
        {annotationSourceName}
        {editable}
        {occupiedTrackIds}
        {onAnnotationChange}
        {onTrackChange}
    />
</QueryClientProvider>
