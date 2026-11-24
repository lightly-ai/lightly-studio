<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { EvaluationComparison } from '$lib/components/EvaluationComparison';
    import { routeHelpers } from '$lib/routes';
    import type { PageData } from './$types';

    const { data }: { data: PageData } = $props();

    // The dataset slot of the route holds the root collection ID. The API needs the dataset ID.
    const datasetId = $derived(data.collection.dataset_id);
    const listParam = (name: string): string[] =>
        (page.url.searchParams.get(name) ?? '').split(',').filter(Boolean);
    const runIds = $derived(listParam('runs'));
    const tagIds = $derived(listParam('tags'));

    const setTagIds = (nextTagIds: string[]) => {
        const url = new URL(page.url);
        if (nextTagIds.length > 0) {
            url.searchParams.set('tags', nextTagIds.join(','));
        } else {
            url.searchParams.delete('tags');
        }
        goto(url, { replaceState: true, noScroll: true, keepFocus: true });
    };
    const imagesHref = $derived(
        routeHelpers.toImages(
            page.params.dataset_id!,
            page.params.collection_type!,
            page.params.collection_id!
        )
    );
</script>

<EvaluationComparison
    {datasetId}
    collectionId={page.params.collection_id!}
    {runIds}
    {tagIds}
    onTagIdsChange={setTagIds}
    {imagesHref}
/>
