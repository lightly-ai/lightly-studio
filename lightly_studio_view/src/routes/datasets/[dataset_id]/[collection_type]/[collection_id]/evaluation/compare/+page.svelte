<script lang="ts">
    import { page } from '$app/state';
    import { EvaluationComparison } from '$lib/components/EvaluationComparison';
    import { routeHelpers } from '$lib/routes';

    const datasetId = $derived(page.params.dataset_id!);
    const runIds = $derived((page.url.searchParams.get('runs') ?? '').split(',').filter(Boolean));
    const imagesHref = $derived(
        routeHelpers.toImages(datasetId, page.params.collection_type!, page.params.collection_id!)
    );
</script>

<EvaluationComparison {datasetId} {runIds} {imagesHref} />
