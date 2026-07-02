<script lang="ts">
    import { page } from '$app/state';
    import EvaluationMatchesGrid from '$lib/components/EvaluationMatchesGrid/EvaluationMatchesGrid.svelte';
    import { parseConfusionCellParam, parseMatchTypesParam } from '$lib/utils';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();
    const { collection, sampleSize } = $derived(data);

    // The dataset_id route param is the root image collection id (used to scope
    // image filters), while collection.dataset_id is the true dataset uuid used
    // by the evaluation API path.
    const scopeCollectionId = $derived(page.params.dataset_id!);
    const evaluationRunId = $derived(page.params.evaluation_run_id!);

    // All match filters live in the URL so the view is shareable and reload-safe.
    // Parse them here and hand them to the grid as props (like sample_ids).
    const sampleIds = $derived(
        page.url.searchParams.get('sample_ids')?.split(',').filter(Boolean) ?? undefined
    );
    const matchTypes = $derived(parseMatchTypesParam(page.url.searchParams));
    const confusionCell = $derived(parseConfusionCellParam(page.url.searchParams, evaluationRunId));
</script>

<EvaluationMatchesGrid
    datasetId={collection.dataset_id}
    collectionId={scopeCollectionId}
    {evaluationRunId}
    itemWidth={$sampleSize.width}
    {sampleIds}
    {matchTypes}
    {confusionCell}
/>
