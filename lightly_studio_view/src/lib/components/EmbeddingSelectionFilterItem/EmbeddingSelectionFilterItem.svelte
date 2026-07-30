<script lang="ts">
    import FilterChip from '$lib/components/FilterChip/FilterChip.svelte';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { useEmbeddingFilterForAnnotations } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
    import { useEmbeddingFilterForImages } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages';
    import { useEmbeddingFilterForVideos } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { Readable } from 'svelte/store';

    type Props = {
        collectionIdStore: Readable<string>;
        isVideos: boolean;
        isImages: boolean;
        isAnnotations?: boolean;
    };

    let { collectionIdStore, isVideos, isImages, isAnnotations = false }: Props = $props();

    const { setRangeSelectionForCollection } = useGlobalStorage();

    // Instantiate all variants once and pick reactively: this component lives in the
    // layout, which persists when switching between the images/annotations tabs.
    // All three hooks are created in a single $derived.by so they are all eagerly evaluated
    // together (rather than lazily skipped by the ternary).
    const embeddingFilters = $derived.by(() => ({
        images: useEmbeddingFilterForImages(collectionIdStore, setRangeSelectionForCollection),
        videos: useEmbeddingFilterForVideos(collectionIdStore, setRangeSelectionForCollection),
        annotations: useEmbeddingFilterForAnnotations(
            collectionIdStore,
            setRangeSelectionForCollection
        )
    }));
    const embeddingFilter = $derived(
        isAnnotations
            ? embeddingFilters.annotations
            : isVideos
              ? embeddingFilters.videos
              : embeddingFilters.images
    );

    const plotFilterCountStore = $derived(embeddingFilter.effectiveCount);
    const isPlotFilterAppliedStore = $derived(embeddingFilter.isVisible);

    const setEmbeddingFilterVisibility = (shouldShow: boolean) => {
        embeddingFilter.setVisibility(shouldShow);
    };

    const clearFilter = () => {
        embeddingFilter.clearFilter();
    };

    const plotFilterItemLabel = $derived(
        isAnnotations ? 'annotation' : isVideos ? 'video' : 'image'
    );
    const isPlotFilterApplied = $derived($isPlotFilterAppliedStore);
    const plotFilterCount = $derived($plotFilterCountStore);
    const hasPlotFilterContext = $derived(
        (isImages || isVideos || isAnnotations) && plotFilterCount > 0
    );
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
