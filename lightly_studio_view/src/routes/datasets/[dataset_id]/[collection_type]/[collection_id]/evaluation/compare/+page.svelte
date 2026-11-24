<script lang="ts">
    import { page } from '$app/state';
    import { EvaluationComparison } from '$lib/components/EvaluationComparison';
    import { routeHelpers } from '$lib/routes';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();

    // The dataset slot of the route holds the root collection ID. The API needs the dataset ID.
    const datasetId = $derived(data.collection.dataset_id);
    const runIds = $derived((page.url.searchParams.get('runs') ?? '').split(',').filter(Boolean));
    const imagesHref = $derived(
        routeHelpers.toImages(
            page.params.dataset_id!,
            page.params.collection_type!,
            page.params.collection_id!
        )
    );
</script>

<EvaluationComparison {datasetId} {runIds} {imagesHref} />
