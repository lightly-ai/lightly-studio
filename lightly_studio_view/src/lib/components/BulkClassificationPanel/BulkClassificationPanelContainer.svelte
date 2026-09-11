<script lang="ts">
    import { page } from '$app/state';
    import {
        useAnnotationCollections,
        useAnnotationLabels,
        useBulkCreateClassifications,
        useGlobalStorage
    } from '$lib/hooks';
    import BulkClassificationPanel from './BulkClassificationPanel.svelte';

    interface Props {
        collectionId: string;
    }

    let { collectionId }: Props = $props();

    const DEFAULT_SOURCE_NAME = 'annotation';
    const rootCollectionId = $derived(page.params.dataset_id!);
    const annotationCollectionsQuery = useAnnotationCollections(() => ({ collectionId }));
    const annotationLabelsQuery = useAnnotationLabels(() => ({ collectionId }));
    const { addClass } = useBulkCreateClassifications();
    const {
        getSelectedSampleIds,
        getSelectAllSnapshot,
        isEditingMode,
        lastAnnotationSource,
        updateLastAnnotationSource,
        clearSelectedSamples
    } = useGlobalStorage();
    const selectedSampleIds = $derived(getSelectedSampleIds(collectionId));
    const selectAllSnapshot = $derived(getSelectAllSnapshot(collectionId));
    const sourceNames = $derived(
        annotationCollectionsQuery.data?.map((source) => source.name) ?? []
    );
    const classNames = $derived(
        annotationLabelsQuery.data?.map((label) => label.annotation_label_name) ?? []
    );

    let selection = $state<{ collectionId?: string; sourceName?: string; className?: string }>({});
    let isApplying = $state(false);

    // A selection belongs to the collection it was made in; another collection starts empty.
    const activeSelection = $derived(selection.collectionId === collectionId ? selection : {});

    // Stays undefined until the sources are known, so the fallbacks see the real source list.
    const defaultSourceName = $derived(
        $lastAnnotationSource[collectionId] ??
            (annotationCollectionsQuery.isSuccess
                ? (sourceNames.find((name) => name === DEFAULT_SOURCE_NAME) ??
                  sourceNames[0] ??
                  DEFAULT_SOURCE_NAME)
                : undefined)
    );
    const sourceName = $derived(activeSelection.sourceName ?? defaultSourceName);
    const className = $derived(activeSelection.className);

    const sourceOptions = $derived([
        ...new Set([...sourceNames, ...(sourceName ? [sourceName] : [])])
    ]);
    const classOptions = $derived([...new Set([...classNames, ...(className ? [className] : [])])]);

    const handleSourceSelect = (name: string) => {
        selection = { ...activeSelection, collectionId, sourceName: name };
        updateLastAnnotationSource(collectionId, name);
    };

    const handleClassSelect = (name: string) => {
        selection = { ...activeSelection, collectionId, className: name };
    };

    const handleApply = async () => {
        if (!className || !sourceName || isApplying || $selectedSampleIds.size === 0) return;
        isApplying = true;
        try {
            await addClass({
                collectionId,
                selectedIds: $selectedSampleIds,
                className,
                sourceName,
                selectAllSnapshot: $selectAllSnapshot,
                rootCollectionId
            });
            clearSelectedSamples(collectionId);
        } finally {
            isApplying = false;
        }
    };
</script>

{#if $isEditingMode}
    <div class="min-w-[250px] max-w-[30%] flex-1">
        <BulkClassificationPanel
            selectedCount={$selectedSampleIds.size}
            {sourceName}
            {className}
            sourceNames={sourceOptions}
            classNames={classOptions}
            {isApplying}
            onSourceSelect={handleSourceSelect}
            onClassSelect={handleClassSelect}
            onApply={handleApply}
        />
    </div>
{/if}
