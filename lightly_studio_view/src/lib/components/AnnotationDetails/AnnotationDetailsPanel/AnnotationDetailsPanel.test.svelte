<script lang="ts">
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import AnnotationDetailsPanel from './AnnotationDetailsPanel.svelte';

    let {
        queryClient,
        annotation,
        onUpdate,
        collectionId
    }: {
        queryClient: QueryClient;
        annotation: AnnotationView;
        onUpdate: () => void;
        collectionId: string;
    } = $props();
</script>

<QueryClientProvider client={queryClient}>
    <AnnotationDetailsPanel {annotation} {onUpdate} {collectionId}>
        <div data-testid="children-slot">Children content</div>
    </AnnotationDetailsPanel>
</QueryClientProvider>
