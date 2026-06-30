<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { onDestroy, onMount } from 'svelte';
    import { toStore } from 'svelte/store';
    import {
        SampleType,
        type AnnotationView,
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
    import {
        setMatchTaggingCollectionIds,
        clearMatchTaggingCollectionIds
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
    };

    const { datasetId, collectionId, evaluationRunId, itemWidth, sampleIds }: Props = $props();

    const {
        getCollectionVersion,
        selectedSampleAnnotationCropIds,
        toggleSampleAnnotationCropSelection,
        clearSelectedSampleAnnotationCrops
    } = useGlobalStorage();
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

    // A match has no id of its own, so identify it by the annotation ids it pairs
    // (gt for FN, pred for FP, both for TP) — stable across re-renders and unique.
    function matchKey(match: EvaluationMatchView): string {
        return `${match.gt_annotation?.sample_id ?? ''}|${match.pred_annotation?.sample_id ?? ''}`;
    }

    // The annotations a match should be selected/tagged through: a true positive
    // carries both boxes, a false positive only the prediction, a false negative
    // only the ground truth.
    function matchAnnotations(match: EvaluationMatchView): AnnotationView[] {
        return [match.gt_annotation, match.pred_annotation].filter(
            (annotation): annotation is AnnotationView => annotation != null
        );
    }

    // Ground-truth and prediction annotations live in separate annotation
    // collections; publish both so the left-panel Tags menu can create and apply
    // annotation tags across them for the current selection.
    const annotationCollectionIds = $derived.by(() => {
        const ids = new Set<string>();
        for (const match of matches) {
            if (match.gt_annotation) ids.add(match.gt_annotation.annotation_collection_id);
            if (match.pred_annotation) ids.add(match.pred_annotation.annotation_collection_id);
        }
        return Array.from(ids);
    });

    // Selection lives in the shared annotation-crop store, keyed by each
    // annotation's own (ground-truth or prediction) collection — the same store the
    // annotations grid uses — so the left-panel Tags menu can act on it.
    function isMatchSelected(match: EvaluationMatchView): boolean {
        const annotations = matchAnnotations(match);
        return (
            annotations.length > 0 &&
            annotations.every((annotation) =>
                $selectedSampleAnnotationCropIds[annotation.annotation_collection_id]?.has(
                    annotation.sample_id
                )
            )
        );
    }

    function setMatchSelected(match: EvaluationMatchView, selected: boolean) {
        for (const annotation of matchAnnotations(match)) {
            const isCurrentlySelected = !!$selectedSampleAnnotationCropIds[
                annotation.annotation_collection_id
            ]?.has(annotation.sample_id);
            if (isCurrentlySelected !== selected) {
                toggleSampleAnnotationCropSelection(
                    annotation.annotation_collection_id,
                    annotation.sample_id
                );
            }
        }
    }

    let selectionAnchorKey = $state<string | null>(null);

    function handleSelect(event: MouseEvent | KeyboardEvent, index: number) {
        const selectedKeys = new Set(matches.filter(isMatchSelected).map(matchKey));
        const keyToMatch = new Map(matches.map((match) => [matchKey(match), match]));
        selectionAnchorKey = selectRangeByAnchor({
            sampleIdsInOrder: matches.map(matchKey),
            selectedSampleIds: selectedKeys,
            clickedSampleId: matchKey(matches[index]),
            clickedIndex: index,
            shiftKey: event.shiftKey,
            anchorSampleId: selectionAnchorKey,
            // selectRangeByAnchor only calls this for the clicked item (toggle) or
            // for not-yet-selected items in a shift range (select), so toggling the
            // match to its opposite state is correct for both.
            onSelectSample: (key) => {
                const match = keyToMatch.get(key);
                if (match) setMatchSelected(match, !isMatchSelected(match));
            }
        });
    }

    function clearSelection() {
        for (const collectionId of annotationCollectionIds) {
            clearSelectedSampleAnnotationCrops(collectionId);
        }
        selectionAnchorKey = null;
    }

    $effect(() => {
        setMatchTaggingCollectionIds(annotationCollectionIds);
    });

    onDestroy(() => {
        clearSelection();
        clearMatchTaggingCollectionIds();
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
            $selectedMatchTypesArray.join(','),
            $selectedAnnotationFilterIdsArray.join(','),
            Array.from($tagsSelected).join(','),
            JSON.stringify(imageFilter ?? {}),
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
