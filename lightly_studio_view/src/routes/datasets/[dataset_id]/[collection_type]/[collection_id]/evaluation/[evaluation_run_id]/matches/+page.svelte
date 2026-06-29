<script lang="ts">
    import { page } from '$app/state';
    import EvaluationMatchesGrid from '$lib/components/EvaluationMatchesGrid/EvaluationMatchesGrid.svelte';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
    const { collection, sampleSize } = $derived(data);

    // The dataset_id route param is the root image collection id (used to scope
    // image filters), while collection.dataset_id is the true dataset uuid used
    // by the evaluation API path.
    const scopeCollectionId = $derived(page.params.dataset_id!);
    const evaluationRunId = $derived(page.params.evaluation_run_id!);

    const sampleIds = $derived(
        page.url.searchParams.get('sample_ids')?.split(',').filter(Boolean) ?? undefined
    );
</script>

<EvaluationMatchesGrid
    datasetId={collection.dataset_id}
    collectionId={scopeCollectionId}
    {evaluationRunId}
    itemWidth={$sampleSize.width}
    {sampleIds}
/>
