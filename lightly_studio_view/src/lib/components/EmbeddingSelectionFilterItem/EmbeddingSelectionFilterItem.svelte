<script lang="ts">
    import { Checkbox } from '$lib/components/ui/checkbox';
    import { X } from '@lucide/svelte';
    import { useEmbeddingFilterForImages } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForImages';
    import { useEmbeddingFilterForVideos } from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForVideos';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { Readable } from 'svelte/store';

    type Props = {
        collectionIdStore: Readable<string>;
        isVideos: boolean;
        isSamples: boolean;
    };

    let { collectionIdStore, isVideos, isSamples }: Props = $props();

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

    const plotFilterItemLabel = $derived(isVideos ? 'video' : 'sample');
    const isPlotFilterApplied = $derived($isPlotFilterAppliedStore);
    const plotFilterCount = $derived($plotFilterCountStore);
    const hasPlotFilterContext = $derived((isSamples || isVideos) && plotFilterCount > 0);
</script>

{#if hasPlotFilterContext}
    <div
        class="rounded-md border border-amber-500/35 bg-amber-500/10 px-2 py-1.5"
        data-testid="embedding-selection-filter-chip"
    >
        <div class="flex items-center gap-2">
            <Checkbox
                checked={isPlotFilterApplied}
                aria-label="Embedding plot filter"
                onCheckedChange={(nextChecked) => setEmbeddingFilterVisibility(nextChecked === true)}
            />
            <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium">Embedding Plot Filter</div>
                <div class="text-xs text-muted-foreground">
                    {plotFilterCount}
                    {plotFilterCount === 1 ? plotFilterItemLabel : `${plotFilterItemLabel}s`}
                </div>
            </div>
            <button
                class="text-muted-foreground hover:text-foreground"
                onclick={clearFilter}
                title="Clear embedding plot filter"
                aria-label="Clear embedding plot filter"
            >
                <X class="size-4" />
            </button>
        </div>
    </div>
{/if}
