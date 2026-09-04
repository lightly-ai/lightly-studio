<script lang="ts">
    import { get } from 'svelte/store';
    import { page } from '$app/state';
    import { useAnnotationCollections } from '$lib/hooks/useAnnotationCollections/useAnnotationCollections';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { useBulkCreateClassifications } from '$lib/hooks/useBulkCreateClassifications/useBulkCreateClassifications';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import BulkClassificationPanel from './BulkClassificationPanel.svelte';

    type Props = {
        collectionId: string;
    };

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
    const selectAllSnapshot = $derived(get(getSelectAllSnapshot(collectionId)));
    const sourceNames = $derived(
        annotationCollectionsQuery.data?.map((source) => source.name) ?? []
    );
    const classNames = $derived(
        annotationLabelsQuery.data?.map((label) => label.annotation_label_name) ?? []
    );

    let sourceName = $state<string>();
    let className = $state<string>();
    let isApplying = $state(false);

    const effectiveSourceName = $derived(
        sourceName ??
            $lastAnnotationSource[collectionId] ??
            sourceNames.find((name) => name === DEFAULT_SOURCE_NAME) ??
            sourceNames[0] ??
            DEFAULT_SOURCE_NAME
    );

    const sourceOptions = $derived([...new Set([...sourceNames, effectiveSourceName])]);
    const classOptions = $derived([...new Set([...classNames, ...(className ? [className] : [])])]);

    $effect(() => {
        if (sourceName === undefined) {
            sourceName = effectiveSourceName;
        }
    });

    const handleSourceSelect = (name: string) => {
        sourceName = name;
        updateLastAnnotationSource(collectionId, name);
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
                selectAllSnapshot,
                rootCollectionId
            });
            clearSelectedSamples(collectionId);
        } finally {
            isApplying = false;
        }
    };
</script>

{#if $isEditingMode && $selectedSampleIds.size > 0}
    <BulkClassificationPanel
        selectedCount={$selectedSampleIds.size}
        {sourceName}
        {className}
        sourceNames={sourceOptions}
        classNames={classOptions}
        {isApplying}
        onSourceSelect={handleSourceSelect}
        onClassSelect={(name) => {
            className = name;
        }}
        onApply={handleApply}
    />
{/if}
