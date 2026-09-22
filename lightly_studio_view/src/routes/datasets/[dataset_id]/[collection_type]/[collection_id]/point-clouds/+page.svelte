<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { McapSequencesGrid } from '$lib/components/McapSequencesGrid';
    import { useGlobalStorage, useMcapSequencesInfinite } from '$lib/hooks';
    import { routeHelpers } from '$lib/routes';
    import type { PageData } from './$types.js';

    interface Props {
        data: PageData;
    }

    const collectionId = $derived(page.params.collection_id!);
    const collectionType = $derived(page.params.collection_type!);
    const { data: pageData }: Props = $props();

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

    const handleSequenceClick = (sampleId: string) => {
        void goto(
            routeHelpers.toPointCloudLabeling({
                datasetId: pageData.collection.dataset_id,
                collectionType,
                collectionId,
                sampleId
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
