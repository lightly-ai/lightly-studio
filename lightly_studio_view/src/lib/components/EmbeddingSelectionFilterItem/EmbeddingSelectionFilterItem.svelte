<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useEmbeddingFilterForImages } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages';
    import { useEmbeddingFilterForVideos } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { Readable } from 'svelte/store';

    type Props = {
        collectionIdStore: Readable<string>;
        isVideos: boolean;
        isImages: boolean;
    };

    let { collectionIdStore, isVideos, isImages }: Props = $props();

    const { setRangeSelectionForCollection } = useGlobalStorage();

    const embeddingFilter = isVideos
        ? useEmbeddingFilterForVideos(collectionIdStore, setRangeSelectionForCollection)
        : useEmbeddingFilterForImages(collectionIdStore, setRangeSelectionForCollection);

    const plotFilterCountStore = $derived(embeddingFilter.effectiveCount);
    const isPlotFilterAppliedStore = $derived(embeddingFilter.isVisible);

    const setEmbeddingFilterVisibility = (shouldShow: boolean) => {
        embeddingFilter.setVisibility(shouldShow);
    };

    const clearFilter = () => {
        embeddingFilter.clearFilter();
    };

    const plotFilterItemLabel = $derived(isVideos ? 'video' : 'image');
    const isPlotFilterApplied = $derived($isPlotFilterAppliedStore);
    const plotFilterCount = $derived($plotFilterCountStore);
    const hasPlotFilterContext = $derived((isImages || isVideos) && plotFilterCount > 0);
</script>

{#if hasPlotFilterContext}
    <Segment title="Embeddings">
        <FilterChip
            checked={isPlotFilterApplied}
            title="Embedding Plot Filter"
            checkboxLabel="Embedding plot filter"
            testId="embedding-selection-filter-chip"
            onCheckedChange={(nextChecked) => setEmbeddingFilterVisibility(nextChecked === true)}
            onClear={clearFilter}
        >
            {#snippet subtitle()}
                <div class="text-xs text-muted-foreground">
                    {plotFilterCount}
                    {plotFilterCount === 1 ? plotFilterItemLabel : `${plotFilterItemLabel}s`}
                </div>
            {/snippet}
        </FilterChip>
    </Segment>
{/if}
