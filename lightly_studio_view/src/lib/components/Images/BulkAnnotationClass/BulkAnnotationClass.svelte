<script lang="ts">
    import { toast } from 'svelte-sonner';
    import { get } from 'svelte/store';
    import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local';
    import { Card, CardContent } from '$lib/components';
    import BulkAnnotationClassPanel from '$lib/components/BulkAnnotationClassPanel/BulkAnnotationClassPanel.svelte';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useBulkAddAnnotationClass } from '$lib/hooks/useBulkAddAnnotationClass/useBulkAddAnnotationClass';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import {
        useImageAnnotationCounts,
        useImageAnnotationCountsQueryKey
    } from '$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts';
    import {
        buildSelectionCountsFilter,
        formatApplyResult,
        resolveAnnotationSource,
        toAnnotationClassOptions,
        toSelectionClassCounts
    } from './BulkAnnotationClass.helpers';

    interface Props {
        collectionId: string;
    }

    const { collectionId }: Props = $props();

    const {
        getSelectedSampleIds,
        isEditingMode,
        lastAnnotationSource,
        updateLastAnnotationSource
    } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    const selectedCount = $derived($selectedSampleIds.size);
    const isVisible = $derived($isEditingMode && selectedCount > 0);

    const annotationCollections = useAnnotationCollections(() => ({ collectionId }));
    const annotationLabels = useAnnotationLabels(() => ({ collectionId }));

    const sourceNames = $derived(annotationCollections.data?.map((source) => source.name) ?? []);
    const selectedSource = $derived(
        resolveAnnotationSource({ lastSource: $lastAnnotationSource[collectionId], sourceNames })
    );

    // The counts endpoint scopes by source ID, while the picker works in names. A name the user
    // just typed has no source yet, and therefore no existing annotations to count.
    const selectedSourceId = $derived(
        annotationCollections.data?.find((source) => source.name === selectedSource)?.collection_id
    );

    const countsSampleIds = $derived(isVisible ? [...$selectedSampleIds] : []);
    const countsFilter = $derived(
        selectedSourceId
            ? buildSelectionCountsFilter({
                  sampleIds: countsSampleIds,
                  annotationSourceId: selectedSourceId
              })
            : undefined
    );

    const counts = useImageAnnotationCounts(() => ({
        collectionId,
        annotationType: AnnotationType.CLASSIFICATION,
        // Distinct samples, not object counts: the panel reports how many images are skipped.
        countMode: AnnotationCountMode.SAMPLES,
        filter: countsFilter,
        // A suffix-extension of the shared key keeps mutation invalidations reaching this query
        // while isolating its cache entry; the selection and source are part of the key because
        // the base key does not cover the filter.
        queryKey: [
            ...useImageAnnotationCountsQueryKey,
            'bulkAnnotationClassSelection',
            { selectedSourceId, countsSampleIds }
        ],
        enabled: isVisible && selectedSourceId !== undefined
    }));

    const selectionClassCounts = $derived(
        selectedSourceId ? toSelectionClassCounts(counts.data) : []
    );

    const { addAnnotationClass } = useBulkAddAnnotationClass({
        getCollectionId: () => collectionId
    });

    let isApplying = $state(false);

    const handleApply = async ({ className, source }: { className: string; source: string }) => {
        if (isApplying) return;
        isApplying = true;
        try {
            const result = await addAnnotationClass({
                className,
                annotationSource: source,
                selectedSampleIds: get(getSelectedSampleIds(collectionId))
            });
            toast.success(
                formatApplyResult({
                    createdCount: result.created_count,
                    skippedCount: result.skipped_count
                })
            );
        } catch {
            toast.error('Failed to add the annotation class. Please try again.');
        } finally {
            isApplying = false;
        }
    };
</script>

<!--
    Sits beside the grid, mirroring the annotation grid's SelectedAnnotations panel, so it never
    occludes the tiles the user is checking their work against.
-->
{#if isVisible}
    <div class="min-w-[250px] max-w-[30%] flex-1">
        <Card className="h-full">
            <CardContent className="h-full flex flex-col">
                <div
                    class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
                >
                    <BulkAnnotationClassPanel
                        {selectedCount}
                        annotationClasses={toAnnotationClassOptions(annotationLabels.data)}
                        annotationSources={sourceNames}
                        {selectedSource}
                        {selectionClassCounts}
                        isLoadingCounts={counts.isFetching}
                        {isApplying}
                        onSourceChange={(source) =>
                            updateLastAnnotationSource(collectionId, source)}
                        onApply={handleApply}
                    />
                </div>
            </CardContent>
        </Card>
    </div>
{/if}
