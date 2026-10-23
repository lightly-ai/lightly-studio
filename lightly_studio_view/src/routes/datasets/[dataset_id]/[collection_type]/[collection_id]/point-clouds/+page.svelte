<script lang="ts">
    import type { PageData } from './$types';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { get } from 'svelte/store';
    import { McapSequencesGrid } from '$lib/components/McapSequencesGrid';
    import { useGlobalStorage, useMcapSequenceFilters, useMcapSequencesInfinite } from '$lib/hooks';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { routeHelpers } from '$lib/routes';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';

    // The page layout provides data, but this route loads its own sequence data.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { data: _data }: { data: PageData } = $props();
    const datasetId = $derived(page.params.dataset_id!);
    const collectionId = $derived(page.params.collection_id!);
    const collectionType = $derived(page.params.collection_type!);

    const { textEmbedding, getSelectedSampleIds, toggleSampleSelection, setfilteredSampleCount } =
        useGlobalStorage();
    const { mcapSequenceFilter, setCollectionId, updateTagIds } = useMcapSequenceFilters();
    const { tagsSelected } = $derived.by(() => useTags({ collection_id: collectionId }));

    $effect(() => {
        setCollectionId(collectionId);
        updateTagIds(Array.from($tagsSelected));
    });

    const {
        data: sequenceData,
        query,
        loadMore,
        totalCount
    } = useMcapSequencesInfinite(() => ({
        collection_id: collectionId,
        filter: $mcapSequenceFilter,
        text_embedding: $textEmbedding?.embedding
    }));

    $effect(() => {
        setfilteredSampleCount($totalCount);
    });

    const sequences = $derived(
        $sequenceData.map((sequence) => ({
            sampleId: sequence.sample_id,
            fileName: sequence.file_name,
            sampleCount: sequence.sample_count,
            sequenceFrame: sequence.sequence_frame ?? null,
            similarityScore: sequence.similarity_score ?? null
        }))
    );
    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    let selectionAnchorSampleId = $state<string | null>(null);
    const isLoading = $derived(query.isPending && sequences.length === 0);
    const isEmpty = $derived(query.isSuccess && sequences.length === 0);
    const isError = $derived(query.isError);
    const hasNextPage = $derived(query.hasNextPage ?? false);
    const isFetchingNextPage = $derived(query.isFetchingNextPage);

    const handleSequenceSelect = (sampleId: string, index: number, shiftKey: boolean) => {
        selectionAnchorSampleId = selectRangeByAnchor({
            sampleIdsInOrder: sequences.map((sequence) => sequence.sampleId),
            selectedSampleIds: get(getSelectedSampleIds(collectionId)),
            clickedSampleId: sampleId,
            clickedIndex: index,
            shiftKey,
            anchorSampleId: selectionAnchorSampleId,
            onSelectSample: (selectedSampleId) =>
                toggleSampleSelection(selectedSampleId, collectionId)
        });
    };

    // An MCAP component's sample is its sequence, so the sample id doubles as the sequence id.
    // The dataset slot carries a collection id (what the collection layout resolves the hierarchy
    // by); the labeling page derives the real dataset id from the loaded collection.
    const handleSequenceOpen = (sampleId: string) => {
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
    selectedSampleIds={$selectedSampleIds}
    {isLoading}
    {isEmpty}
    {isError}
    {hasNextPage}
    {isFetchingNextPage}
    scrollResetKey={JSON.stringify($mcapSequenceFilter) + ($textEmbedding?.queryText ?? '')}
    onLoadMore={loadMore}
    onSequenceSelect={handleSequenceSelect}
    onSequenceOpen={handleSequenceOpen}
/>
