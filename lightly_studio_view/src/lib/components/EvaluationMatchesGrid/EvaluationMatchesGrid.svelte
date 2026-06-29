<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
    import { toStore } from 'svelte/store';
    import {
        SampleType,
        type EvaluationMatchView,
        type ImageFilter,
        type SampleFilter
    } from '$lib/api/lightly_studio_local';
    import { GridContainer } from '$lib/components/GridContainer';
    import { Grid } from '$lib/components/Grid';
    import { GridItem } from '$lib/components/GridItem';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useSelectedAnnotationsFilter } from '$lib/hooks/useAnnotationsFilter/useAnnotationsFilter';
    import { useTags } from '$lib/hooks/useTags/useTags';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import {
        createMetadataFilters,
        useMetadataFilters
    } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useMatchTypeFilter } from '$lib/hooks/useMatchTypeFilter/useMatchTypeFilter';
    import { useMatchSort } from '$lib/hooks/useMatchSort/useMatchSort';
    import { useEvaluationMatchesInfinite } from '$lib/hooks/useEvaluationMatchesInfinite/useEvaluationMatchesInfinite';
    import { routeHelpers } from '$lib/routes';
    import EvaluationMatchItem from './EvaluationMatchItem/EvaluationMatchItem.svelte';

    type Props = {
        datasetId: string;
        collectionId: string;
        evaluationRunId: string;
        itemWidth: number;
        // Restricts matches to a single parent image (sample-details entry point).
        sampleIds?: string[];
    };

    const { datasetId, collectionId, evaluationRunId, itemWidth, sampleIds }: Props = $props();

    const { getCollectionVersion } = useGlobalStorage();
    let collectionVersion = $state('');
    onMount(async () => {
        collectionVersion = await getCollectionVersion(collectionId);
    });

    const { selectedAnnotationFilterIdsArray } = useSelectedAnnotationsFilter();
    const { tagsSelected } = $derived(useTags({ collection_id: collectionId, kind: ['sample'] }));
    const collectionIdStore = toStore(() => collectionId);
    const { dimensionsValues } = useDimensions(collectionIdStore);
    const { metadataValues } = $derived(useMetadataFilters(collectionId));
    const { selectedMatchTypesArray } = useMatchTypeFilter();
    const { sortField, sortDirection } = useMatchSort();

    const imageFilter = $derived.by((): ImageFilter | undefined => {
        const sampleFilter: SampleFilter = {};

        if ($tagsSelected.size > 0) {
            sampleFilter.tag_ids = Array.from($tagsSelected);
        }
        if (sampleIds && sampleIds.length > 0) {
            sampleFilter.sample_ids = sampleIds;
        }
        const metadataFilters = $metadataValues ? createMetadataFilters($metadataValues) : [];
        if (metadataFilters.length > 0) {
            sampleFilter.metadata_filters = metadataFilters;
        }

        const filter: ImageFilter = { filter_type: 'image' };
        let hasFilter = false;

        const dims = $dimensionsValues;
        if (dims?.min_width != null || dims?.max_width != null) {
            filter.width = { min: dims?.min_width ?? undefined, max: dims?.max_width ?? undefined };
            hasFilter = true;
        }
        if (dims?.min_height != null || dims?.max_height != null) {
            filter.height = {
                min: dims?.min_height ?? undefined,
                max: dims?.max_height ?? undefined
            };
            hasFilter = true;
        }
        if (Object.keys(sampleFilter).length > 0) {
            filter.sample_filter = sampleFilter;
            hasFilter = true;
        }

        return hasFilter ? filter : undefined;
    });

    const { matches: infiniteMatches } = useEvaluationMatchesInfinite(() => ({
        datasetId,
        evaluationRunId,
        collectionId,
        matchTypes: $selectedMatchTypesArray.length > 0 ? $selectedMatchTypesArray : undefined,
        annotationLabelIds:
            $selectedAnnotationFilterIdsArray.length > 0
                ? $selectedAnnotationFilterIdsArray
                : undefined,
        imageFilter,
        sortField: $sortField,
        sortDirection: $sortDirection
    }));

    const matches: EvaluationMatchView[] = $derived(
        infiniteMatches.data?.pages.flatMap((p) => p.data) ?? []
    );

    function handleLoadMore() {
        if (infiniteMatches.hasNextPage) {
            infiniteMatches.fetchNextPage();
        }
    }

    // Open the annotation details for the box that produced the match: prefer the
    // prediction (what we usually debug), fall back to ground truth for FN matches.
    // The annotation lives in its own (GT or prediction) annotation collection, so we
    // route through that collection. The URL dataset segment is the root collection id
    // from the route, which the details layout uses to resolve the collection hierarchy.
    function handleOnDoubleClick(match: EvaluationMatchView) {
        const annotation = match.pred_annotation ?? match.gt_annotation;
        if (!annotation) {
            return;
        }
        goto(
            routeHelpers.toSampleWithAnnotation({
                datasetId: page.params.dataset_id!,
                collectionType: SampleType.ANNOTATION,
                collectionId: annotation.annotation_collection_id,
                annotationId: annotation.sample_id
            })
        );
    }

    const filterHash = $derived(
        [
            $selectedMatchTypesArray.join(','),
            $selectedAnnotationFilterIdsArray.join(','),
            Array.from($tagsSelected).join(','),
            JSON.stringify(imageFilter ?? {}),
            $sortField,
            $sortDirection
        ].join('|')
    );
</script>

<div class="flex h-full min-w-0 flex-1">
    <div class="min-w-0 flex-1">
        <GridContainer
            itemCount={matches.length}
            message={{
                loading: 'Loading evaluation matches...',
                error: 'Error loading evaluation matches',
                empty: {
                    title: 'No matches found',
                    description:
                        'No TP/FP/FN matches for this run with the current filters. Object detection runs only.'
                }
            }}
            status={{
                loading: infiniteMatches.isPending && matches.length === 0,
                error: infiniteMatches.isError && matches.length === 0,
                empty: infiniteMatches.isFetched && matches.length === 0,
                success: matches.length > 0
            }}
            loader={{
                loadMore: handleLoadMore,
                disabled: !infiniteMatches.hasNextPage || infiniteMatches.isFetchingNextPage,
                loading: infiniteMatches.isFetchingNextPage
            }}
        >
            {#snippet children({ footer })}
                <Grid
                    itemCount={matches.length}
                    columnCount={itemWidth}
                    scrollResetKey={filterHash}
                    gridProps={{
                        'data-testid': 'evaluation-matches-grid',
                        class: 'dark:[color-scheme:dark]'
                    }}
                >
                    {#snippet gridItem({ index, style, width, height })}
                        {#if matches[index]}
                            {#key index}
                                <GridItem
                                    {width}
                                    {height}
                                    {style}
                                    dataTestId="evaluation-match-grid-item"
                                    tag={false}
                                    ariaLabel={`Evaluation match: ${matches[index].match_type}`}
                                    onSelect={() => undefined}
                                    ondblclick={() => handleOnDoubleClick(matches[index])}
                                >
                                    <EvaluationMatchItem
                                        match={matches[index]}
                                        containerWidth={width}
                                        containerHeight={height}
                                        cachedCollectionVersion={collectionVersion}
                                    />
                                </GridItem>
                            {/key}
                        {/if}
                    {/snippet}
                    {#snippet footerItem()}
                        {@render footer()}
                    {/snippet}
                </Grid>
            {/snippet}
        </GridContainer>
    </div>
</div>
