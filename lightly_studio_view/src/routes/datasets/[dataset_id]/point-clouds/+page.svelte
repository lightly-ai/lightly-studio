<script lang="ts">
    import { page } from '$app/state';
    import { useMcapSequences } from '$lib/hooks';
    import { routeHelpers } from '$lib/routes';
    import GridContainer from '$lib/components/GridContainer/GridContainer.svelte';

    const collectionId = $derived(page.params.dataset_id!);
    const { data: sequences, loadMore, query } = useMcapSequences(() => collectionId);
</script>

<div class="h-full w-full p-6" data-testid="mcap-sequences-page">
    <h1 class="mb-4 text-xl font-semibold">MCAP sequences</h1>
    <GridContainer
        itemCount={$sequences.length}
        message={{
            loading: 'Loading sequences...',
            error: 'Failed to load MCAP sequences.',
            empty: {
                title: 'No MCAP sequences found',
                description: 'This collection does not contain any MCAP sequences.'
            }
        }}
        status={{
            loading: query.isLoading,
            error: query.isError,
            empty: query.isSuccess && $sequences.length === 0,
            success: query.isSuccess && $sequences.length > 0
        }}
        loader={{
            loadMore,
            disabled: !query.hasNextPage || query.isFetchingNextPage,
            loading: query.isFetchingNextPage
        }}
    >
        {#snippet children({ footer })}
            <div class="grid grid-cols-[repeat(auto-fill,minmax(16rem,1fr))] gap-4">
                {#each $sequences as sequence}
                    <a
                        class="rounded-lg border p-4 transition-colors hover:bg-muted"
                        href={routeHelpers.toPointCloudLabeling({
                            datasetId: collectionId,
                            collectionId,
                            sampleId: sequence.sample_id
                        })}
                        data-testid={`mcap-sequence-${sequence.sample_id}`}
                    >
                        <div class="font-medium">Sequence {sequence.sample_id}</div>
                        <div class="mt-1 text-sm text-muted-foreground">
                            {sequence.sample_count}
                            {sequence.sample_count === 1 ? 'sample' : 'samples'}
                        </div>
                    </a>
                {/each}
            </div>
            {@render footer()}
        {/snippet}
    </GridContainer>
</div>
