<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { McapSequencesGrid } from '$lib/components/McapSequencesGrid';
    import { useGlobalStorage, useMcapSequencesInfinite } from '$lib/hooks';
    import { routeHelpers } from '$lib/routes';

    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);
    const collectionType = $derived(page.params.collection_type!);

    const { data, query, loadMore, totalCount } = useMcapSequencesInfinite(() => collectionId);
    const { setfilteredSampleCount } = useGlobalStorage();

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });

    const sequences = $derived(
        $data.map((sequence) => ({
            sampleId: sequence.sample_id,
            sampleCount: sequence.sample_count,
            sequenceFrame: sequence.sequence_frame ?? null
        }))
    );
    const isLoading = $derived(query.isPending && sequences.length === 0);
    const isEmpty = $derived(query.isSuccess && sequences.length === 0);
    const isError = $derived(query.isError);
    const hasNextPage = $derived(query.hasNextPage ?? false);
    const isFetchingNextPage = $derived(query.isFetchingNextPage);

    // An MCAP component's sample is its sequence, so the sample id doubles as the sequence id.
    // The dataset slot carries a collection id (what the collection layout resolves the hierarchy
    // by); the labeling page derives the real dataset id from the loaded collection.
    const handleSequenceClick = (sampleId: string) => {
        void goto(
            routeHelpers.toPointCloudLabeling({
                datasetId,
                collectionType,
                collectionId,
                sequenceId: sampleId
            })
        );
    };
</script>

<McapSequencesGrid
    {sequences}
    {isLoading}
    {isEmpty}
    {isError}
    {hasNextPage}
    {isFetchingNextPage}
    onLoadMore={loadMore}
    onSequenceClick={handleSequenceClick}
/>
