<script lang="ts">
    import {
        CollectionLayout,
        CollectionLayoutHeader,
        CollectionLayoutSidebar,
        CollectionLayoutSearchBar,
        CollectionLayoutAuxControls,
        CollectionLayoutFooter,
        PlotPanel,
        CreateClassifierDialog,
        RefineClassifierDialog
    } from '$lib/components';
    import { useCollectionLayoutState } from '$lib/hooks';

    const { data, children } = $props();
    const {
        collection,
        globalStorage: {
            setTextEmbedding,
            textEmbedding,
            setLastGridType,
            clearSelectedSamples,
            clearSelectedSampleAnnotationCrops
        }
    } = $derived(data);

    // Master state management hook - call at top level, not inside $derived
    const state = useCollectionLayoutState({
        collection,
        setTextEmbedding,
        textEmbedding,
        setLastGridType,
        clearSelectedSamples,
        clearSelectedSampleAnnotationCrops
    });

    // Destructure stores for easy template access
    const {
        annotationFilterRows,
        showPlot,
        filteredSampleCount,
        filteredAnnotationCount
    } = state;
</script>

<CollectionLayout {...state.layoutProps}>
    {#snippet header()}
        <CollectionLayoutHeader
            collection={state.collection}
            routeType={state.routeType}
            hasEmbeddings={state.hasEmbeddings}
        />
    {/snippet}

    {#snippet sidebar()}
        <CollectionLayoutSidebar
            collectionId={state.collectionId}
            gridType={state.gridType}
            routeType={state.routeType}
            annotationFilterRows={annotationFilterRows}
            toggleAnnotationFilterSelection={state.toggleAnnotationFilterSelection}
        />
    {/snippet}

    {#snippet searchBar()}
        <CollectionLayoutSearchBar
            routeType={state.routeType}
            hasEmbeddings={state.hasEmbeddings}
            search={state.search}
        />
    {/snippet}

    {#snippet auxControls()}
        <CollectionLayoutAuxControls
            routeType={state.routeType}
            hasEmbeddings={state.hasEmbeddings}
            showPlot={$showPlot}
            setShowPlot={state.setShowPlot}
        />
    {/snippet}

    {#snippet plotPanel()}
        <PlotPanel />
    {/snippet}

    {#snippet fewShotDialogs()}
        {#if state.hasEmbeddings}
            <CreateClassifierDialog />
            <RefineClassifierDialog />
        {/if}
    {/snippet}

    {#snippet footer()}
        <CollectionLayoutFooter
            totalSamples={state.collection?.total_sample_count}
            filteredSamples={$filteredSampleCount}
            totalAnnotations={state.totalAnnotations}
            filteredAnnotations={$filteredAnnotationCount}
        />
    {/snippet}

    {@render children()}
</CollectionLayout>
