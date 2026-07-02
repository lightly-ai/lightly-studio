<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { onDestroy, onMount } from 'svelte';
    import { toStore } from 'svelte/store';
    import { toast } from 'svelte-sonner';
    import {
        listEvaluationMatches,
        SampleType,
        type ConfusionCell,
        type EvaluationMatchType,
        type EvaluationMatchView,
        type ImageFilter,
        type SampleFilter
    } from '$lib/api/lightly_studio_local';
    import { GRID_PAGE_SIZE } from '$lib/constants';
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
    import { useMatchSort } from '$lib/hooks/useMatchSort/useMatchSort';
    import { useEvaluationMatchesInfinite } from '$lib/hooks/useEvaluationMatchesInfinite/useEvaluationMatchesInfinite';
    import {
        setMatchTaggingContext,
        clearMatchTaggingContext,
        setMatchSelectAllHandler,
        clearMatchSelectAllHandler,
        matchSelectionId
    } from '$lib/hooks/useMatchAnnotationTags/useMatchAnnotationTags';
    import { routeHelpers } from '$lib/routes';
    import { selectRangeByAnchor } from '$lib/utils/selectRangeByAnchor';
    import EvaluationMatchItem from './EvaluationMatchItem/EvaluationMatchItem.svelte';

    type Props = {
        datasetId: string;
        collectionId: string;
        evaluationRunId: string;
        itemWidth: number;
        // Restricts matches to a single parent image (sample-details entry point).
        sampleIds?: string[];
        // Filters below are URL-driven (parsed by the matches page). The confusion
        // cell is already scoped to this run by the page, so no run-id guard here.
        matchTypes?: EvaluationMatchType[];
        confusionCell?: ConfusionCell;
    };

    const {
        datasetId,
        collectionId,
        evaluationRunId,
        itemWidth,
        sampleIds,
        matchTypes,
        confusionCell
    }: Props = $props();

    const {
        getCollectionVersion,
        selectedSampleAnnotationCropIds,
        toggleSampleAnnotationCropSelection,
        clearSelectedSampleAnnotationCrops,
        setAllSelectedAnnotationCropIds,
        setfilteredMatchCount
    } = useGlobalStorage();
    let collectionVersion = $state('');
    onMount(async () => {
        collectionVersion = await getCollectionVersion(collectionId);
    });

    // Selection, the selection pill and the select-all control are all keyed to the
    // route's collection (the same one the images/annotations grids use), so the
    // matches selection lives there too — as one composite id per match.
    const selectionCollectionId = $derived(page.params.collection_id!);

    const { selectedAnnotationFilterIdsArray } = useSelectedAnnotationsFilter();
    const { tagsSelected } = $derived(useTags({ collection_id: collectionId, kind: ['sample'] }));
    const collectionIdStore = toStore(() => collectionId);
    const { dimensionsValues } = useDimensions(collectionIdStore);
    const { metadataValues } = $derived(useMetadataFilters(collectionId));
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
        matchTypes: matchTypes && matchTypes.length > 0 ? matchTypes : undefined,
        annotationLabelIds:
            $selectedAnnotationFilterIdsArray.length > 0
                ? $selectedAnnotationFilterIdsArray
                : undefined,
        confusionCell,
        imageFilter,
        sortField: $sortField,
        sortDirection: $sortDirection
    }));

    const matches: EvaluationMatchView[] = $derived(
        infiniteMatches.data?.pages.flatMap((p) => p.data) ?? []
    );

    // Feed the footer the number of matches the current filters resolve to (the
    // total for the query, not just the page that has scrolled into view).
    $effect(() => {
        setfilteredMatchCount(infiniteMatches.data?.pages[0]?.total_count ?? 0);
    });

    function handleLoadMore() {
        if (infiniteMatches.hasNextPage) {
            infiniteMatches.fetchNextPage();
        }
    }

    // A match has no id of its own, so identify it by the annotation ids it pairs
    // (gt for FN, pred for FP, both for TP) — stable across re-renders and unique.
    function matchKey(match: EvaluationMatchView): string {
        return matchSelectionId(match.gt_annotation?.sample_id, match.pred_annotation?.sample_id);
    }

    // Ground-truth and prediction annotations live in separate annotation
    // collections, but every match in a run shares the same two; capture each so a
    // composite selection id can be split back to the right collection when tagging.
    const gtCollectionId = $derived(
        matches.find((match) => match.gt_annotation)?.gt_annotation?.annotation_collection_id ??
            null
    );
    const predCollectionId = $derived(
        matches.find((match) => match.pred_annotation)?.pred_annotation?.annotation_collection_id ??
            null
    );

    // Selection is stored in the shared annotation-crop store under the route's
    // collection — the same store, pill and select-all the other grids use.
    const selectedMatchIds = $derived(
        $selectedSampleAnnotationCropIds[selectionCollectionId] ?? new Set<string>()
    );

    function isMatchSelected(match: EvaluationMatchView): boolean {
        return selectedMatchIds.has(matchKey(match));
    }

    let selectionAnchorKey = $state<string | null>(null);

    function handleSelect(event: MouseEvent | KeyboardEvent, index: number) {
        selectionAnchorKey = selectRangeByAnchor({
            sampleIdsInOrder: matches.map(matchKey),
            selectedSampleIds: selectedMatchIds,
            clickedSampleId: matchKey(matches[index]),
            clickedIndex: index,
            shiftKey: event.shiftKey,
            anchorSampleId: selectionAnchorKey,
            // selectRangeByAnchor only calls this for the clicked item (toggle) or
            // for not-yet-selected items in a shift range (select), so toggling is
            // correct for both.
            onSelectSample: (key) => toggleSampleAnnotationCropSelection(selectionCollectionId, key)
        });
    }

    function clearSelection() {
        clearSelectedSampleAnnotationCrops(selectionCollectionId);
        selectionAnchorKey = null;
    }

    // Select-all mirrors the other grids: page through every match the current
    // filters resolve to and select them all. Matches have no dedicated ids
    // endpoint, so walk the same paginated listing the grid renders.
    async function selectAllMatches() {
        const toastId = toast.loading('Selecting all matches...');
        try {
            const ids = new Set<string>();
            let offset = 0;
            for (;;) {
                const { data } = await listEvaluationMatches({
                    path: { dataset_id: datasetId, evaluation_run_id: evaluationRunId },
                    body: {
                        collection_id: collectionId,
                        match_types: matchTypes && matchTypes.length ? matchTypes : undefined,
                        annotation_label_ids: $selectedAnnotationFilterIdsArray.length
                            ? $selectedAnnotationFilterIdsArray
                            : undefined,
                        confusion_cell: confusionCell,
                        image_filter: imageFilter,
                        sort_field: $sortField,
                        sort_direction: $sortDirection,
                        pagination: { offset, limit: GRID_PAGE_SIZE }
                    },
                    throwOnError: true
                });
                for (const match of data.data) {
                    ids.add(
                        matchSelectionId(
                            match.gt_annotation?.sample_id,
                            match.pred_annotation?.sample_id
                        )
                    );
                }
                if (data.nextCursor == null) break;
                offset = data.nextCursor;
            }
            setAllSelectedAnnotationCropIds(selectionCollectionId, ids);
            toast.success(`${ids.size} matches selected`, { id: toastId });
        } catch {
            toast.error('Failed to select all matches', { id: toastId });
        }
    }

    $effect(() => {
        setMatchTaggingContext({ selectionCollectionId, gtCollectionId, predCollectionId });
    });
    onMount(() => {
        setMatchSelectAllHandler(selectAllMatches);
    });

    onDestroy(() => {
        clearSelection();
        clearMatchTaggingContext();
        clearMatchSelectAllHandler();
        setfilteredMatchCount(0);
    });

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
            (matchTypes ?? []).join(','),
            $selectedAnnotationFilterIdsArray.join(','),
            Array.from($tagsSelected).join(','),
            JSON.stringify(imageFilter ?? {}),
            JSON.stringify(confusionCell ?? {}),
            $sortField,
            $sortDirection
        ].join('|')
    );

    // Selecting matches and then changing filters would leave a confusing,
    // invisible selection behind, so reset it whenever the filter set changes.
    let lastFilterHash = $state('');
    $effect(() => {
        if (filterHash !== lastFilterHash) {
            lastFilterHash = filterHash;
            clearSelection();
        }
    });
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
                                    isSelected={isMatchSelected(matches[index])}
                                    ariaLabel={`Evaluation match: ${matches[index].match_type}`}
                                    onSelect={(event) => handleSelect(event, index)}
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
